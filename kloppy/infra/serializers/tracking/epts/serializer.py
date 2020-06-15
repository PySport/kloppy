import logging
from typing import Tuple, Dict

from kloppy.domain import (
    TrackingDataset,
    DatasetFlag,
    AttackingDirection,
    Frame,
    Point,
    Team,
    Orientation,
    attacking_direction_from_frame,
)
from kloppy.infra.utils import Readable, performance_logging

from .meta_data import load_meta_data, EPTSMetaData
from .reader import read_raw_data

from .. import TrackingDataSerializer

logger = logging.getLogger(__name__)


class EPTSSerializer(TrackingDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "meta_data" not in inputs:
            raise ValueError("Please specify a value for 'meta_data'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    @staticmethod
    def _frame_from_row(row: dict, meta_data: EPTSMetaData) -> Frame:
        timestamp = row["timestamp"]
        if meta_data.periods and row["period_id"]:
            # might want to search for it instead
            period = meta_data.periods[row["period_id"] - 1]
        else:
            period = None

        home_team_player_positions = {}
        away_team_player_positions = {}
        for player in meta_data.players:
            if player.team == Team.HOME:
                if f"player_home_{player.jersey_no}_x" in row:
                    home_team_player_positions[player.jersey_no] = Point(
                        x=row[f"player_home_{player.jersey_no}_x"],
                        y=row[f"player_home_{player.jersey_no}_y"],
                    )
            elif player.team == Team.AWAY:
                if f"player_away_{player.jersey_no}_x" in row:
                    away_team_player_positions[player.jersey_no] = Point(
                        x=row[f"player_away_{player.jersey_no}_x"],
                        y=row[f"player_away_{player.jersey_no}_y"],
                    )

        return Frame(
            frame_id=row["frame_id"],
            timestamp=timestamp,
            ball_owning_team=None,
            ball_state=None,
            period=period,
            home_team_player_positions=home_team_player_positions,
            away_team_player_positions=away_team_player_positions,
            ball_position=Point(x=row["ball_x"], y=row["ball_y"]),
        )

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> TrackingDataset:
        """
        Deserialize EPTS tracking data into a `TrackingDataset`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `meta_data` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the EPTS file. Possible options are
            `sample_rate` (float between 0 and 1) to specify the amount of
            frames that should be loaded, `limit` to specify the max number of
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
        >>> serializer = EPTSSerializer()
        >>> with open("metadata.xml", "rb") as meta, \
        >>>      open("raw.dat", "rb") as raw:
        >>>     dataset = serializer.deserialize(
        >>>         inputs={
        >>>             'meta_data': meta,
        >>>             'raw_data': raw
        >>>         },
        >>>         options={
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get("sample_rate", 1.0))
        limit = int(options.get("limit", 0))

        with performance_logging("Loading metadata", logger=logger):
            meta_data = load_meta_data(inputs["meta_data"])

        periods = meta_data.periods

        with performance_logging("Loading data", logger=logger):
            # assume they are sorted
            frames = [
                self._frame_from_row(row, meta_data)
                for row in read_raw_data(
                    raw_data=inputs["raw_data"],
                    meta_data=meta_data,
                    sensor_ids=[
                        "position"
                    ],  # we don't care about other sensors
                    sample_rate=sample_rate,
                    limit=limit,
                )
            ]

        if periods:
            start_attacking_direction = periods[0].attacking_direction
        elif frames:
            start_attacking_direction = attacking_direction_from_frame(
                frames[0]
            )
        else:
            start_attacking_direction = None

        orientation = (
            (
                Orientation.FIXED_HOME_AWAY
                if start_attacking_direction == AttackingDirection.HOME_AWAY
                else Orientation.FIXED_AWAY_HOME
            )
            if start_attacking_direction != AttackingDirection.NOT_SET
            else None
        )

        return TrackingDataset(
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            frame_rate=meta_data.frame_rate,
            orientation=orientation,
            pitch_dimensions=meta_data.pitch_dimensions,
            periods=periods,
            records=frames,
        )

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
