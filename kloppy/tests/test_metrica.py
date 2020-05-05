from io import BytesIO

from kloppy import MetricaTrackingSerializer # NOT YET: , MetricaEventSerializer
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

#
# class TestMetricaEvent:
#     def test_correct_deserialization(self):
#         raw_data = BytesIO(b"""Team,Type,Subtype,Period,Start Frame,Start Time [s],End Frame,End Time [s],From,To,Start X,Start Y,End X,End Y
# Away,SET PIECE,KICK OFF,1,1,0.04,0,0,Player19,,NaN,NaN,NaN,NaN
# Away,PASS,,1,1,0.04,3,0.12,Player19,Player21,0.45,0.39,0.55,0.43
# Away,PASS,,1,3,0.12,17,0.68,Player21,Player15,0.55,0.43,0.58,0.21
# Away,PASS,,1,45,1.8,61,2.44,Player15,Player19,0.55,0.19,0.45,0.31
# Away,PASS,,1,77,3.08,96,3.84,Player19,Player21,0.45,0.32,0.49,0.47
# Away,PASS,,1,191,7.64,217,8.68,Player21,Player22,0.4,0.73,0.32,0.98
# Away,PASS,,1,279,11.16,303,12.12,Player22,Player17,0.39,0.96,0.49,0.98
# Away,BALL LOST,INTERCEPTION,1,346,13.84,380,15.2,Player17,,0.51,0.97,0.27,0.75
# Home,RECOVERY,INTERCEPTION,1,378,15.12,378,15.12,Player2,,0.27,0.78,NaN,NaN
# Home,BALL LOST,INTERCEPTION,1,378,15.12,452,18.08,Player2,,0.27,0.78,0.59,0.64
# Away,RECOVERY,INTERCEPTION,1,453,18.12,453,18.12,Player16,,0.57,0.67,NaN,NaN
# Away,BALL LOST,HEAD-INTERCEPTION,1,453,18.12,497,19.88,Player16,,0.57,0.67,0.33,0.65
# Away,CHALLENGE,AERIAL-LOST,1,497,19.88,497,19.88,Player18,,0.38,0.67,NaN,NaN
# Home,CHALLENGE,AERIAL-WON,1,498,19.92,498,19.92,Player2,,0.36,0.67,NaN,NaN
# Home,RECOVERY,INTERCEPTION,1,498,19.92,498,19.92,Player2,,0.36,0.67,NaN,NaN
# Home,PASS,HEAD,1,498,19.92,536,21.44,Player2,Player9,0.36,0.67,0.53,0.59
# Home,PASS,,1,536,21.44,556,22.24,Player9,Player10,0.53,0.59,0.5,0.65
# Home,BALL LOST,INTERCEPTION,1,572,22.88,616,24.64,Player10,,0.5,0.65,0.67,0.44
# Away,RECOVERY,INTERCEPTION,1,618,24.72,618,24.72,Player16,,0.64,0.46,NaN,NaN
# Away,PASS,,1,763,30.52,784,31.36,Player16,Player19,0.58,0.27,0.51,0.33
# Away,PASS,,1,784,31.36,804,32.16,Player19,Player20,0.51,0.33,0.57,0.47
# Away,PASS,,1,834,33.36,881,35.24,Player20,Player22,0.53,0.53,0.44,0.92
# Away,PASS,,1,976,39.04,1010,40.4,Player22,Player17,0.36,0.96,0.48,0.86
# Away,BALL LOST,INTERCEPTION,1,1110,44.4,1134,45.36,Player17,,0.42,0.79,0.31,0.84
# Home,RECOVERY,INTERCEPTION,1,1134,45.36,1134,45.36,Player5,,0.32,0.89,NaN,NaN
# Home,PASS,HEAD,1,1134,45.36,1154,46.16,Player5,Player6,0.32,0.89,0.31,0.78
# Home,PASS,,1,1154,46.16,1177,47.08,Player6,Player10,0.31,0.78,0.41,0.74
# Home,PASS,,1,1226,49.04,1266,50.64,Player10,Player8,0.46,0.68,0.56,0.34
# Home,BALL LOST,INTERCEPTION,1,1370,54.8,1375,55,Player8,,0.86,0.26,0.88,0.28
# Away,RECOVERY,INTERCEPTION,1,1374,54.96,1374,54.96,Player15,,0.87,0.29,NaN,NaN
# Away,BALL OUT,,1,1374,54.96,1425,57,Player15,,0.87,0.29,1.05,0.17
# Home,SET PIECE,CORNER KICK,1,2143,85.72,2143,85.72,Player6,,NaN,NaN,NaN,NaN
# Home,PASS,,1,2143,85.72,2184,87.36,Player6,Player10,1,0.01,0.9,0.09
# Home,PASS,CROSS,1,2263,90.52,2289,91.56,Player10,Player9,0.89,0.14,0.92,0.47
# Home,SHOT,HEAD-ON TARGET-GOAL,1,2289,91.56,2309,92.36,Player9,,0.92,0.47,1.01,0.55
# Away,SET PIECE,KICK OFF,1,3675,147,3675,147,Player19,,NaN,NaN,NaN,NaN
# Away,PASS,,1,3675,147,3703,148.12,Player19,Player21,0.49,0.5,0.58,0.52""")
#
#         serializer = MetricaEventSerializer()
#         serializer.deserialize(
#             inputs={
#                 'raw_data': raw_data
#             }
#         )