from typing import Tuple, Dict

import json

from kloppy.domain import EventDataSet, PassEvent, Team, Period, Point, PassResult
from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.infra.utils import Readable, performance_logging


SB_EVENT_TYPE_DRIBBLE = 14
SB_EVENT_TYPE_SHOT = 16
SB_EVENT_TYPE_PASS = 30
SB_EVENT_TYPE_CARRY = 43

SB_EVENT_TYPE_HALF_START = 18
SB_EVENT_TYPE_HALF_END = 34

SB_PASS_OUTCOME_INCOMPLETE = 9
SB_PASS_OUTCOME_INJURY_CLEARANCE = 74
SB_PASS_OUTCOME_OUT = 75
SB_PASS_OUTCOME_OFFSIDE = 76
SB_PASS_OUTCOME_UNKNOWN = 77


def parse_str_ts(timestamp: str) -> float:
    h, m, s = timestamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _parse_pass(pass_dict: Dict, current_team_map: Dict[int, int]) -> Dict:
    if 'outcome' in pass_dict:
        outcome_id = pass_dict['outcome']['id']
        if outcome_id == SB_PASS_OUTCOME_OUT:
            result = PassResult.OUT
        elif outcome_id == SB_PASS_OUTCOME_INCOMPLETE:
            result = PassResult.INCOMPLETE
        elif outcome_id == SB_PASS_OUTCOME_OFFSIDE:
            result = PassResult.OFFSIDE
        elif outcome_id == SB_PASS_OUTCOME_INJURY_CLEARANCE:
            result = PassResult.OUT
        elif outcome_id == SB_PASS_OUTCOME_UNKNOWN:
            result = None
        else:
            raise Exception(f"Unknown pass outcome: {outcome_id}")

        receiver_player_jersey_no = None
        receiver_position = None
    else:
        result = PassResult.COMPLETE
        receiver_player_jersey_no = current_team_map[
            pass_dict['recipient']['id']
        ]
        receiver_position = Point(
            x=pass_dict['end_location'][0],
            y=pass_dict['end_location'][1]
        )

    return dict(
        result=result,
        receiver_position=receiver_position,
        receiver_player_jersey_no=receiver_player_jersey_no
    )


class StatsbombSerializer(EventDataSerializer):
    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> EventDataSet:
        with performance_logging("load data"):
            raw_events = json.load(inputs['raw_data'])
            home_lineup, away_lineup = json.load(inputs['lineup'])



        with performance_logging("parse data"):
            home_player_map = {
                player['player_id']: player['jersey_number']
                for player in home_lineup['lineup']
            }
            away_player_map = {
                player['player_id']: player['jersey_number']
                for player in away_lineup['lineup']
            }

            periods = []
            period = None
            events = []
            for raw_event in raw_events:
                if raw_event['team']['id'] == home_lineup['team_id']:
                    team = Team.HOME
                    current_team_map = home_player_map
                elif raw_event['team']['id'] == away_lineup['team_id']:
                    team = Team.AWAY
                    current_team_map = away_player_map
                else:
                    raise Exception(f"Unknown team_id {raw_event['team']['id']}")

                timestamp = parse_str_ts(raw_event['timestamp'])
                period_id = int(raw_event['period'])
                if not period or period.id != period_id:
                    period = Period(
                        id=period_id,
                        start_timestamp=timestamp,
                        end_timestamp=timestamp
                    )
                    periods.append(period)
                else:
                    period.end_timestamp = timestamp

                player_jersey_no = None
                if 'player' in raw_event:
                    player_jersey_no = current_team_map[raw_event['player']['id']]

                event_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=timestamp,
                    ball_owning_team=None,
                    ball_state=None,
                    # from Event
                    event_id=raw_event['id'],
                    team=team,
                    player_jersey_no=player_jersey_no,
                    position=(
                        Point(
                            x=raw_event['location'][0],
                            y=raw_event['location'][1]
                        )
                        if 'location' in raw_event
                        else None
                    )
                )

                event_type = raw_event['type']['id']
                if event_type == SB_EVENT_TYPE_PASS:
                    pass_event_kwargs = _parse_pass(raw_event['pass'], current_team_map)

                    event = PassEvent(
                        end_timestamp=timestamp + raw_event['duration'],
                        **pass_event_kwargs,
                        **event_kwargs
                    )
                else:
                    continue

                events.append(event)

    def serialize(self, data_set: EventDataSet) -> Tuple[str, str]:
        raise NotImplementedError
