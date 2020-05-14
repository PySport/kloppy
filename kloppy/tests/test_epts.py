import os
from io import BytesIO

from kloppy import EPTSSerializer
from kloppy.domain import Period, AttackingDirection, Orientation, Point, BallState, Team
from kloppy.infra.serializers.tracking.epts.meta_data import load_meta_data
from kloppy.infra.serializers.tracking.epts.reader import build_regex


class TestEPTSTracking:
    def test_regex(self):
        base_dir = os.path.dirname(__file__)
        with open(f'{base_dir}/files/epts_meta.xml', 'rb') as meta_data_fp:
            meta_data = load_meta_data(meta_data_fp)

        regex = build_regex(
            meta_data.data_format_specifications[0],
            meta_data.player_channels
        )
        assert regex == "(?P<frameCount>):" \
                        "(?P<player_home_22_x>),(?P<player_home_22_y>),(?P<player_home_22_z>)," \
                        "(?P<player_home_22_distance>),(?P<player_home_22_avg_speed>)," \
                        "(?P<player_home_22_max_speed>),(?P<player_home_22_acceleration>)," \
                        "(?P<player_home_22_max_acceleration>),(?P<player_home_22_heartbeat>)," \
                        "(?P<player_home_22_max_heartbeat>);" \
                        "(?P<player_home_10_x>),(?P<player_home_10_y>),(?P<player_home_10_z>)," \
                        "(?P<player_home_10_distance>),(?P<player_home_10_avg_speed>)," \
                        "(?P<player_home_10_max_speed>),(?P<player_home_10_acceleration>)," \
                        "(?P<player_home_10_max_acceleration>),(?P<player_home_10_heartbeat>)," \
                        "(?P<player_home_10_max_heartbeat>);" \
                        "(?P<player_home_7_x>),(?P<player_home_7_y>),(?P<player_home_7_z>)," \
                        "(?P<player_home_7_distance>),(?P<player_home_7_avg_speed>)," \
                        "(?P<player_home_7_max_speed>),(?P<player_home_7_acceleration>)," \
                        "(?P<player_home_7_max_acceleration>),(?P<player_home_7_heartbeat>)," \
                        "(?P<player_home_7_max_heartbeat>):" \
                        "(?P<ball_x>),(?P<ball_y>),(?P<ball_z>)"

    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = EPTSSerializer()

        with open(f'{base_dir}/files/epts_meta.xml', 'rb') as meta_data, \
            open(f'{base_dir}/files/epts_raw.txt', 'rb') as raw_data:

            data_set = serializer.deserialize(
                inputs={
                    'meta_data': meta_data,
                    'raw_data': raw_data
                }
            )

        assert len(data_set.records) == 6
        assert len(data_set.periods) == 2
        assert data_set.orientation == Orientation.FIXED_HOME_AWAY
        assert data_set.periods[0] == Period(id=1, start_timestamp=4.0, end_timestamp=4.08,
                                             attacking_direction=AttackingDirection.HOME_AWAY)

        assert data_set.periods[1] == Period(id=2, start_timestamp=8.0, end_timestamp=8.08,
                                             attacking_direction=AttackingDirection.AWAY_HOME)

        assert data_set.records[0].home_team_player_positions['19'] == Point(x=-1234.0, y=-294.0)
        assert data_set.records[0].away_team_player_positions['19'] == Point(x=8889, y=-666)
        assert data_set.records[0].ball_position == Point(x=-27, y=25)
        assert data_set.records[0].ball_state == BallState.ALIVE
        assert data_set.records[0].ball_owning_team == Team.HOME

        assert data_set.records[1].ball_owning_team == Team.AWAY

        assert data_set.records[2].ball_state == BallState.DEAD

        # make sure player data is only in the frame when the player is at the pitch
        assert '1337' not in data_set.records[0].away_team_player_positions
        assert '1337' in data_set.records[3].away_team_player_positions
