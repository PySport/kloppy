from io import BytesIO

from kloppy import MetricaTrackingSerializer
from kloppy.domain import Period, AttackingDirection, Orientation, Point


class TestMetricaTracking:
    def test_correct_deserialization(self):
        raw_data_home = BytesIO(b""",,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,Home,,,
,,,11,,1,,2,,3,,4,,5,,6,,7,,8,,9,,10,,12,,13,,14,,,
Period,Frame,Time [s],Player11,,Player1,,Player2,,Player3,,Player4,,Player5,,Player6,,Player7,,Player8,,Player9,,Player10,,Player12,,Player13,,Player14,,Ball,
1,1,0.04,0.00082,0.48238,0.32648,0.65322,0.33701,0.48863,0.30927,0.35529,0.32137,0.21262,0.41094,0.72589,0.41698,0.47843,0.39125,0.3255,0.45388,0.21174,0.52697,0.3798,0.55243,0.43269,NaN,NaN,NaN,NaN,NaN,NaN,0.45472,0.38709
1,2,0.08,0.00096,0.48238,0.32648,0.65322,0.33701,0.48863,0.30927,0.35529,0.32137,0.21262,0.41094,0.72589,0.41698,0.47843,0.39125,0.3255,0.45388,0.21174,0.52697,0.3798,0.55243,0.43269,NaN,NaN,NaN,NaN,NaN,NaN,0.49645,0.40656
1,3,0.12,0.00114,0.48238,0.32648,0.65322,0.33701,0.48863,0.30927,0.35529,0.32137,0.21262,0.41094,0.72589,0.41698,0.47843,0.39125,0.3255,0.45388,0.21174,0.52697,0.3798,0.55243,0.43269,NaN,NaN,NaN,NaN,NaN,NaN,0.53716,0.42556
2,145004,5800.16,0.90492,0.45355,NaN,NaN,0.34089,0.64569,0.31214,0.67501,0.11428,0.92765,0.25757,0.60019,NaN,NaN,0.37398,0.62446,0.17401,0.83396,0.1667,0.76677,NaN,NaN,0.30044,0.68311,0.33637,0.65366,0.34089,0.64569,NaN,NaN
2,145005,5800.2,0.90456,0.45356,NaN,NaN,0.34056,0.64552,0.31171,0.67468,0.11428,0.92765,0.25721,0.60089,NaN,NaN,0.37398,0.62446,0.17358,0.8343,0.16638,0.76665,NaN,NaN,0.30044,0.68311,0.33615,0.65317,0.34056,0.64552,NaN,NaN
2,145006,5800.24,0.90456,0.45356,NaN,NaN,0.33996,0.64544,0.31122,0.67532,0.11428,0.92765,0.25659,0.60072,NaN,NaN,0.37398,0.62446,0.17327,0.8346,0.1659,0.76555,NaN,NaN,0.30044,0.68311,0.33563,0.65166,0.33996,0.64544,NaN,NaN""")

        raw_data_away = BytesIO(b""",,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,
,,,25,,15,,16,,17,,18,,19,,20,,21,,22,,23,,24,,26,,27,,28,,,
Period,Frame,Time [s],Player25,,Player15,,Player16,,Player17,,Player18,,Player19,,Player20,,Player21,,Player22,,Player23,,Player24,,Player26,,Player27,,Player28,,Ball,
1,1,0.04,0.90509,0.47462,0.58393,0.20794,0.67658,0.4671,0.6731,0.76476,0.40783,0.61525,0.45472,0.38709,0.5596,0.67775,0.55243,0.43269,0.50067,0.94322,0.43693,0.05002,0.37833,0.27383,NaN,NaN,NaN,NaN,NaN,NaN,0.45472,0.38709
1,2,0.08,0.90494,0.47462,0.58393,0.20794,0.67658,0.4671,0.6731,0.76476,0.40783,0.61525,0.45472,0.38709,0.5596,0.67775,0.55243,0.43269,0.50067,0.94322,0.43693,0.05002,0.37833,0.27383,NaN,NaN,NaN,NaN,NaN,NaN,0.49645,0.40656
1,3,0.12,0.90434,0.47463,0.58393,0.20794,0.67658,0.4671,0.6731,0.76476,0.40783,0.61525,0.45472,0.38709,0.5596,0.67775,0.55243,0.43269,0.50067,0.94322,0.43693,0.05002,0.37833,0.27383,NaN,NaN,NaN,NaN,NaN,NaN,0.53716,0.42556
2,145004,5800.16,0.12564,0.55386,0.17792,0.56682,0.25757,0.60019,0.0988,0.92391,0.21235,0.77391,NaN,NaN,0.14926,0.56204,0.10285,0.81944,NaN,NaN,0.29331,0.488,NaN,NaN,0.35561,0.55254,0.19805,0.452,0.21798,0.81079,NaN,NaN
2,145005,5800.2,0.12564,0.55386,0.1773,0.56621,0.25721,0.60089,0.0988,0.92391,0.21235,0.77391,NaN,NaN,0.14857,0.56068,0.10231,0.81944,NaN,NaN,0.29272,0.48789,NaN,NaN,0.35532,0.55243,0.19766,0.45237,0.21798,0.81079,NaN,NaN
2,145006,5800.24,0.12564,0.55386,0.17693,0.56675,0.25659,0.60072,0.0988,0.92391,0.21235,0.77391,NaN,NaN,0.14846,0.56017,0.10187,0.8198,NaN,NaN,0.29267,0.48903,NaN,NaN,0.35495,0.55364,0.19754,0.45364,0.21798,0.81079,NaN,NaN""")

        serializer = MetricaTrackingSerializer()

        data_set = serializer.deserialize(
            inputs={
                'raw_data_home': raw_data_home,
                'raw_data_away': raw_data_away
            }
        )

        assert len(data_set.records) == 6
        assert len(data_set.periods) == 2
        assert data_set.orientation == Orientation.FIXED_HOME_AWAY
        assert data_set.periods[0] == Period(id=1, start_timestamp=0.04, end_timestamp=0.12,
                                             attacking_direction=AttackingDirection.HOME_AWAY)
        assert data_set.periods[1] == Period(id=2, start_timestamp=5800.16, end_timestamp=5800.24,
                                             attacking_direction=AttackingDirection.AWAY_HOME)

        # make sure data is loaded correctly (including flip y-axis)
        assert data_set.records[0].home_team_player_positions['11'] == Point(x=0.00082, y=1 - 0.48238)
        assert data_set.records[0].away_team_player_positions['25'] == Point(x=0.90509, y=1 - 0.47462)
        assert data_set.records[0].ball_position == Point(x=0.45472, y=1 - 0.38709)

        # make sure player data is only in the frame when the player is at the pitch
        assert '14' not in data_set.records[0].home_team_player_positions
        assert '14' in data_set.records[3].home_team_player_positions
