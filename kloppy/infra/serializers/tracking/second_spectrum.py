import json
import logging
from typing import Tuple, Dict

from lxml import objectify

from kloppy.domain import (
    TrackingDataset,
    DatasetFlag,
    AttackingDirection,
    Frame,
    Point,
    Point3D,
    Team,
    BallState,
    Period,
    Provider,
    Orientation,
    attacking_direction_from_frame,
    Metadata,
    Ground,
    Player,
    build_coordinate_system,
    Provider,
    Transformer,
    PlayerData,
)

from kloppy.utils import Readable, performance_logging

from . import TrackingDataSerializer

logger = logging.getLogger(__name__)


class SecondSpectrumSerializer(TrackingDataSerializer):
    @classmethod
    def _frame_from_framedata(cls, teams, period, frame_data):

        frame_id = frame_data["frameIdx"]
        frame_timestamp = frame_data["gameClock"]

        ball_x, ball_y, ball_z = frame_data["ball"]["xyz"]
        ball_state = BallState.ALIVE if frame_data["live"] else BallState.DEAD
        ball_owning_team = (
            teams[0] if frame_data["lastTouch"] == "home" else teams[1]
        )

        players_data = {}
        for team, team_str in zip(teams, ["homePlayers", "awayPlayers"]):
            for player_data in frame_data[team_str]:

                jersey_no = player_data["number"]
                x, y, _ = player_data["xyz"]
                player = team.get_player_by_jersey_number(jersey_no)

                if not player:
                    player = Player(
                        player_id=player_data["playerId"],
                        team=team,
                        jersey_no=int(jersey_no),
                    )
                    team.players.append(player)

                players_data[player] = PlayerData(
                    coordinates=Point(float(x), float(y))
                )

        return Frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=Point3D(
                float(ball_x), float(ball_y), float(ball_z)
            ),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_data=players_data,
            period=period,
            other_data={},
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "xml_metadata" not in inputs:
            raise ValueError("Please specify a value for 'xml_metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> TrackingDataset:
        """
        Deserialize Second Spectrum tracking data into a `TrackingDataset`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'jsonl' formatted raw data from Second Spectrum. input `xml_metadata` 
            should point to the xml metadata. input `json_metadata` is optional and should point 
            to the 'jsonl' metadata file if it's available.
        options : dict
            Options for deserialization of the Second Spectrum file. Possible options are
            `only_alive` (boolean) to specify that only frames with alive ball state
            should be loaded, or `sample_rate` (float between 0 and 1) to specify
            the amount of frames that should be loaded, `limit` to specify the maximum number of
            frames that will be returned.
        Returns
        -------
        dataset : TrackingDataset
        Raises
        ------
        -

        See Also
        --------

        Examples
        --------
        >>> serializer = SecondSpectrumSerializer()
        >>> with open('metadata.xml', "rb") as metadata, \
        >>>         open('metadata.jsonl', "rb") as json_metadata, \
        >>>         open('rawdata.jsonl', "rb") as raw_data:
        >>>     dataset = serializer.deserialize(
        >>>         inputs={
        >>>             "xml_metadata": metadata, 
        >>>             "raw_data": raw_data, 
        >>>             "json_metadata" : json_metadata
        >>>         },
        >>>         options={
        >>>             "only_alive": False,
        >>>             "limit": 4000,
        >>>             "sample_rate" : 0.1
        >>>         },
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get("sample_rate", 1.0))
        limit = int(options.get("limit", 0))
        only_alive = bool(options.get("only_alive", True))

        # Handles the XML metadata that contains the pitch dimensions and frame info
        with performance_logging("Loading XML metadata", logger=logger):
            match = objectify.fromstring(inputs["xml_metadata"].read()).match
            frame_rate = int(match.attrib["iFrameRateFps"])
            pitch_size_height = float(match.attrib["fPitchYSizeMeters"])
            pitch_size_width = float(match.attrib["fPitchXSizeMeters"])

            periods = []
            for period in match.iterchildren(tag="period"):
                start_frame_id = int(period.attrib["iStartFrame"])
                end_frame_id = int(period.attrib["iEndFrame"])
                if start_frame_id != 0 or end_frame_id != 0:
                    # Frame IDs are unix timestamps (in milliseconds)
                    periods.append(
                        Period(
                            id=int(period.attrib["iId"]),
                            start_timestamp=start_frame_id,
                            end_timestamp=end_frame_id,
                        )
                    )

        # Default team initialisation
        home_team = Team(team_id="home", name="home", ground=Ground.HOME)
        away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        teams = [home_team, away_team]

        if "json_metadata" in inputs:
            with performance_logging("Loading JSON metadata", logger=logger):
                try:
                    metadata = json.loads(inputs["json_metadata"].read())

                    home_team_id = metadata["homeOptaId"]
                    away_team_id = metadata["awayOptaId"]

                    # Tries to parse (short) team names from the description string
                    try:
                        home_name = (
                            metadata["description"].split("-")[0].strip()
                        )
                        away_name = (
                            metadata["description"]
                            .split("-")[1]
                            .split(":")[0]
                            .strip()
                        )
                    except:
                        home_name, away_name = "home", "away"

                    teams[0].team_id = home_team_id
                    teams[0].name = home_name
                    teams[1].team_id = away_team_id
                    teams[1].name = away_name

                    for team, team_str in zip(
                        teams, ["homePlayers", "awayPlayers"]
                    ):
                        for player_data in metadata[team_str]:

                            # We use the attributes field of Player to store the extra IDs provided by the
                            # metadata. We designate the player_id to be the 'optaId' field as this is what's
                            # used as 'player_id' in the raw frame data file
                            player_attributes = {
                                k: v
                                for k, v in player_data.items()
                                if k in ["ssiId", "optaUuid"]
                            }

                            player = Player(
                                player_id=player_data["optaId"],
                                name=player_data["name"],
                                starting=player_data["position"] != "SUB",
                                position=player_data["position"],
                                team=team,
                                jersey_no=int(player_data["number"]),
                                attributes=player_attributes,
                            )
                            team.players.append(player)

                except:  # TODO: More specific exception
                    logging.warning(
                        "Optional JSON Metadata is malformed. Continuing without"
                    )

        # Handles the tracking frame data
        with performance_logging("Loading data", logger=logger):

            from_coordinate_system = build_coordinate_system(
                Provider.SECONDSPECTRUM,
                length=pitch_size_width,
                width=pitch_size_height,
            )

            to_coordinate_system = build_coordinate_system(
                options.get("coordinate_system", Provider.KLOPPY),
                length=pitch_size_width,
                width=pitch_size_height,
            )

            transformer = Transformer(
                from_coordinate_system=from_coordinate_system,
                to_coordinate_system=to_coordinate_system,
            )

            def _iter():
                n = 0
                sample = 1 / sample_rate

                for line_ in inputs["raw_data"].readlines():
                    line_ = line_.strip().decode("ascii")
                    if not line_:
                        continue

                    # Each line is just json so we just parse it
                    frame_data = json.loads(line_)

                    if only_alive and not frame_data["live"]:
                        continue

                    if n % sample == 0:
                        yield frame_data

                    n += 1

            frames = []
            for n, frame_data in enumerate(_iter()):
                period = periods[frame_data["period"] - 1]

                frame = self._frame_from_framedata(teams, period, frame_data)
                frame = transformer.transform_frame(frame)
                frames.append(frame)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(
                            frame
                        )
                    )

                if limit and n + 1 >= limit:
                    break

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY
            else Orientation.FIXED_AWAY_HOME
        )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=to_coordinate_system.pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.SECONDSPECTRUM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=to_coordinate_system,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
