import json
import logging
import re
import warnings
from dataclasses import replace
from datetime import timedelta
from typing import IO, Dict, List, NamedTuple, Optional, Tuple, Union

from kloppy.domain import (
    BallState,
    CardEvent,
    CardType,
    DatasetFlag,
    Event,
    EventDataset,
    EventType,
    FormationType,
    Ground,
    Metadata,
    Orientation,
    PassQualifier,
    PassType,
    Period,
    Player,
    PlayerOffEvent,
    PositionType,
    Provider,
    ShotResult,
    SubstitutionEvent,
    Team,
)
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.infra.serializers.event.impect.helpers import (
    insert,
    parse_cumulative_timestamp,
    parse_timestamp,
)
from kloppy.infra.serializers.event.impect.specification import (
    create_impect_events,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

position_types_mapping: Dict[Tuple[str, str], PositionType] = {
    ("GOALKEEPER", "CENTRE"): PositionType.Goalkeeper,
    ("LEFT_WINGBACK_DEFENDER", "LEFT"): PositionType.LeftWingBack,
    ("CENTRAL_DEFENDER", "CENTRE_LEFT"): PositionType.LeftCenterBack,
    ("CENTRAL_DEFENDER", "CENTRE"): PositionType.CenterBack,
    ("CENTRAL_DEFENDER", "CENTRE_RIGHT"): PositionType.RightCenterBack,
    ("RIGHT_WINGBACK_DEFENDER", "RIGHT"): PositionType.RightWingBack,
    ("LEFT_WINGER", "LEFT"): PositionType.LeftWing,
    ("DEFENSE_MIDFIELD", "CENTRE_LEFT"): PositionType.LeftDefensiveMidfield,
    ("DEFENSE_MIDFIELD", "CENTRE"): PositionType.CenterDefensiveMidfield,
    ("DEFENSE_MIDFIELD", "CENTRE_RIGHT"): PositionType.RightDefensiveMidfield,
    ("RIGHT_WINGER", "RIGHT"): PositionType.RightWing,
    (
        "CENTRAL_MIDFIELD",
        "LEFT",
    ): PositionType.LeftCentralMidfield,  # TBD whether this exists
    ("CENTRAL_MIDFIELD", "CENTRE_LEFT"): PositionType.LeftCentralMidfield,
    (
        "CENTRAL_MIDFIELD",
        "CENTRE",
    ): PositionType.CenterMidfield,  # TBD whether this exists
    ("CENTRAL_MIDFIELD", "CENTRE_RIGHT"): PositionType.RightCentralMidfield,
    (
        "CENTRAL_MIDFIELD",
        "RIGHT",
    ): PositionType.RightCentralMidfield,  # TBD whether this exists
    ("ATTACKING_MIDFIELD", "CENTRE_LEFT"): PositionType.LeftAttackingMidfield,
    ("ATTACKING_MIDFIELD", "CENTRE"): PositionType.CenterAttackingMidfield,
    (
        "ATTACKING_MIDFIELD",
        "CENTRE_RIGHT",
    ): PositionType.RightAttackingMidfield,
    ("CENTER_FORWARD", "LEFT"): PositionType.LeftForward,
    ("CENTER_FORWARD", "CENTRE_LEFT"): PositionType.Striker,
    ("CENTER_FORWARD", "CENTRE"): PositionType.Striker,
    ("CENTER_FORWARD", "CENTRE_RIGHT"): PositionType.Striker,
    ("CENTER_FORWARD", "RIGHT"): PositionType.RightForward,
}


class ImpectInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]
    squads_data: Optional[IO[bytes]] = None
    players_data: Optional[IO[bytes]] = None


