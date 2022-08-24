import os

from pandas import DataFrame
from pandas.testing import assert_frame_equal


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
    Metadata,
    MetricaCoordinateSystem,
    Team,
    Ground,
    Player,
    PlayerData,
    Point3D,
)

from kloppy import opta, tracab, statsbomb


class TestHelpers:
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
                    players_data={},
                    other_data=None,
                    ball_coordinates=Point3D(x=100, y=-50, z=0),
                ),
                Frame(
                    frame_id=2,
                    timestamp=0.2,
                    ball_owning_team=None,
                    ball_state=None,
                    period=periods[0],
                    players_data={
                        Player(
                            team=home_team, player_id="home_1", jersey_no=1
                        ): PlayerData(
                            coordinates=Point(x=15, y=35),
                            distance=0.03,
                            speed=10.5,
                            other_data={"extra_data": 1},
                        )
                    },
                    other_data={"extra_data": 1},
                    ball_coordinates=Point3D(x=0, y=50, z=1),
                ),
            ],
        )
        return tracking_data

    def test_transform(self):
        tracking_data = self._get_tracking_dataset()

        # orientation change AND dimension scale
        transformed_dataset = tracking_data.transform(
            to_orientation="AWAY_TEAM",
            to_pitch_dimensions=[[0, 1], [0, 1]],
        )

        assert transformed_dataset.frames[0].ball_coordinates == Point3D(
            x=0, y=1, z=0
        )
        assert transformed_dataset.frames[1].ball_coordinates == Point3D(
            x=1, y=0, z=1
        )
        assert (
            transformed_dataset.metadata.orientation == Orientation.AWAY_TEAM
        )
        assert transformed_dataset.metadata.coordinate_system is None
        assert (
            transformed_dataset.metadata.pitch_dimensions
            == PitchDimensions(
                x_dim=Dimension(min=0, max=1), y_dim=Dimension(min=0, max=1)
            )
        )

    def test_transform_to_coordinate_system(self):
        base_dir = os.path.dirname(__file__)

        dataset = tracab.load(
            meta_data=f"{base_dir}/files/tracab_meta.xml",
            raw_data=f"{base_dir}/files/tracab_raw.dat",
            only_alive=False,
            coordinates="tracab",
        )

        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            19
        )
        assert dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=-1234.0, y=-294.0)

        transformed_dataset = dataset.transform(
            to_coordinate_system=Provider.METRICA
        )
        transformerd_coordinate_system = MetricaCoordinateSystem(
            normalized=True,
            length=dataset.metadata.coordinate_system.length,
            width=dataset.metadata.coordinate_system.width,
        )

        assert transformed_dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=0.3766, y=0.5489999999999999)
        assert (
            transformed_dataset.metadata.orientation
            == dataset.metadata.orientation
        )
        assert (
            transformed_dataset.metadata.coordinate_system
            == transformerd_coordinate_system
        )
        assert (
            transformed_dataset.metadata.pitch_dimensions
            == transformerd_coordinate_system.pitch_dimensions
        )

    def test_transform_event_data(self):
        """Make sure event data that's in ACTION_EXECUTING orientation is
        transformed correctly"""
        base_dir = os.path.dirname(__file__)

        dataset = statsbomb.load(
            lineup_data=f"{base_dir}/files/statsbomb_lineup.json",
            event_data=f"{base_dir}/files/statsbomb_event.json",
        )

        home_team, away_team = dataset.metadata.teams

        # This is a pressure event by Deportivo while Barcelona is in possession
        pressure_event = dataset.get_event_by_id(
            "6399af5c-74b8-4efe-ae19-85f331d355e8"
        )
        assert pressure_event.team == away_team
        assert pressure_event.ball_owning_team == home_team

        receipt_event = pressure_event.next()
        assert receipt_event.team == home_team
        assert receipt_event.ball_owning_team == home_team

        transformed_dataset = dataset.transform(
            to_orientation="fixed_home_away"
        )
        transformed_pressure_event = transformed_dataset.get_event_by_id(
            pressure_event.event_id
        )
        transformed_receipt_event = transformed_pressure_event.next()

        # The receipt event is executed by the away team and should be changed by the transformation
        assert (
            pressure_event.coordinates.x
            == 1 - transformed_pressure_event.coordinates.x
        )
        assert (
            pressure_event.coordinates.y
            == 1 - transformed_pressure_event.coordinates.y
        )

        # The receipt event is executed by the home team and shouldn't be changed by the transformation
        assert (
            receipt_event.coordinates.x
            == transformed_receipt_event.coordinates.x
        )
        assert (
            receipt_event.coordinates.y
            == transformed_receipt_event.coordinates.y
        )

    def test_to_pandas(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = tracking_data.to_pandas()

        expected_data_frame = DataFrame.from_dict(
            {
                "period_id": {0: 1, 1: 1},
                "timestamp": {0: 0.1, 1: 0.2},
                "ball_state": {0: None, 1: None},
                "ball_owning_team_id": {0: None, 1: None},
                "ball_x": {0: 100, 1: 0},
                "ball_y": {0: -50, 1: 50},
                "ball_z": {0: 0, 1: 1},
                "home_1_x": {0: None, 1: 15.0},
                "home_1_y": {0: None, 1: 35.0},
                "home_1_d": {0: None, 1: 0.03},
                "home_1_s": {0: None, 1: 10.5},
                "home_1_extra_data": {0: None, 1: 1},
                "extra_data": {0: None, 1: 1},
            }
        )
        assert_frame_equal(data_frame, expected_data_frame, check_like=True)

    def test_to_pandas_generic_events(self):
        base_dir = os.path.dirname(__file__)
        dataset = opta.load(
            f7_data=f"{base_dir}/files/opta_f7.xml",
            f24_data=f"{base_dir}/files/opta_f24.xml",
        )

        dataframe = dataset.to_pandas()
        dataframe = dataframe[dataframe.event_type == "BALL_OUT"]
        assert dataframe.shape[0] == 2

    def test_to_pandas_incomplete_pass(self):
        base_dir = os.path.dirname(__file__)

        dataset = statsbomb.load(
            lineup_data=f"{base_dir}/files/statsbomb_lineup.json",
            event_data=f"{base_dir}/files/statsbomb_event.json",
        )
        df = dataset.to_pandas()
        incomplete_passes = df[
            (df.event_type == "PASS") & (df.result == "INCOMPLETE")
        ].reset_index()
        assert incomplete_passes.loc[0, "end_coordinates_y"] == 0.90625
        assert incomplete_passes.loc[0, "end_coordinates_x"] == 0.7125

    def test_to_pandas_additional_columns(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = tracking_data.to_pandas(
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
                "ball_z": [0, 1],
                "match": ["test", "test"],
                "bonus_column": [11, 12],
                "home_1_x": [None, 15],
                "home_1_y": [None, 35],
                "home_1_d": [None, 0.03],
                "home_1_s": [None, 10.5],
                "home_1_extra_data": [None, 1],
                "extra_data": [None, 1],
            }
        )

        assert_frame_equal(data_frame, expected_data_frame, check_like=True)
