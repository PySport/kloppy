from io import BytesIO

from kloppy import TRACABSerializer
from kloppy.domain import Period, AttackingDirection, Orientation, Point, BallState, Team


class TestTracabTracking:
    def test_correct_deserialization(self):
        meta_data = BytesIO(b"""
        <TracabMetaData sVersion="1.0">
            <match 
                iId="1337" 
                dtDate="2020-01-02 03:04:05" 
                iFrameRateFps="25" 
                fPitchXSizeMeters="100.00" 
                fPitchYSizeMeters="60.00" 
                fTrackingAreaXSizeMeters="105.00" 
                fTrackingAreaYSizeMeters="70.00">
                <period iId="1" iStartFrame="100" iEndFrame="102"/>
                <period iId="2" iStartFrame="200" iEndFrame="202"/>
                <period iId="3" iStartFrame="0" iEndFrame="0"/>
                <period iId="4" iStartFrame="0" iEndFrame="0"/>
            </match>
        </TracabMetaData>
        """)

        raw_data = BytesIO(b"""
        100:0,1,19,8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Alive;:
        101:0,1,19,8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,A,Alive;:
        102:0,1,19,8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Dead;:

        200:0,1,1337,-8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Alive;:
        201:0,1,1337,-8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Alive;:
        202:0,1,1337,-8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Alive;:
        203:0,1,1337,-8889,-666,0.55;1,2,19,-1234,-294,0.07;:-27,25,0,27.00,H,Alive;:
        """)
        serializer = TRACABSerializer()

        data_set = serializer.deserialize(
            inputs={
                'meta_data': meta_data,
                'raw_data': raw_data
            },
            options={
                "only_alive": False
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
