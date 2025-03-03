from datetime import datetime, timedelta, timezone
from typing import Dict, List, NamedTuple, IO, Optional
import json
import logging
from kloppy.domain import PitchDimensions, Point, Dimension


from kloppy.domain import (
    EventDataset,
    Team,
    Period,
    Point,
    BallState,
    DatasetFlag,
    Orientation,
    Provider,
    Metadata,
    Player,
    Score,
    Ground,
)
from kloppy.domain.models.common import DatasetType
from kloppy.domain.models.event import (
    BodyPart,
    BodyPartQualifier,
    PassQualifier,
    PassResult,
    PassType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
)
from kloppy.domain.models.pitch import Unit
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging
from enum import Enum
from lxml import objectify


logger = logging.getLogger(__name__)


class SecondSpectrumEvents:
    # Pass events
    PASS = "pass"
    CROSS = "cross"
    THROW_IN = "throw_in"
    FREE_KICK = "free_kick"
    CORNER = "corner"
    GOAL_KICK = "goal_kick"

    # Shot events
    SHOT = "shot"
    PENALTY = "penalty"

    # Other events
    DUEL = "duel"
    TAKE_ON = "take_on"
    INTERCEPTION = "interception"
    CLEARANCE = "clearance"
    BALL_RECOVERY = "ball_recovery"
    FOUL = "foul"
    CARD = "card"
    SUBSTITUTION = "substitution"


class SecondSpectrumEventDataInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]
    additional_meta_data: IO[bytes]