class ImpectDeserializer(EventDataDeserializer[ImpectInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.IMPECT

    def deserialize(self, inputs: ImpectInputs) -> EventDataset:
        # Initialize coordinate system transformer
        self.transformer = self.get_transformer()

        with performance_logging("load data", logger=logger):
            metadata = json.load(inputs.meta_data)
            raw_events = json.load(inputs.event_data)

            # Load optional squads and players data for enrichment
            squads_lookup = None
            players_lookup = None
            if inputs.squads_data:
                squads_data = json.load(inputs.squads_data)
                squads_lookup = {
                    str(squad["id"]): squad for squad in squads_data
                }
            if inputs.players_data:
                players_data = json.load(inputs.players_data)
                players_lookup = {
                    str(player["id"]): player for player in players_data
                }

        with performance_logging("parse data", logger=logger):
            teams = self.create_teams_and_players(
                metadata, squads_lookup, players_lookup
            )

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            impect_events = create_impect_events(raw_events)
            for impect_event in impect_events.values():
                new_events = impect_event.set_refs(
                    periods, teams, impect_events
                ).deserialize(self.event_factory, teams)
                for event in new_events:
                    if self.should_include_event(event):
                        # Transform event to the coordinate system
                        event = self.transformer.transform_event(event)
                        events.append(event)

        self.mark_events_as_assists(events)
        substitution_events = self.parse_substitutions(
            teams, periods, metadata, events
        )
        for sub_event in substitution_events:
            insert(sub_event, events)

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            provider=Provider.IMPECT,
            coordinate_system=self.transformer.get_to_coordinate_system(),
        )
        dataset = EventDataset(metadata=metadata, records=events)

        return dataset

    @staticmethod
    def create_teams_and_players(
        metadata: Dict,
        squads_lookup: Optional[Dict] = None,
        players_lookup: Optional[Dict] = None,
    ) -> List[Team]:
        def create_team(team_info: Dict, ground: Ground) -> Team:
            starting_formation_stripped = re.sub(
                r"[^0-9-]", "", team_info["startingFormation"]
            )
            try:
                starting_formation = FormationType(starting_formation_stripped)
            except ValueError:
                warnings.warn(
                    f"Unknown starting formation {team_info['startingFormation']}, defaulting to UNKNOWN"
                )
                starting_formation = FormationType.UNKNOWN

            # Get team name from squads lookup if available
            team_id_str = str(team_info["id"])
            team_name = ""
            if squads_lookup and team_id_str in squads_lookup:
                team_name = squads_lookup[team_id_str].get("name", "")

            team = Team(
                team_id=team_id_str,
                name=team_name,
                ground=ground,
                starting_formation=starting_formation,
            )
            player_starting_positions = {}
            for player_starting_info in team_info["startingPositions"]:
                position_key = (
                    player_starting_info["position"],
                    player_starting_info["positionSide"],
                )
                try:
                    position = position_types_mapping[position_key]
                except KeyError:
                    warnings.warn(
                        f"Unknown position {position_key}, defaulting to Unknown"
                    )
                    position = PositionType.Unknown
                player_starting_positions[
                    player_starting_info["playerId"]
                ] = position

            players = []
            for player in team_info["players"]:
                player_id_str = str(player["id"])
                starting_position = player_starting_positions.get(player["id"])

                # Get player name from players lookup if available
                player_name = ""
                if players_lookup and player_id_str in players_lookup:
                    player_data = players_lookup[player_id_str]
                    player_name = (
                        player_data.get("commonname")
                        or f"{player_data.get('firstname', '')} {player_data.get('lastname', '')}".strip()
                    )

                players.append(
                    Player(
                        player_id=player_id_str,
                        team=team,
                        name=player_name,
                        jersey_no=player["shirtNumber"],
                        starting_position=starting_position,
                        starting=True if starting_position else False,
                    )
                )

            team.players = players

            return team

        home_team = create_team(metadata["squadHome"], Ground.HOME)
        away_team = create_team(metadata["squadAway"], Ground.AWAY)

        return [home_team, away_team]

    @staticmethod
    def create_periods(raw_events: List[Dict]) -> List[Period]:
        periods = []

        for idx, raw_event in enumerate(raw_events):
            next_period_id = None
            if (idx + 1) < len(raw_events):
                next_event = raw_events[idx + 1]
                next_period_id = next_event["periodId"]

            timestamp, _ = parse_cumulative_timestamp(
                raw_event["gameTime"]["gameTime"]
            )
            period_id = raw_event["periodId"]

            if len(periods) == 0 or periods[-1].id != period_id:
                periods.append(
                    Period(
                        id=period_id,
                        start_timestamp=(
                            timedelta(seconds=0)
                            if len(periods) == 0
                            else periods[-1].end_timestamp
                        ),
                        end_timestamp=None,
                    )
                )

            if next_period_id != period_id:
                # Set period end to cumulative timestamp
                periods[-1] = replace(
                    periods[-1],
                    end_timestamp=periods[-1].start_timestamp + timestamp,
                )

        return periods

    def parse_substitutions(
        self,
        teams: List[Team],
        periods: List[Period],
        metadata: Dict,
        events: List[Event],
    ) -> List[Union[SubstitutionEvent, PlayerOffEvent]]:
        substitutions: List[Union[SubstitutionEvent, PlayerOffEvent]] = []
        squads = [metadata["squadHome"], metadata["squadAway"]]

        SUB_WINDOW = timedelta(seconds=30)

        # Collect all players who received red cards or second yellow
        red_card_players = []
        for event in events:
            if isinstance(event, CardEvent):
                if event.card_type in [CardType.RED, CardType.SECOND_YELLOW]:
                    red_card_players.append(event.player)

        for team, squad in zip(teams, squads):
            # Parse all substitution records
            all_subs = []
            for sub in squad["substitutions"]:
                is_in = sub["fromPosition"] == "BANK"
                is_out = sub["toPosition"] == "BANK"
                if not (is_in or is_out):
                    continue

                ts, period_id = parse_timestamp(sub["gameTime"]["gameTime"])
                player = team.get_player_by_id(sub["playerId"])
                period = periods[period_id - 1]

                position = PositionType.Unknown
                if is_in:
                    position_key = (sub["toPosition"], sub["positionSide"])
                    try:
                        position = position_types_mapping[position_key]
                    except KeyError:
                        warnings.warn(
                            f"Unknown substitution position {position_key}, defaulting to Unknown"
                        )

                all_subs.append(
                    {
                        "is_out": is_out,
                        "player": player,
                        "position": position,
                        "timestamp": ts,
                        "period": period,
                    }
                )

            # Separate into OUTs and INs (preserve original order)
            outs = [s for s in all_subs if s["is_out"]]
            ins = [s for s in all_subs if not s["is_out"]]

            # Sort both by period and timestamp (Python's sort is stable)
            outs.sort(key=lambda x: (x["period"].id, x["timestamp"]))
            ins.sort(key=lambda x: (x["period"].id, x["timestamp"]))

            # For each OUT, find matching IN
            for out_sub in outs:
                # Check if player had red card - if so, skip and remove from list
                if out_sub["player"] in red_card_players:
                    red_card_players.remove(out_sub["player"])
                    continue

                # Find first IN within time window and pop it
                found_match = False
                for in_idx, in_sub in enumerate(ins):
                    # Must be same period
                    if in_sub["period"] != out_sub["period"]:
                        continue

                    # Must be within time window
                    time_diff = abs(in_sub["timestamp"] - out_sub["timestamp"])
                    if time_diff <= SUB_WINDOW:
                        # Found match!
                        eid = f"substitution-{out_sub['player'].player_id}-{in_sub['player'].player_id}"
                        substitutions.append(
                            self.event_factory.build_substitution(
                                event_id=eid,
                                ball_owning_team=None,
                                ball_state=BallState.DEAD,
                                coordinates=None,
                                player=out_sub["player"],
                                replacement_player=in_sub["player"],
                                position=in_sub["position"],
                                team=team,
                                period=in_sub["period"],
                                timestamp=in_sub["timestamp"],
                                result=None,
                                raw_event=None,
                                qualifiers=None,
                            )
                        )
                        # Remove the matched IN so it can't be used again
                        ins.pop(in_idx)
                        found_match = True
                        break

                if not found_match:
                    # Player went OFF without replacement - emit PlayerOff event
                    eid = f"player-off-{out_sub['player'].player_id}"
                    substitutions.append(
                        self.event_factory.build_player_off(
                            event_id=eid,
                            ball_owning_team=None,
                            ball_state=BallState.DEAD,
                            coordinates=None,
                            player=out_sub["player"],
                            team=team,
                            period=out_sub["period"],
                            timestamp=out_sub["timestamp"],
                            result=None,
                            qualifiers=None,
                            raw_event=None,
                        )
                    )

        # Check if there are any red card players still on the pitch
        if red_card_players:
            player_names = ", ".join([str(p) for p in red_card_players])
            warnings.warn(
                f"Players received red/second yellow card but have no substitution OUT record: {player_names}"
            )

        return substitutions

    @staticmethod
    def mark_events_as_assists(events: List[Event]):
        for ix, event in enumerate(events):
            for i in range(1, 3):
                if event.event_type == EventType.SHOT and ix > i - 1:
                    potential_assist_event = events[ix - i]
                    is_pass_event = (
                        potential_assist_event.event_type == EventType.PASS
                    )
                    is_same_team_event = (
                        event.team == potential_assist_event.team
                    )
                    if is_pass_event and is_same_team_event:
                        potential_assist_event.qualifiers.append(
                            PassQualifier(value=PassType.SHOT_ASSIST)
                        )
                        if event.result == ShotResult.GOAL:
                            potential_assist_event.qualifiers.append(
                                PassQualifier(value=PassType.ASSIST)
                            )
                        break
