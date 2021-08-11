import os

from pandas import DataFrame
from pandas.testing import assert_frame_equal

from kloppy import (
    to_pandas,
    load_metrica_tracking_data,
    load_tracab_tracking_data,
    transform,
    OptaSerializer,
    TRACABSerializer,
)
from kloppy.domain import (
    Period,
    DatasetFlag,
    Point,
    AttackingDirection,
    TrackingDataset,
    PitchDimensions,
    Dimension,
    Orientation,
    Provider,
    Frame,
    EventDataset,
    PassEvent,
    Metadata,
    Team,
    Ground,
    Player,
)
from kloppy.domain.models.common import DatasetType


class TestHelpers:
    def test_load_metrica_tracking_data(self):
        base_dir = os.path.dirname(__file__)
        dataset = load_metrica_tracking_data(
            f"{base_dir}/files/metrica_home.csv",
            f"{base_dir}/files/metrica_away.csv",
        )
        assert len(dataset.records) == 6
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.provider == Provider.METRICA
        assert dataset.dataset_type == DatasetType.TRACKING

    def test_load_tracab_tracking_data(self):
        base_dir = os.path.dirname(__file__)
        dataset = load_tracab_tracking_data(
            f"{base_dir}/files/tracab_meta.xml",
            f"{base_dir}/files/tracab_raw.dat",
        )
        assert len(dataset.records) == 5  # only alive=True
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING

    def _get_tracking_dataset(self):
        home_team = Team(team_id="home", name="home", ground=Ground.HOME)
        away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        teams = [home_team, away_team]

        periods = [
            Period(
                id=1,
                start_timestamp=0.0,
                end_timestamp=10.0,
                attacking_direction=AttackingDirection.HOME_AWAY,
            ),
            Period(
                id=2,
                start_timestamp=15.0,
                end_timestamp=25.0,
                attacking_direction=AttackingDirection.AWAY_HOME,
            ),
        ]
        metadata = Metadata(
            flags=~(DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE),
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 100), y_dim=Dimension(-50, 50)
            ),
            orientation=Orientation.HOME_TEAM,
            frame_rate=25,
            periods=periods,
            teams=teams,
            score=None,
            provider=None,
            coordinate_system=None,
        )

        tracking_data = TrackingDataset(
            metadata=metadata,
            records=[
                Frame(
                    frame_id=1,
                    timestamp=0.1,
                    ball_owning_team=None,
                    ball_state=None,
                    period=periods[0],
                    players_coordinates={},
                    ball_coordinates=Point(x=100, y=-50),
                ),
                Frame(
                    frame_id=2,
                    timestamp=0.2,
                    ball_owning_team=None,
                    ball_state=None,
                    period=periods[0],
                    players_coordinates={
                        Player(
                            team=home_team, player_id="home_1", jersey_no=1
                        ): Point(x=15, y=35)
                    },
                    ball_coordinates=Point(x=0, y=50),
                ),
            ],
        )
        return tracking_data

    def test_transform(self):
        tracking_data = self._get_tracking_dataset()

        # orientation change AND dimension scale
        transformed_dataset = transform(
            tracking_data,
            to_orientation="AWAY_TEAM",
            to_pitch_dimensions=[[0, 1], [0, 1]],
        )

        assert transformed_dataset.frames[0].ball_coordinates == Point(
            x=0, y=1
        )
        assert transformed_dataset.frames[1].ball_coordinates == Point(
            x=1, y=0
        )

    def test_transform_to_coordinate_system(self):

        base_dir = os.path.dirname(__file__)

        serializer = TRACABSerializer()

        with open(f"{base_dir}/files/tracab_meta.xml", "rb") as metadata, open(
            f"{base_dir}/files/tracab_raw.dat", "rb"
        ) as raw_data:

            dataset = serializer.deserialize(
                inputs={"metadata": metadata, "raw_data": raw_data},
                options={
                    "only_alive": False,
                    "coordinate_system": Provider.TRACAB,
                },
            )

        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            "19"
        )
        assert dataset.records[0].players_coordinates[player_home_19] == Point(
            x=-1234.0, y=-294.0
        )

        transformed_dataset = transform(
            dataset,
            to_coordinate_system=Provider.METRICA,
        )

        assert transformed_dataset.records[0].players_coordinates[
            player_home_19
        ] == Point(x=0.3766, y=0.5489999999999999)

    def test_to_pandas(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = to_pandas(tracking_data)

        expected_data_frame = DataFrame.from_dict(
            {
                "period_id": {0: 1, 1: 1},
                "timestamp": {0: 0.1, 1: 0.2},
                "ball_state": {0: None, 1: None},
                "ball_owning_team_id": {0: None, 1: None},
                "ball_x": {0: 100, 1: 0},
                "ball_y": {0: -50, 1: 50},
                "home_1_x": {0: None, 1: 15.0},
                "home_1_y": {0: None, 1: 35.0},
            }
        )
        assert_frame_equal(data_frame, expected_data_frame, check_like=True)

    def test_to_pandas_generic_events(self):
        base_dir = os.path.dirname(__file__)

        serializer = OptaSerializer()

        with open(f"{base_dir}/files/opta_f24.xml", "rb") as f24_data, open(
            f"{base_dir}/files/opta_f7.xml", "rb"
        ) as f7_data:
            dataset = serializer.deserialize(
                inputs={"f24_data": f24_data, "f7_data": f7_data}
            )

        dataframe = to_pandas(dataset)
        dataframe = dataframe[dataframe.event_type == "BALL_OUT"]
        assert dataframe.shape[0] == 2

    def test_to_pandas_additional_columns(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = to_pandas(
            tracking_data,
            additional_columns={
                "match": "test",
                "bonus_column": lambda frame: frame.frame_id + 10,
            },
        )

        expected_data_frame = DataFrame.from_dict(
            {
                "period_id": [1, 1],
                "timestamp": [0.1, 0.2],
                "ball_state": [None, None],
                "ball_owning_team_id": [None, None],
                "ball_x": [100, 0],
                "ball_y": [-50, 50],
                "match": ["test", "test"],
                "bonus_column": [11, 12],
                "home_1_x": [None, 15],
                "home_1_y": [None, 35],
            }
        )

        assert_frame_equal(data_frame, expected_data_frame, check_like=True)
