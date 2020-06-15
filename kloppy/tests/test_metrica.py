import os

from kloppy import (
    MetricaTrackingSerializer,
)  # NOT YET: , MetricaEventSerializer
from kloppy.domain import Period, AttackingDirection, Orientation, Point


class TestMetricaTracking:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = MetricaTrackingSerializer()

        with open(
            f"{base_dir}/files/metrica_home.csv", "rb"
        ) as raw_data_home, open(
            f"{base_dir}/files/metrica_away.csv", "rb"
        ) as raw_data_away:
            dataset = serializer.deserialize(
                inputs={
                    "raw_data_home": raw_data_home,
                    "raw_data_away": raw_data_away,
                }
            )

        assert len(dataset.records) == 6
        assert len(dataset.periods) == 2
        assert dataset.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.periods[0] == Period(
            id=1,
            start_timestamp=0.04,
            end_timestamp=0.12,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.periods[1] == Period(
            id=2,
            start_timestamp=5800.16,
            end_timestamp=5800.24,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        # make sure data is loaded correctly (including flip y-axis)
        assert dataset.records[0].home_team_player_positions["11"] == Point(
            x=0.00082, y=1 - 0.48238
        )
        assert dataset.records[0].away_team_player_positions["25"] == Point(
            x=0.90509, y=1 - 0.47462
        )
        assert dataset.records[0].ball_position == Point(
            x=0.45472, y=1 - 0.38709
        )

        # make sure player data is only in the frame when the player is at the pitch
        assert "14" not in dataset.records[0].home_team_player_positions
        assert "14" in dataset.records[3].home_team_player_positions


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