class SecondSpectrumEventDataDeserializer(
    EventDataDeserializer[SecondSpectrumEventDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.SECONDSPECTRUM

    def _parse_shot(self, raw_event: Dict) -> Dict:
        qualifiers = []

        if raw_event["attributes"]["scored"] == True:
            result = ShotResult.GOAL
        elif raw_event["attributes"]["saved"] == True:
            result = ShotResult.SAVED
        elif raw_event["attributes"]["woodwork"] == True:
            result = ShotResult.OFF_TARGET
        elif raw_event["attributes"]["deflected"] == True:
            result = ShotResult.BLOCKED
        else:
            result = None

        if "bodyPart" in raw_event["attributes"]:
            if raw_event["attributes"]["bodyPart"] == "head":
                qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))
            elif raw_event["attributes"]["bodyPart"] == "leftFoot":
                qualifiers.append(BodyPartQualifier(value=BodyPart.LEFT_FOOT))
            elif raw_event["attributes"]["bodyPart"] == "rightFoot":
                qualifiers.append(BodyPartQualifier(value=BodyPart.RIGHT_FOOT))
            elif raw_event["attributes"]["bodyPart"] == "upperBody":
                qualifiers.append(BodyPartQualifier(value=BodyPart.CHEST))
            elif raw_event["attributes"]["bodyPart"] == "lowerBody":
                qualifiers.append(BodyPartQualifier(value=BodyPart.OTHER))

        return {
            "result": result,
            "qualifiers": qualifiers,
            "location": raw_event["attributes"]["location"],
            "goalmouthLocation": raw_event["attributes"].get(
                "goalmouthLocation"
            ),
        }

    def _parse_pass(self, raw_event: Dict, team: Team) -> Dict:
        """Parse a pass event from SecondSpectrum data."""
        qualifiers = []

        # Get attributes and players from raw event
        attributes = raw_event.get("attributes", {})
        players = raw_event.get("players", {})

        # Determine pass result and receiver
        if attributes.get("complete", False):
            result = PassResult.COMPLETE
            receiver_player = (
                team.get_player_by_id(players.get("receiver"))
                if players.get("receiver")
                else None
            )
            # For complete passes, use end coordinates as receiver coordinates
            receiver_coordinates = raw_event.get("end_coordinates")
            # Calculate receive timestamp (assuming constant ball speed)
            if raw_event.get("timestamp") and attributes.get("distance"):
                # Estimate receive time based on distance and average pass speed (15 m/s)
                pass_duration = float(attributes["distance"]) / 15.0  # seconds
                receive_timestamp = raw_event["timestamp"] + timedelta(
                    seconds=pass_duration
                )
            else:
                receive_timestamp = raw_event["timestamp"]
        else:
            result = PassResult.INCOMPLETE
            receiver_player = None
            receiver_coordinates = None
            receive_timestamp = raw_event["timestamp"]

        # Add qualifiers
        if attributes.get("crossed", False):
            qualifiers.append(PassQualifier(value=PassType.CROSS))

        # Add body part qualifiers
        if "bodyPart" in attributes:
            body_part_name = attributes["bodyPart"].get("name")
            body_part_map = {
                "rightFoot": BodyPart.RIGHT_FOOT,
                "leftFoot": BodyPart.LEFT_FOOT,
                "head": BodyPart.HEAD,
                "upperBody": BodyPart.CHEST,
                "lowerBody": BodyPart.OTHER,
                "hands": BodyPart.OTHER,
            }
            if body_part := body_part_map.get(body_part_name):
                qualifiers.append(BodyPartQualifier(value=body_part))

        # Add set piece qualifiers
        if restart_type := attributes.get("restartType"):
            restart_type_map = {
                "throwIn": SetPieceType.THROW_IN,
                "goalKick": SetPieceType.GOAL_KICK,
                "freeKick": SetPieceType.FREE_KICK,
                "cornerKick": SetPieceType.CORNER_KICK,
                "kickOff": SetPieceType.KICK_OFF,
                "penaltyKick": SetPieceType.PENALTY,
            }
            if set_piece_type := restart_type_map.get(
                restart_type.get("name")
            ):
                qualifiers.append(SetPieceQualifier(value=set_piece_type))

        return {
            "result": result,
            "receiver_player": receiver_player,
            "receive_timestamp": receive_timestamp,
            "receiver_coordinates": receiver_coordinates,
            "qualifiers": qualifiers,
        }

    def _parse_event(
        self, raw_event: Dict, teams: List[Team], periods: List[Period]
    ) -> Optional[Dict]:
        """Parse an event based on its type."""
        event_type = raw_event["type"]
        if event_type in [
            "out",
            "goalkeeperAction",
            "stoppage",
            "aerialDuel",
            "foul",
            "deflection",
            "reception",
            "goalkeeperPossession",
        ]:
            team = None
        else:
            # Only try to find team for other event types
            team = next(
                (
                    team
                    for team in teams
                    if team.team_id == raw_event["team_id"]
                ),
                None,
            )
            if not team:
                logger.warning(
                    f"Team not found for event {raw_event['event_id']}"
                )
                return None

        period = next(
            (p for p in periods if p.id == raw_event["period"]), None
        )

        # Base event kwargs - only include fields from Event base class
        base_kwargs = {
            "event_id": raw_event["event_id"],
            "period": period,
            "timestamp": raw_event["timestamp"],
            "team": team,
            "player": next(
                (
                    p
                    for p in teams[0].players + teams[1].players
                    if p.player_id == raw_event["player_id"]
                ),
                None,
            ),
            "coordinates": raw_event.get("coordinates"),
            "ball_owning_team": team,
            "ball_state": BallState.ALIVE,
            "raw_event": raw_event,
            "related_event_ids": [],
            "freeze_frame": None,
            "qualifiers": [],  # Initialize empty qualifiers list
        }

        try:
            if event_type == "pass":
                pass_data = self._parse_pass(raw_event, team)
                if pass_data["result"] == PassResult.INCOMPLETE:
                    event_kwargs = {
                        "result": pass_data["result"],
                        "receiver_coordinates": pass_data[
                            "receiver_coordinates"
                        ],
                        "receive_timestamp": pass_data["receive_timestamp"],
                        "receiver_player": pass_data["receiver_player"],
                    }
                    base_kwargs["qualifiers"] = pass_data["qualifiers"]
                    return self.event_factory.build_pass(
                        **base_kwargs, **event_kwargs
                    )
                # Only include pass-specific fields
                event_kwargs = {
                    "receive_timestamp": pass_data["receive_timestamp"],
                    "receiver_player": pass_data["receiver_player"],
                    "receiver_coordinates": pass_data["receiver_coordinates"],
                    "result": pass_data["result"],
                }
                # Add qualifiers to base kwargs
                base_kwargs["qualifiers"] = pass_data["qualifiers"]
                return self.event_factory.build_pass(
                    **base_kwargs, **event_kwargs
                )

            elif event_type == "shot":
                shot_data = self._parse_shot(raw_event)
                event_kwargs = {
                    "result": shot_data["result"],
                    "result_coordinates": raw_event.get("goalmouthLocation"),
                }
                base_kwargs["qualifiers"] = shot_data["qualifiers"]
                return self.event_factory.build_shot(
                    **base_kwargs, **event_kwargs
                )

            elif event_type == "reception":
                return self.event_factory.build_recovery(
                    result=None, **base_kwargs
                )

            elif event_type == "clearance":
                return self.event_factory.build_clearance(
                    result=None, **base_kwargs
                )

            elif event_type == "take_on":
                return self.event_factory.build_take_on(
                    result=None, **base_kwargs
                )

            elif event_type == "substitution":
                player_in = team.get_player_by_id(
                    raw_event["players"].get("playerIn")
                )
                return self.event_factory.build_substitution(
                    replacement_player=player_in, result=None, **base_kwargs
                )
            elif event_type == "out":
                return self.event_factory.build_ball_out(
                    result=None, **base_kwargs
                )
            elif (
                event_type == "goalkeeperAction"
                or event_type == "goalkeeperPossession"
            ):
                return self.event_factory.build_goalkeeper_event(
                    result=None, **base_kwargs
                )
            elif event_type == "deflection":
                return self.event_factory.build_deflection(
                    result=None, **base_kwargs
                )
            elif event_type == "foul":
                penalty_awarded = raw_event["attributes"].get(
                    "penaltyAwarded", False
                )
                if penalty_awarded:
                    return self.event_factory.build_foul_committed(
                        penalty_awarded=True, result=None, **base_kwargs
                    )
                return self.event_factory.build_foul_committed(
                    result=None, **base_kwargs
                )
            # Add after the other elif statements in _parse_event method
            elif event_type == "aerialDuel":
                # Get players involved in the duel
                players = raw_event.get("players", {})
                contestor_one = next(
                    (
                        p
                        for p in teams[0].players + teams[1].players
                        if p.player_id == players.get("contestor_one")
                    ),
                    None,
                )
                contestor_two = next(
                    (
                        p
                        for p in teams[0].players + teams[1].players
                        if p.player_id == players.get("contestor_two")
                    ),
                    None,
                )
                winner = next(
                    (
                        p
                        for p in teams[0].players + teams[1].players
                        if p.player_id == players.get("winner")
                    ),
                    None,
                )

                return self.event_factory.build_duel(
                    # contestor_one=contestor_one,
                    # contestor_two=contestor_two,
                    # winner=winner,
                    result=None,
                    **base_kwargs,
                )

            logger.debug(f"Skipping unsupported event type: {event_type}")
            return None

        except Exception as e:
            logger.error(f"Error creating event {raw_event['event_id']}: {e}")
            return None

    def load_data(self, event_data: IO[bytes]) -> Dict[str, Dict]:
        """Load SecondSpectrum event data from JSONL format."""
        raw_events = {}

        def _iter():
            for line in event_data:
                line = line.strip().decode("ascii")
                if not line:
                    continue
                yield json.loads(line)

        for event in _iter():
            event_id = event["eventId"]
            raw_events[event_id] = {
                "event_id": event_id,
                "period": event["period"],
                "timestamp": timedelta(
                    milliseconds=float(event["startGameClock"])
                ),
                "team_id": event["primaryTeam"],
                "player_id": event["primaryPlayer"],
                "type": event["eventType"],
                "attributes": event.get("attributes", {}),
                "players": event.get("players", {}),
                "teams": event.get("teams", {}),
            }

            # Parse coordinates
            attrs = event.get("attributes", {})
            if location := attrs.get("location"):
                try:
                    raw_events[event_id]["coordinates"] = Point(
                        x=float(location[0]), y=float(location[1])
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to parse location for event {event_id}: {e}"
                    )

            if end_location := attrs.get("endLocation"):
                try:
                    raw_events[event_id]["end_coordinates"] = Point(
                        x=float(end_location[0]), y=float(end_location[1])
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to parse end location for event {event_id}: {e}"
                    )

        return raw_events

    def get_transformer(
        self, pitch_length=None, pitch_width=None, provider=None
    ):
        from kloppy.domain import MetricPitchDimensions, Dimension, Unit

        pitch_dimensions = MetricPitchDimensions(
            x_dim=Dimension(0, pitch_length if pitch_length else 105.0),
            y_dim=Dimension(0, pitch_width if pitch_width else 68.0),
            pitch_length=pitch_length if pitch_length else 105.0,
            pitch_width=pitch_width if pitch_width else 68.0,
            standardized=True,
        )

        return self.transformer_builder.build(
            provider=self.provider,
            dataset_type=DatasetType.EVENT,
            pitch_length=pitch_dimensions.x_dim.max,
            pitch_width=pitch_dimensions.y_dim.max,
        )

    def deserialize(
        self, inputs: SecondSpectrumEventDataInputs
    ) -> EventDataset:
        metadata = None
        # Initialize transformer
        self.transformer = self.get_transformer()
        first_byte = inputs.meta_data.read(1)
        with performance_logging("Loading  metadata", logger=logger):
            # The meta data can also be in JSON format. In that case
            # it also contains the 'additional metadata'.
            # First do a 'peek' to determine the char
            # Read the first byte and properly decode it
            inputs.meta_data.seek(0)
            first_byte = inputs.meta_data.read(1)
            if first_byte == b"{":
                inputs.meta_data.seek(0)
                metadata = json.loads(inputs.meta_data.read())

                frame_rate = float(metadata.get("fps", 25.0))
                pitch_length = float(
                    metadata["data"].get("pitchLength", 105.0)
                )
                pitch_width = float(metadata["data"].get("pitchWidth", 68.0))

                # Now initialize the transformer with the correct dimensions
                self.transformer = self.get_transformer(
                    pitch_length=pitch_length, pitch_width=pitch_width
                )
                periods = []
                legacy_meta = metadata

                metadata = metadata["data"]
                for period in metadata["periods"]:
                    start_frame_id = int(period["startFrameClock"])
                    end_frame_id = int(period["endFrameClock"])
                    if start_frame_id != 0 or end_frame_id != 0:
                        # Frame IDs are unix timestamps (in milliseconds)
                        periods.append(
                            Period(
                                id=int(period["number"]),
                                start_timestamp=timedelta(
                                    seconds=start_frame_id / frame_rate
                                ),
                                end_timestamp=timedelta(
                                    seconds=end_frame_id / frame_rate
                                ),
                            )
                        )
            else:
                logger.error(
                    "Metadata is not in JSON format. XML not implemented yet."
                )
                raise ValueError(
                    "Metadata is not in JSON format. XML not implemented yet."
                )
                # match = objectify.fromstring(
                #     first_byte + inputs.meta_data.read()
                # ).match
                # frame_rate = int(match.attrib["iFrameRateFps"])
                # pitch_size_height = float(match.attrib["fPitchXSizeMeters"])
                # pitch_size_width = float(match.attrib["fPitchYSizeMeters"])

                # periods = []
                # for period in match.iterchildren(tag="period"):
                #     start_frame_id = int(period.attrib["iStartFrame"])
                #     end_frame_id = int(period.attrib["iEndFrame"])
                #     if start_frame_id != 0 or end_frame_id != 0:
                #         # Frame IDs are unix timestamps (in milliseconds)
                #         periods.append(
                #             Period(
                #                 id=int(period.attrib["iId"]),
                #                 start_timestamp=timedelta(
                #                     seconds=start_frame_id / frame_rate
                #                 ),
                #                 end_timestamp=timedelta(
                #                     seconds=end_frame_id / frame_rate
                #                 ),
                #             )
                #         )

        with performance_logging("parse teams and players", logger=logger):
            # Create teams
            home_team = Team(
                team_id=metadata["homeTeam"]["id"],
                name=metadata["description"].split("-")[0].strip(),
                ground=Ground.HOME,
                # attributes={
                #     "opta_id": metadata["homeTeam"]["externalIds"]["optaId"]
                # }
            )
            away_team = Team(
                team_id=metadata["awayTeam"]["id"],
                name=metadata["description"]
                .split("-")[1]
                .split(":")[0]
                .strip(),
                ground=Ground.AWAY,
                # attributes={
                #     "opta_id": metadata["awayTeam"]["externalIds"]["optaId"]
                # }
            )
            teams = [home_team, away_team]

            # Create players
            for team, team_data in [
                (home_team, metadata["homeTeam"]),
                (away_team, metadata["awayTeam"]),
            ]:
                for player_data in team_data["players"]:
                    player = Player(
                        player_id=player_data["id"],
                        name=player_data["name"],
                        team=team,
                        jersey_no=int(player_data["number"]),
                        starting=player_data["position"] != "SUB",
                        starting_position=player_data["position"],
                    )
                    team.players.append(player)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            raw_events = self.load_data(inputs.event_data)
            periods = []
            for period_data in metadata["periods"]:
                start_ms = int(float(period_data["startFrameClock"]))
                end_ms = int(float(period_data["endFrameClock"]))

                period = Period(
                    id=int(period_data["number"]),
                    start_timestamp=timedelta(milliseconds=start_ms),
                    end_timestamp=timedelta(milliseconds=end_ms),
                )
                periods.append(period)

        # Parse events
        # In the deserialize method, replace the event parsing section:
        # Parse events
        with performance_logging("parse events", logger=logger):
            parsed_events = []

            for event_id, raw_event in raw_events.items():
                event = self._parse_event(raw_event, teams, periods)
                if event and self.should_include_event(event):
                    # Add common fields
                    event = self.transformer.transform_event(event)

                    # Transform coordinates if needed
                    if self.should_include_event(event):
                        event = self.transformer.transform_event(event)
                        parsed_events.append(event)

        # Create metadata
        metadata_obj = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            score=Score(
                home=metadata["homeScore"], away=metadata["awayScore"]
            ),
            frame_rate=float(
                legacy_meta["fps"] if "fps" in legacy_meta else 1000.0
            ),
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            provider=Provider.SECONDSPECTRUM,
            coordinate_system=self.transformer.get_to_coordinate_system(),
            date=datetime(
                metadata["year"],
                metadata["month"],
                metadata["day"],
                tzinfo=timezone.utc,
            ),
            game_id=metadata["id"],
        )

        return EventDataset(metadata=metadata_obj, records=parsed_events)
