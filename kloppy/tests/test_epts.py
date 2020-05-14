import os
import re
from io import BytesIO

from kloppy import EPTSSerializer
from kloppy.domain import Period, AttackingDirection, Orientation, Point, BallState, Team
from kloppy.infra.serializers.tracking.epts.meta_data import load_meta_data
from kloppy.infra.serializers.tracking.epts.reader import build_regex, _read


class TestEPTSTracking:
    def test_regex(self):
        base_dir = os.path.dirname(__file__)
        with open(f'{base_dir}/files/epts_meta.xml', 'rb') as meta_data_fp:
            meta_data = load_meta_data(meta_data_fp)

        regex_str = build_regex(
            meta_data.data_format_specifications[0],
            meta_data.player_channels,
            meta_data.sensors
        )

        regex = re.compile(regex_str)

        print(regex_str)

        regex_str = "(?P<frameCount>\\-?\\d+?(?:\\.\\d+)?):(?P<player_home_22_x>\-?\d*(?:\.\d+)?),(?P<player_home_22_y>\-?\d+?(?:\.\d+)?)"  #,(?P<player_home_22_z>\-?\d+?(?:\.\d+)?),(?P<player_home_22_distance>\-?\d+?(?:\.\d+)?),(?P<player_home_22_avg_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_22_max_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_22_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_22_max_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_22_heartbeat>\-?\d+?(?:\.\d+)?),(?P<player_home_22_max_heartbeat>\-?\d+?(?:\.\d+)?);(?P<player_home_10_x>\-?\d+?(?:\.\d+)?),(?P<player_home_10_y>\-?\d+?(?:\.\d+)?),(?P<player_home_10_z>\-?\d+?(?:\.\d+)?),(?P<player_home_10_distance>\-?\d+?(?:\.\d+)?),(?P<player_home_10_avg_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_10_max_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_10_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_10_max_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_10_heartbeat>\-?\d+?(?:\.\d+)?),(?P<player_home_10_max_heartbeat>\-?\d+?(?:\.\d+)?);(?P<player_home_7_x>\-?\d+?(?:\.\d+)?),(?P<player_home_7_y>\-?\d+?(?:\.\d+)?),(?P<player_home_7_z>\-?\d+?(?:\.\d+)?),(?P<player_home_7_distance>\-?\d+?(?:\.\d+)?),(?P<player_home_7_avg_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_7_max_speed>\-?\d+?(?:\.\d+)?),(?P<player_home_7_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_7_max_acceleration>\-?\d+?(?:\.\d+)?),(?P<player_home_7_heartbeat>\-?\d+?(?:\.\d+)?),(?P<player_home_7_max_heartbeat>\-?\d+?(?:\.\d+)?):(?P<ball_x>\-?\d+?(?:\.\d+)?),(?P<ball_y>\-?\d+?(?:\.\d+)?),(?P<ball_z>\-?\d+?(?:\.\d+)?)"
        #regex = re.compile(regex_str)

        result = regex.search("1779143:,-2.013,-500,100,9.63,9.80,4,5,177,182;-461,-615,-120,99,900,9.10,4,5,170,179;-2638,3478,120,110,1.15,5.20,3,4,170,175:-2656,367,100:")

        print(result)

        assert result is not None
        #
        # assert regex == "(?P<frameCount>):" \
        #                 "(?P<player_home_22_x>),(?P<player_home_22_y>),(?P<player_home_22_z>)," \
        #                 "(?P<player_home_22_distance>),(?P<player_home_22_avg_speed>)," \
        #                 "(?P<player_home_22_max_speed>),(?P<player_home_22_acceleration>)," \
        #                 "(?P<player_home_22_max_acceleration>),(?P<player_home_22_heartbeat>)," \
        #                 "(?P<player_home_22_max_heartbeat>);" \
        #                 "(?P<player_home_10_x>),(?P<player_home_10_y>),(?P<player_home_10_z>)," \
        #                 "(?P<player_home_10_distance>),(?P<player_home_10_avg_speed>)," \
        #                 "(?P<player_home_10_max_speed>),(?P<player_home_10_acceleration>)," \
        #                 "(?P<player_home_10_max_acceleration>),(?P<player_home_10_heartbeat>)," \
        #                 "(?P<player_home_10_max_heartbeat>);" \
        #                 "(?P<player_home_7_x>),(?P<player_home_7_y>),(?P<player_home_7_z>)," \
        #                 "(?P<player_home_7_distance>),(?P<player_home_7_avg_speed>)," \
        #                 "(?P<player_home_7_max_speed>),(?P<player_home_7_acceleration>)," \
        #                 "(?P<player_home_7_max_acceleration>),(?P<player_home_7_heartbeat>)," \
        #                 "(?P<player_home_7_max_heartbeat>):" \
        #                 "(?P<ball_x>),(?P<ball_y>),(?P<ball_z>)"

    def test_read(self):
        base_dir = os.path.dirname(__file__)
        with open(f'{base_dir}/files/epts_meta.xml', 'rb') as meta_data_fp:
            meta_data = load_meta_data(meta_data_fp)

        with open(f'{base_dir}/files/epts_raw.txt', 'rb') as raw_data:
            iterator = _read(raw_data, meta_data) #, {"position"})

            list(iterator)

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
