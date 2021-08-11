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
    PitchDimensions,
    Dimension,
    attacking_direction_from_frame,
    Metadata,
    Ground,
    Player,
    build_coordinate_system,
    Provider,
    Transformer,
)

from kloppy.utils import Readable, performance_logging

from . import TrackingDataSerializer

logger = logging.getLogger(__name__)


class TRACABSerializer(TrackingDataSerializer):
    @classmethod
    def _frame_from_line(cls, teams, period, line, frame_rate):
        line = str(line)
        frame_id, players, ball = line.strip().split(":")[:3]

        players_coordinates = {}

        for player_data in players.split(";")[:-1]:
            team_id, target_id, jersey_no, x, y, speed = player_data.split(",")
            team_id = int(team_id)

            if team_id == 1:
                team = teams[0]
            elif team_id == 0:
                team = teams[1]
            else:
                # it's probably -1, but make sure it doesn't crash
                continue

            player = team.get_player_by_jersey_number(jersey_no)

            if not player:
                player = Player(
                    player_id=f"{team.ground}_{jersey_no}",
                    team=team,
                    jersey_no=int(jersey_no),
                )
                team.players.append(player)

            players_coordinates[player] = Point(float(x), float(y))

        (
            ball_x,
            ball_y,
            ball_z,
            ball_speed,
            ball_owning_team,
            ball_state,
        ) = ball.rstrip(";").split(",")[:6]

        frame_id = int(frame_id)

        if ball_owning_team == "H":
            ball_owning_team = teams[0]
        elif ball_owning_team == "A":
            ball_owning_team = teams[1]
        else:
            raise Exception(f"Unknown ball owning team: {ball_owning_team}")

        if ball_state == "Alive":
            ball_state = BallState.ALIVE
        elif ball_state == "Dead":
            ball_state = BallState.DEAD
        else:
            raise Exception(f"Unknown ball state: {ball_state}")

        return Frame(
            frame_id=frame_id,
            timestamp=frame_id / frame_rate - period.start_timestamp,
            ball_coordinates=Point3D(
                float(ball_x), float(ball_y), float(ball_z)
            ),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_coordinates=players_coordinates,
            period=period,
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for 'metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> TrackingDataset:
        """
        Deserialize TRACAB tracking data into a `TrackingDataset`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `metadata` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the TRACAB file. Possible options are
            `only_alive` (boolean) to specify that only frames with alive ball state
            should be loaded, or `sample_rate` (float between 0 and 1) to specify
            the amount of frames that should be loaded, `limit` to specify the max number of
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
        >>> serializer = TRACABSerializer()
        >>> with open("metadata.xml", "rb") as meta, \
        >>>      open("raw.dat", "rb") as raw:
        >>>     dataset = serializer.deserialize(
        >>>         inputs={
        >>>             'metadata': meta,
        >>>             'raw_data': raw
        >>>         },
        >>>         options={
        >>>             'only_alive': True,
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get("sample_rate", 1.0))
        limit = int(options.get("limit", 0))
        only_alive = bool(options.get("only_alive", True))

        # TODO: also used in Metrica, extract to a method
        home_team = Team(team_id="home", name="home", ground=Ground.HOME)
        away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        teams = [home_team, away_team]

        with performance_logging("Loading metadata", logger=logger):
            match = objectify.fromstring(inputs["metadata"].read()).match
            frame_rate = int(match.attrib["iFrameRateFps"])
            pitch_size_width = float(match.attrib["fPitchXSizeMeters"])
            pitch_size_height = float(match.attrib["fPitchYSizeMeters"])

            periods = []
            for period in match.iterchildren(tag="period"):
                start_frame_id = int(period.attrib["iStartFrame"])
                end_frame_id = int(period.attrib["iEndFrame"])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=int(period.attrib["iId"]),
                            start_timestamp=start_frame_id / frame_rate,
                            end_timestamp=end_frame_id / frame_rate,
                        )
                    )

        with performance_logging("Loading data", logger=logger):

            from_coordinate_system = build_coordinate_system(
                Provider.TRACAB,
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
                sample = 1.0 / sample_rate

                for line_ in inputs["raw_data"].readlines():
                    line_ = line_.strip().decode("ascii")
                    if not line_:
                        continue

                    frame_id = int(line_[:10].split(":", 1)[0])
                    if only_alive and not line_.endswith("Alive;:"):
                        continue

                    for period_ in periods:
                        if period_.contains(frame_id / frame_rate):
                            if n % sample == 0:
                                yield period_, line_
                            n += 1

            frames = []
            for n, (period, line) in enumerate(_iter()):
                frame = self._frame_from_line(teams, period, line, frame_rate)

                frame = transformer.transform_frame(frame)

                frames.append(frame)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(
                            frame
                        )
                    )

                if limit and n >= limit:
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
            provider=Provider.TRACAB,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=to_coordinate_system,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
