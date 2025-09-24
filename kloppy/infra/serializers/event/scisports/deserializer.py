import json
import logging
from datetime import timedelta
from typing import IO, NamedTuple, Optional, Dict, Any, List

from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    EventType,
    FormationType,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    PositionType,
    Provider,
    Team,
    Time,
    Point,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging

from . import specification as SS

logger = logging.getLogger(__name__)


class SciSportsInputs(NamedTuple):
    event_data: IO[bytes]


class SciSportsDeserializer(EventDataDeserializer[SciSportsInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.SCISPORTS

    def deserialize(
        self, inputs: SciSportsInputs, additional_metadata: dict = None
    ) -> EventDataset:
        if additional_metadata is None:
            additional_metadata = {}

        # Initialize coordinate system transformer
        self.transformer = self.get_transformer()

        # Load data from JSON file
        with performance_logging("load data", logger=logger):
            raw_data = self._load_data(inputs)

        # Create teams and players
        with performance_logging("parse teams and players", logger=logger):
            teams = self._create_teams_and_players(raw_data)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self._create_periods(raw_data)

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            raw_events = raw_data.get("data", [])

            # Pre-process substitution events to pair SUBBED_OUT with SUBBED_IN
            substitution_pairs = self._pair_substitution_events(
                raw_events, teams
            )

            for raw_event in raw_events:
                try:
                    # Skip SUBBED_IN events as they are handled by SUBBED_OUT events
                    if (
                        raw_event.get("baseTypeName") == "SUBSTITUTE"
                        and raw_event.get("subTypeName") == "SUBBED_IN"
                    ):
                        continue

                    event_objects = self._create_events(
                        raw_event, teams, periods, substitution_pairs
                    )
                    for event in event_objects:
                        if event and self.should_include_event(event):
                            # Transform event to the coordinate system
                            event = self.transformer.transform_event(event)
                            events.append(event)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse event {raw_event.get('eventId')}: {e}"
                    )
                    continue

        metadata = Metadata(
            teams=list(teams.values()),
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=Orientation.STATIC_HOME_AWAY,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            score=None,
            provider=Provider.SCISPORTS,
            coordinate_system=self.transformer.get_to_coordinate_system(),
            **additional_metadata,
        )

        return EventDataset(metadata=metadata, records=events)

    def _load_data(self, inputs: SciSportsInputs) -> Dict[str, Any]:
        """Load and parse the JSON data from SciSports"""
        return json.load(inputs.event_data)

    def _create_teams_and_players(
        self, raw_data: Dict[str, Any]
    ) -> Dict[str, Team]:
        """Create Team and Player objects from SciSports data"""
        teams = {}

        # Get unique teams from metadata and players
        home_team_id = raw_data["metaData"]["homeTeamId"]
        away_team_id = raw_data["metaData"]["awayTeamId"]

        # Parse starting formations from FORMATION events
        starting_formations = self._parse_starting_formations(raw_data)

        # Create teams with starting formations
        home_team = Team(
            team_id=str(home_team_id),
            name=raw_data["metaData"]["homeTeamName"],
            ground=Ground.HOME,
            starting_formation=starting_formations.get(str(home_team_id)),
        )

        away_team = Team(
            team_id=str(away_team_id),
            name=raw_data["metaData"]["awayTeamName"],
            ground=Ground.AWAY,
            starting_formation=starting_formations.get(str(away_team_id)),
        )

        teams[str(home_team_id)] = home_team
        teams[str(away_team_id)] = away_team

        # Identify starting players by analyzing substitution events
        starting_players = self._identify_starting_players(raw_data)

        # Parse starting positions from POSITION events (only for starting players)
        starting_positions = self._parse_player_starting_positions(raw_data)

        # Add players to teams
        for player_data in raw_data.get("players", []):
            team_id = str(player_data["teamId"])
            player_id = str(player_data["playerId"])
            if team_id in teams:
                is_starter = player_id in starting_players

                # Only use starting position from POSITION events if the player is a starter
                # Otherwise, starting_position should be None for substitutes
                starting_position = None
                if is_starter:
                    # Use position from STARTING_POSITION events if available, otherwise fallback to player metadata
                    position_id = starting_positions.get(
                        player_id, player_data.get("positionId", -1)
                    )
                    starting_position = SS.get_position_type(position_id)

                player = Player(
                    player_id=player_id,
                    team=teams[team_id],
                    jersey_no=player_data.get("shirtNumber"),
                    name=player_data.get("playerName"),
                    first_name=None,
                    last_name=None,
                    starting=is_starter,
                    starting_position=starting_position,
                )
                teams[team_id].players.append(player)

        return teams

    def _identify_starting_players(self, raw_data: Dict[str, Any]) -> set[str]:
        """Identify starting players by analyzing substitution events"""
        # Track first substitution event for each player
        first_sub_event = {}

        # Find all substitution events in chronological order
        substitution_events = []
        for event in raw_data.get("data", []):
            if event.get("baseTypeName") == "SUBSTITUTE":
                substitution_events.append(event)

        # Sort by timestamp to get chronological order
        substitution_events.sort(
            key=lambda x: (x.get("partId", 0), x.get("eventTime", 0))
        )

        # Track what each player's first substitution action was
        for event in substitution_events:
            player_id = str(event.get("playerId"))
            sub_type = event.get("subTypeName")

            # Only record the first substitution event for each player
            if player_id not in first_sub_event:
                first_sub_event[player_id] = sub_type

        # Get all player IDs
        all_players = set()
        for player_data in raw_data.get("players", []):
            all_players.add(str(player_data["playerId"]))

        # Starting players are:
        # 1. Players whose first substitution event was "SUBBED_OUT" (they started and were taken off)
        # 2. Players who were never involved in substitutions (played the full game)
        starting_players = set()
        for player_id in all_players:
            if player_id not in first_sub_event:
                # Never substituted - was a starter who played full game
                starting_players.add(player_id)
            elif first_sub_event[player_id] == "SUBBED_OUT":
                # First action was being taken off - must have started
                starting_players.add(player_id)
            # If first action was "SUBBED_IN", they didn't start

        return starting_players

    def _parse_player_starting_positions(
        self, raw_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """Parse player starting positions from POSITION events (only PLAYER_STARTING_POSITION)"""
        starting_positions = {}

        # Find PLAYER_STARTING_POSITION events to determine starting positions
        for event in raw_data.get("data", []):
            if (
                event.get("baseTypeName") == "POSITION"
                and event.get("subTypeId") == 1800
            ):  # PLAYER_STARTING_POSITION only
                player_id = str(event.get("playerId"))
                position_type_id = event.get("positionTypeId")
                starting_positions[player_id] = position_type_id

        return starting_positions

    def _parse_starting_formations(
        self, raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse starting formations from FORMATION events"""
        starting_formations = {}

        # Find TEAM_STARTING_FORMATION events
        for event in raw_data.get("data", []):
            if (
                event.get("baseTypeName") == "FORMATION"
                and event.get("subTypeId") == 1700
            ):  # TEAM_STARTING_FORMATION
                team_id = str(event.get("teamId"))
                formation_type_id = event.get("formationTypeId")

                # Use the formation mapping to get the kloppy FormationType
                formation_type = SS.get_formation_type(formation_type_id)
                starting_formations[team_id] = formation_type

        return starting_formations

    def _create_periods(self, raw_data: Dict[str, Any]) -> list[Period]:
        """Create Period objects from SciSports data"""
        periods = []

        # SciSports uses END_PERIOD events to mark period boundaries
        # We need to find the actual start and end times for each period
        period_data = {}
        period_end_times = {}

        # First pass: find END_PERIOD events for each period
        for event in raw_data.get("data", []):
            if (
                event.get("baseTypeName") == "PERIOD"
                and event.get("subTypeName") == "END_PERIOD"
            ):
                part_id = event.get("partId")
                end_time_ms = event.get("startTimeMs", 0)
                if part_id not in period_end_times:
                    period_end_times[part_id] = end_time_ms
                else:
                    # Take the latest end time if multiple END_PERIOD events exist
                    period_end_times[part_id] = max(
                        period_end_times[part_id], end_time_ms
                    )

        # Second pass: find the first event timestamp for each period (start time)
        for event in raw_data.get("data", []):
            part_id = event.get("partId")
            part_name = event.get("partName")
            start_time_ms = event.get("startTimeMs", 0)

            # Skip period events themselves from start time calculation
            if event.get("baseTypeName") == "PERIOD":
                continue

            if part_id:
                if part_id not in period_data:
                    period_data[part_id] = {
                        "id": part_id,
                        "name": part_name,
                        "start_time_ms": start_time_ms,
                    }
                else:
                    # Find the earliest non-period event time as period start
                    period_data[part_id]["start_time_ms"] = min(
                        period_data[part_id]["start_time_ms"], start_time_ms
                    )

        # Create periods sorted by ID with correct timestamps
        for part_id in sorted(period_data.keys()):
            if part_id in period_data and part_id in period_end_times:
                period_info = period_data[part_id]

                # Convert milliseconds to seconds for timedelta
                start_seconds = period_info["start_time_ms"] / 1000.0
                end_seconds = period_end_times[part_id] / 1000.0

                period = Period(
                    id=part_id,
                    start_timestamp=timedelta(seconds=start_seconds),
                    end_timestamp=timedelta(seconds=end_seconds),
                )
                periods.append(period)

        return periods

    def _pair_substitution_events(
        self, raw_events: List[Dict[str, Any]], teams: Dict[str, Team]
    ) -> Dict[str, Player]:
        """Pre-process substitution events to pair SUBBED_OUT with SUBBED_IN events"""
        substitution_pairs = (
            {}
        )  # Maps SUBBED_OUT event_id to replacement Player
        used_subbed_in_events = (
            set()
        )  # Track which SUBBED_IN events have been used

        # Group substitution events by team and timestamp to find proper pairs
        subbed_out_events = []
        subbed_in_events = []

        for event in raw_events:
            if event.get("baseTypeName") == "SUBSTITUTE":
                if event.get("subTypeName") == "SUBBED_OUT":
                    subbed_out_events.append(event)
                elif event.get("subTypeName") == "SUBBED_IN":
                    subbed_in_events.append(event)

        # Pair each SUBBED_OUT with the closest unused SUBBED_IN from the same team
        for out_event in subbed_out_events:
            out_team_id = out_event.get("teamId")
            out_time = out_event.get("startTimeMs", 0)

            best_match = None
            best_time_diff = float("inf")

            # Find the closest SUBBED_IN event from the same team that hasn't been used
            for in_event in subbed_in_events:
                in_event_id = in_event.get("eventId")
                if (
                    in_event.get("teamId") == out_team_id
                    and in_event_id not in used_subbed_in_events
                ):

                    in_time = in_event.get("startTimeMs", 0)
                    time_diff = abs(in_time - out_time)

                    # Accept if within 1 second (1000ms) and closest so far
                    if time_diff <= 1000 and time_diff < best_time_diff:
                        best_match = in_event
                        best_time_diff = time_diff

            # If we found a match, create the pairing
            if best_match:
                replacement_player_id = str(best_match.get("playerId"))
                team_id = str(best_match.get("teamId"))

                if team_id in teams:
                    team = teams[team_id]
                    replacement_player = team.get_player_by_id(
                        replacement_player_id
                    )
                    if replacement_player:
                        substitution_pairs[
                            str(out_event.get("eventId"))
                        ] = replacement_player
                        used_subbed_in_events.add(best_match.get("eventId"))

        return substitution_pairs

    def _create_events(
        self,
        raw_event: Dict[str, Any],
        teams: Dict[str, Team],
        periods: list[Period],
        substitution_pairs: Dict[str, Player] = None,
    ) -> List[Any]:
        """Create Event objects from raw SciSports event data using the new event classes"""
        # Use the event decoder to get the appropriate event class
        event_obj = SS.event_decoder(raw_event)

        if event_obj is None:
            # Skip metadata-only events (PERIOD, POSITION)
            return []

        # Set references to teams and periods
        event_obj.set_refs(teams, periods)

        # Check if we have valid team and player
        if not event_obj.team:
            logger.warning(f"Unknown team: {raw_event.get('teamId')}")
            return []

        if not event_obj.player and raw_event.get("playerId", -1) != -1:
            logger.warning(f"Unknown player: {raw_event.get('playerId')}")
            return []

        # For substitution events, check if we have a replacement player
        replacement_player = None
        if (
            substitution_pairs
            and raw_event.get("baseTypeName") == "SUBSTITUTE"
            and raw_event.get("subTypeName") == "SUBBED_OUT"
        ):

            event_id = str(raw_event.get("eventId"))
            replacement_player = substitution_pairs.get(event_id)

        # Deserialize the event using the event factory
        # Pass replacement player information for substitution events
        if replacement_player:
            events = event_obj.deserialize(
                self.event_factory, replacement_player=replacement_player
            )
        else:
            events = event_obj.deserialize(self.event_factory)

        return events
