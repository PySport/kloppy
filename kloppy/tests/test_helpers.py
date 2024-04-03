import os
import sys
from pathlib import Path

import pytest

from kloppy.config import config_context
from pandas import DataFrame
from pandas.testing import assert_frame_equal


from kloppy.domain import (
    Period,
    DatasetFlag,
    Point,
    AttackingDirection,
    TrackingDataset,
    NormalizedPitchDimensions,
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
from kloppy.io import open_as_file


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
            ),
            Period(
                id=2,
                start_timestamp=15.0,
                end_timestamp=25.0,
            ),
        ]
        metadata = Metadata(
            flags=(DatasetFlag.BALL_OWNING_TEAM),
            pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(0, 100),
                y_dim=Dimension(-50, 50),
                pitch_length=105,
                pitch_width=68,
            ),
            orientation=Orientation.HOME_AWAY,
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
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    players_data={},
                    other_data=None,
                    ball_coordinates=Point3D(x=100, y=-50, z=0),
                ),
                Frame(
                    frame_id=2,
                    timestamp=0.2,
                    ball_owning_team=teams[1],
                    ball_state=None,
                    period=periods[1],
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
            to_orientation="AWAY_HOME",
            to_pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(min=0, max=1),
                y_dim=Dimension(min=0, max=1),
                pitch_length=105,
                pitch_width=68,
            ),
        )

        assert transformed_dataset.frames[0].ball_coordinates == Point3D(
            x=0, y=1, z=0
        )
        assert transformed_dataset.frames[1].ball_coordinates == Point3D(
            x=1, y=0, z=1
        )
        assert (
            transformed_dataset.metadata.orientation == Orientation.AWAY_HOME
        )
        assert transformed_dataset.metadata.coordinate_system is None
        assert (
            transformed_dataset.metadata.pitch_dimensions
            == NormalizedPitchDimensions(
                x_dim=Dimension(min=0, max=1),
                y_dim=Dimension(min=0, max=1),
                pitch_length=105,
                pitch_width=68,
            )
        )

    def test_transform_to_pitch_dimensions(self):
        tracking_data = self._get_tracking_dataset()

        transformed_dataset = tracking_data.transform(
            to_pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(min=0, max=1),
                y_dim=Dimension(min=0, max=1),
                pitch_length=105,
                pitch_width=68,
            ),
        )

        assert transformed_dataset.frames[0].ball_coordinates == Point3D(
            x=1, y=0, z=0
        )
        assert transformed_dataset.frames[1].ball_coordinates == Point3D(
            x=0, y=1, z=1
        )
        assert (
            transformed_dataset.metadata.pitch_dimensions
            == NormalizedPitchDimensions(
                x_dim=Dimension(min=0, max=1),
                y_dim=Dimension(min=0, max=1),
                pitch_length=105,
                pitch_width=68,
            )
        )

    def test_transform_to_orientation(self):
        to_pitch_dimensions = NormalizedPitchDimensions(
            x_dim=Dimension(min=0, max=1),
            y_dim=Dimension(min=0, max=1),
            pitch_length=105,
            pitch_width=68,
        )
        # Create a dataset with the KLOPPY pitch dimensions
        # and HOME_AWAY orientation
        original = self._get_tracking_dataset().transform(
            to_pitch_dimensions=to_pitch_dimensions,
        )
        assert original.metadata.orientation == Orientation.HOME_AWAY
        assert original.frames[0].ball_coordinates == Point3D(x=1, y=0, z=0)
        assert original.frames[1].ball_coordinates == Point3D(x=0, y=1, z=1)
        # the frames should have the correct attacking direction
        assert original.frames[0].attacking_direction == AttackingDirection.LTR
        assert original.frames[1].attacking_direction == AttackingDirection.RTL

        # Transform to AWAY_HOME orientation
        transform1 = original.transform(
            to_orientation=Orientation.AWAY_HOME,
            to_pitch_dimensions=to_pitch_dimensions,
        )
        assert transform1.metadata.orientation == Orientation.AWAY_HOME
        # all coordinates should be flipped
        assert transform1.frames[0].ball_coordinates == Point3D(x=0, y=1, z=0)
        assert transform1.frames[1].ball_coordinates == Point3D(x=1, y=0, z=1)
        # the frames should have the correct attacking direction
        assert (
            transform1.frames[0].attacking_direction == AttackingDirection.RTL
        )
        assert (
            transform1.frames[1].attacking_direction == AttackingDirection.LTR
        )

        # Transform to STATIC_AWAY_HOME orientation
        transform2 = transform1.transform(
            to_orientation=Orientation.STATIC_AWAY_HOME,
            to_pitch_dimensions=to_pitch_dimensions,
        )
        assert transform2.metadata.orientation == Orientation.STATIC_AWAY_HOME
        # all coordintes in the second half should be flipped
        assert transform2.frames[0].ball_coordinates == Point3D(x=0, y=1, z=0)
        assert transform2.frames[1].ball_coordinates == Point3D(x=0, y=1, z=1)
        # the frames should have the correct attacking direction
        for frame in transform2.frames:
            assert frame.attacking_direction == AttackingDirection.RTL

        # Transform to BALL_OWNING_TEAM orientation
        transform3 = transform2.transform(
            to_orientation=Orientation.BALL_OWNING_TEAM,
            to_pitch_dimensions=to_pitch_dimensions,
        )
        assert transform3.metadata.orientation == Orientation.BALL_OWNING_TEAM
        # the coordinates of frame 1 should be flipped
        assert transform3.frames[0].ball_coordinates == Point3D(x=1, y=0, z=0)
        assert transform3.frames[1].ball_coordinates == Point3D(x=0, y=1, z=1)
        # the frames should have the correct attacking direction
        assert (
            transform3.frames[0].attacking_direction == AttackingDirection.LTR
        )
        assert (
            transform3.frames[1].attacking_direction == AttackingDirection.RTL
        )

        # Transform to ACTION_EXECUTING_TEAM orientation
        # this should be identical to BALL_OWNING_TEAM for tracking data
        transform4 = transform3.transform(
            to_orientation=Orientation.ACTION_EXECUTING_TEAM,
            to_pitch_dimensions=to_pitch_dimensions,
        )
        assert (
            transform4.metadata.orientation
            == Orientation.ACTION_EXECUTING_TEAM
        )
        assert transform4.frames[1].ball_coordinates == Point3D(x=0, y=1, z=1)
        for frame_t3, frame_t4 in zip(transform3.frames, transform4.frames):
            assert frame_t3.ball_coordinates == frame_t4.ball_coordinates
            assert frame_t3.attacking_direction == frame_t4.attacking_direction

        # Transform back to the original HOME_AWAY orientation
        transform5 = transform4.transform(
            to_orientation=Orientation.HOME_AWAY,
            to_pitch_dimensions=to_pitch_dimensions,
        )
        # we should be back at the original
        for frame1, frame2 in zip(original.frames, transform5.frames):
            assert frame1.ball_coordinates == frame2.ball_coordinates
            assert frame1.attacking_direction == frame2.attacking_direction

    def test_transform_to_coordinate_system(self, base_dir):
        dataset = tracab.load(
            meta_data=base_dir / "files/tracab_meta.xml",
            raw_data=base_dir / "files/tracab_raw.dat",
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
            pitch_length=dataset.metadata.coordinate_system.pitch_length,
            pitch_width=dataset.metadata.coordinate_system.pitch_width,
        )

        assert transformed_dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=0.37660000000000005, y=0.5489999999999999)
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

    def test_transform_event_data(self, base_dir):
        """Make sure event data that's in ACTION_EXECUTING orientation is
        transformed correctly"""
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
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
            to_orientation="static_home_away"
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

    def test_transform_event_data_freeze_frame(self, base_dir):
        """Make sure the freeze frame within event data is transformed too"""
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )

        _, away_team = dataset.metadata.teams

        shot_event = dataset.get_event_by_id(
            "65f16e50-7c5d-4293-b2fc-d20887a772f9"
        )
        transformed_dataset = dataset.transform(
            to_orientation="static_away_home"
        )
        shot_event_transformed = transformed_dataset.get_event_by_id(
            shot_event.event_id
        )

        player = away_team.get_player_by_id(6612)
        coordinates = shot_event.freeze_frame.players_coordinates[player]
        coordinates_transformed = (
            shot_event_transformed.freeze_frame.players_coordinates[player]
        )

        assert coordinates.x == 1 - coordinates_transformed.x
        assert coordinates.y == 1 - coordinates_transformed.y

    def test_to_pandas(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = tracking_data.to_pandas()

        expected_data_frame = DataFrame.from_dict(
            {
                "frame_id": {0: 1, 1: 2},
                "period_id": {0: 1, 1: 2},
                "timestamp": {0: 0.1, 1: 0.2},
                "ball_state": {0: None, 1: None},
                "ball_owning_team_id": {0: "home", 1: "away"},
                "ball_x": {0: 100, 1: 0},
                "ball_y": {0: -50, 1: 50},
                "ball_z": {0: 0, 1: 1},
                "ball_speed": {0: None, 1: None},
                "home_1_x": {0: None, 1: 15.0},
                "home_1_y": {0: None, 1: 35.0},
                "home_1_d": {0: None, 1: 0.03},
                "home_1_s": {0: None, 1: 10.5},
                "home_1_extra_data": {0: None, 1: 1},
                "extra_data": {0: None, 1: 1},
            }
        )
        assert_frame_equal(data_frame, expected_data_frame, check_like=True)

    def test_to_pandas_generic_events(self, base_dir):
        dataset = opta.load(
            f7_data=base_dir / "files/opta_f7.xml",
            f24_data=base_dir / "files/opta_f24.xml",
        )

        dataframe = dataset.to_pandas()
        dataframe = dataframe[dataframe.event_type == "BALL_OUT"]
        assert dataframe.shape[0] == 2

    def test_to_pandas_incomplete_pass(self, base_dir):
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )
        df = dataset.to_pandas()
        incomplete_passes = df[
            (df.event_type == "PASS") & (df.result == "INCOMPLETE")
        ].reset_index()
        assert incomplete_passes.loc[0, "end_coordinates_y"] == pytest.approx(
            0.91519, 1e-4
        )
        assert incomplete_passes.loc[0, "end_coordinates_x"] == pytest.approx(
            0.70945, 1e-4
        )

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
                "frame_id": [1, 2],
                "period_id": [1, 2],
                "timestamp": [0.1, 0.2],
                "ball_state": [None, None],
                "ball_owning_team_id": ["home", "away"],
                "ball_x": [100, 0],
                "ball_y": [-50, 50],
                "ball_z": [0, 1],
                "ball_speed": [None, None],
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

    def test_event_dataset_to_polars(self, base_dir):
        """
        Make sure an event dataset can be exported as a Polars DataFrame
        """
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )
        df = dataset.to_df(engine="polars")

        import polars as pl

        c = df.select(pl.col("event_id").count())[0, 0]
        assert c == 4061

    def test_tracking_dataset_to_polars(self):
        """
        Make sure a tracking dataset can be exported as a Polars DataFrame
        """
        dataset = self._get_tracking_dataset()

        df = dataset.to_df(engine="polars")

        import polars as pl

        c = df.select(pl.col("frame_id").count())[0, 0]
        assert c == 2

    def test_to_df_config(self):
        """
        Make sure to_df get engine from config. By default, pandas, otherwise polars
        """

        import pandas as pd
        import polars as pl

        dataset = self._get_tracking_dataset()
        df = dataset.to_df()
        assert isinstance(df, pd.DataFrame)

        with config_context("dataframe.engine", "polars"):
            df = dataset.to_df()
            assert isinstance(df, pl.DataFrame)

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8")
    def test_to_df_pyarrow(self):
        """
        Make sure we can export to pandas[pyarrow]. Only works for Python > 3.7.

        The pyarrow engine is part of pandas >=1.5. Pandas 1.3 was the last
        version that supports python 3.7, and does not support pyarrow.
        """
        import pandas as pd

        dataset = self._get_tracking_dataset()
        df = dataset.to_df(engine="pandas[pyarrow]")
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.dtypes["ball_x"], pd.ArrowDtype)


class TestOpenAsFile:
    def test_path(self):
        path = Path(__file__).parent / "files/tracab_meta.xml"
        with open_as_file(path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(path)
