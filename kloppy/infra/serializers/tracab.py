from typing import Tuple, List, Dict

from lxml import objectify

from ...domain.models import (
    DataSet,
    AttackingDirection,
    Frame,
    Point,
    BallOwningTeam,
    BallState,
    Period,
    Orientation,
    PitchDimensions,
    Dimension)
from ..utils import Readable, performance_logging
from . import TrackingDataSerializer


def avg(items: List[float]) -> float:
    return sum(items) / len(items)


def attacking_direction_from_frame(frame: Frame) -> AttackingDirection:
    """ This method should only be called for the first frame of a """
    avg_x_home = avg([player.x for player in frame.home_team_player_positions.values()])
    avg_x_away = avg([player.x for player in frame.away_team_player_positions.values()])

    if avg_x_home < avg_x_away:
        return AttackingDirection.HOME_AWAY
    else:
        return AttackingDirection.AWAY_HOME


class TRACABSerializer(TrackingDataSerializer):
    @classmethod
    def _frame_from_line(cls, period, line):
        line = str(line)
        frame_id, players, ball = line.strip().split(":")[:3]

        home_team_player_positions = {}
        away_team_player_positions = {}

        for player in players.split(";")[:-1]:
            team_id, target_id, jersey_no, x, y, speed = player.split(",")
            team_id = int(team_id)

            if team_id == 1:
                home_team_player_positions[jersey_no] = Point(float(x), float(y))
            elif team_id == 0:
                away_team_player_positions[jersey_no] = Point(float(x), float(y))

        ball_x, ball_y, ball_z, ball_speed, ball_owning_team, ball_state = ball.rstrip(";").split(",")[:6]

        return Frame(
            frame_id=int(frame_id),
            ball_position=Point(float(ball_x), float(ball_y)),
            ball_state=BallState.from_string(ball_state),
            ball_owning_team=BallOwningTeam.from_string(ball_owning_team),
            home_team_player_positions=home_team_player_positions,
            away_team_player_positions=away_team_player_positions,
            period=period
        )

    def deserialize(self, data: Readable, metadata, options: Dict = None) -> DataSet:
        if not options:
            options = {}

        sample_rate = float(options.get('sample_rate', 1.0))
        only_alive = bool(options.get('only_alive', True))

        with performance_logging("Loading metadata"):
            match = objectify.fromstring(metadata.read()).match
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
                            start_frame_id=start_frame_id,
                            end_frame_id=end_frame_id
                        )
                    )

        original_orientation = None
        with performance_logging("Loading data"):
            def _iter():
                n = 0
                sample = 1. / sample_rate

                for line in data.readlines():
                    line = line.strip().decode("ascii")

                    frame_id = int(line[:10].split(":", 1)[0])
                    if only_alive and not line.endswith("Alive;:"):
                        continue

                    for period in periods:
                        if period.contains(frame_id):
                            if n % sample == 0:
                                yield period, line
                            n += 1

            frames = []
            for period, line in _iter():
                if not original_orientation:
                    # determine orientation of entire dataset
                    frame = self._frame_from_line(
                        period,
                        line
                    )

                    attacking_direction = attacking_direction_from_frame(frame)
                    original_orientation = (
                        Orientation.FIXED_HOME_AWAY
                        if attacking_direction == AttackingDirection.HOME_AWAY else
                        Orientation.FIXED_AWAY_HOME
                    )

                frame = self._frame_from_line(
                    period,
                    line
                )

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(frame)
                    )

                frames.append(frame)

        return DataSet(
            frame_rate=frame_rate,
            orientation=original_orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(-1 * pitch_size_width / 2, pitch_size_width / 2),
                y_dim=Dimension(-1 * pitch_size_height / 2, pitch_size_height / 2),
                x_per_meter=100,
                y_per_meter=100
            ),
            periods=periods,
            frames=frames
        )

    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError

