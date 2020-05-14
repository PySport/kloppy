import re
from typing import Tuple, Dict


from kloppy.domain import (
    TrackingDataSet, DataSetFlag,
    AttackingDirection,
    Frame,
    Point,
    Team,
    BallState,
    Period,
    Orientation,
    PitchDimensions,
    Dimension,
    attacking_direction_from_frame,
)
from kloppy.infra.utils import Readable, performance_logging

from .meta_data import load_meta_data
from .reader import build_regex

from .. import TrackingDataSerializer

"""

def load_epts_tracking_data(meta_data_filename: str, raw_data_filename: str, options: dict = None) -> DataSet:
    serializer = EPTSSerializer()
    with open(meta_data_filename, "rb") as meta_data, \
            open(raw_data_filename, "rb") as raw_data:

        return serializer.deserialize(
            inputs={
                'meta_data': meta_data,
                'raw_data': raw_data
            },
            options=options
        )
"""


class EPTSSerializer(TrackingDataSerializer):

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "meta_data" not in inputs:
            raise ValueError("Please specify a value for 'meta_data'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")


    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> TrackingDataSet:
        """
        Deserialize EPTS tracking data into a `TrackingDataSet`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `meta_data` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the EPTS file. Possible options are
            `sample_rate` (float between 0 and 1) to specify the amount of
            frames that should be loaded.
        Returns
        -------
        data_set : TrackingDataSet
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
        >>>     data_set = serializer.deserialize(
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

        sample_rate = float(options.get('sample_rate', 1.0))

        with performance_logging("Loading metadata"):
            meta_data = load_meta_data(inputs['meta_data'])

        periods = meta_data.periods

        with performance_logging("Loading data"):
            # assume they are sorted
            pass



        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY else
            Orientation.FIXED_AWAY_HOME
        )

        return TrackingDataSet(
            flags=DataSetFlag.BALL_OWNING_TEAM | DataSetFlag.BALL_STATE,
            frame_rate=frame_rate,
            orientation=orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(-1 * pitch_size_width / 2, pitch_size_width / 2),
                y_dim=Dimension(-1 * pitch_size_height / 2, pitch_size_height / 2),
                x_per_meter=100,
                y_per_meter=100
            ),
            periods=periods,
            records=frames
        )

    def serialize(self, data_set: TrackingDataSet) -> Tuple[str, str]:
        raise NotImplementedError

