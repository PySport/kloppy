from typing import Tuple, Dict

from lxml import objectify

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
from .models import DataFormatSpecification, PlayerChannel, Player

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

    def _load_meta_data(self, meta_data: Readable):
        meta_data = objectify.fromstring(meta_data.read())

        score_path = objectify.ObjectPath("Metadata.Sessions.Session[0].MatchParameters.Score")
        score_elm = score_path.find(meta_data.find('Metadata'))
        team_map = {
            score_elm.attrib['idLocalTeam']: Team.HOME,
            score_elm.attrib['idVisitingTeam']: Team.AWAY
        }

        players = list(
            map(
                lambda x: Player(
                    team=team_map[x.attrib['teamId']],
                    jersey_no=str(x.find('ShirtNumber')),
                    player_id=x.attrib['id']
                ),
                (
                    meta_data
                    .find('Metadata').find('Players')
                    .iterchildren(tag='Player')
                )
            )
        )

        a = 1

        data_specs = list(
            map(
                DataFormatSpecification.from_xml_element,
                (
                    meta_data
                    .find('DataFormatSpecifications')
                    .iterchildren(tag='DataFormatSpecification')
                )
            )
        )

        player_channels = [
            PlayerChannel(player_channel_id='player1_x', channel_id='x',
                          player=Player(team=Team.HOME, jersey_no='23', player_id=None)),
            PlayerChannel(player_channel_id='player1_y', channel_id='y',
                          player=Player(team=Team.HOME, jersey_no='23', player_id=None)),
            PlayerChannel(player_channel_id='player1_z', channel_id='z',
                          player=Player(team=Team.HOME, jersey_no='23', player_id=None))

        ]

        player_channel_map = {
            player_channel.player_channel_id: player_channel
            for player_channel in player_channels
        }

        data_specs[0].split_register.to_regex(
            player_channel_map=player_channel_map
        )
        a = 1

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
        >>>             'only_alive': True,
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get('sample_rate', 1.0))
        only_alive = bool(options.get('only_alive', True))

        with performance_logging("Loading metadata"):
            self._load_meta_data(inputs['meta_data'])


            a = 1

            frame_rate = int(match.attrib['iFrameRateFps'])
            pitch_size_width = float(match.attrib['fPitchXSizeMeters'])
            pitch_size_height = float(match.attrib['fPitchYSizeMeters'])

            periods = []
            for period in match.iterchildren(tag='period'):
                start_frame_id = int(period.attrib['iStartFrame'])
                end_frame_id = int(period.attrib['iEndFrame'])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=int(period.attrib['iId']),
                            start_timestamp=start_frame_id / frame_rate,
                            end_timestamp=end_frame_id / frame_rate
                        )
                    )

        with performance_logging("Loading data"):
            def _iter():
                n = 0
                sample = 1. / sample_rate

                for line in inputs['raw_data'].readlines():
                    line = line.strip().decode("ascii")
                    if not line:
                        continue

                    frame_id = int(line[:10].split(":", 1)[0])
                    if only_alive and not line.endswith("Alive;:"):
                        continue

                    for period in periods:
                        if period.contains(frame_id / frame_rate):
                            if n % sample == 0:
                                yield period, line
                            n += 1

            frames = []
            for period, line in _iter():
                frame = self._frame_from_line(
                    period,
                    line,
                    frame_rate
                )

                frames.append(frame)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(frame)
                    )

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

