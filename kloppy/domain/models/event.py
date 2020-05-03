# Metrica Documentation https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from csv import reader
from typing import List, Union

from .pitch import Point
from .common import DataRecord, DataSet, Team


class SubType(Enum):
    pass


class ChallengeType(SubType):
    Ground = "GROUND"


class ChallengeResult(SubType):
    Won = "Won"
    Lost = "LOST"


class Fault(SubType):
    Fault = "FAULT"
    Advantage = "ADVANTAGE"


class Interference1(SubType):
    Interception = "INTERCEPTION"
    Theft = "THEFT"


class Interference2(SubType):
    Blocked = "BLOCKED"
    Saved = "SAVED"


class Intervention(SubType):
    Voluntary = "VOLUNTARY"
    Forced = "FORCED"
    End_Half = "END HALF"


class Attempt(SubType):
    Clearance = "CLEARANCE"
    Cross = "CROSS"
    Through_Ball = "THROUGH BALL"
    Deep_Ball = "DEEP BALL"
    Goal_Kick = "GOAL KICK"


class Offside(SubType):
    Offside = "OFFSIDE"


class BodyPart(SubType):
    Head = "HEAD"
    Foot = "FOOT"


class Deflection(SubType):
    Woodwork = "WOODWORK"
    Referee_hit = "REFEREE HIT"
    Handball = "HANDBALL"


class ShotDirection(SubType):
    On_Target = "ON TARGET"
    Off_Target = "OFF TARGET"


class ShotResult(SubType):
    Goal = "GOAL"
    Out = "OUT"
    Blocked = "BLOCKED"
    Saved = "SAVED"


class Challenge(SubType):
    Tackle = "TACKLE"
    Dribble = "DRIBBLE"
    Ground = "GROUND"
    Aerial = "AERIAL"


class Card(SubType):
    Yellow = "YELLOW"
    Red = "RED"
    Dismissal = "DISMISSAL"


class SetPiece(SubType):
    Kick_off = "KICK OFF"
    Throw_In = "THROW IN"
    Corner_Kick = "CORNER KICK"
    Goal_Kick = "GOAL KICK"
    Free_Kick = "FREE KICK"


class FKAttempt(SubType):
    Direct = "DIRECT"
    Indirect = "INDIRECT"


class Retaken(SubType):
    Retaken = "RETAKEN"


class OwnGoal(SubType):
    OwnGoal = "OWN GOAL"



"""
@dataclass
class Frame:
    frame_id: int
    timestamp: float
    ball_owning_team: Team
    ball_state: BallState

    period: Period

    home_team_player_positions: Dict[str, Point]
    away_team_player_positions: Dict[str, Point]
    ball_position: Point
    
"""


class EventType(Enum):
    SET_PIECE = "SET PIECE"
    RECOVERY = "RECOVERY"
    PASS = "PASS"
    BALL_LOST = "BALL LOST"
    BALL_OUT = "BALL OUT"
    SHOT = "SHOT"
    FAULT_RECEIVED = "FAULT RECEIVED"
    CHALLENGE = "CHALLENGE"
    CARD = "CARD"


@dataclass
class Event(DataRecord, ABC):
    event_id: int
    team: Team
    end_timestamp: float  # allowed to be same as timestamp

    player_jersey_no: str
    position: Point

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        raise NotImplementedError


@dataclass
class SetPieceEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.SET_PIECE


@dataclass
class ShotEvent(Event):
    shot_result: ShotResult

    @property
    def event_type(self) -> EventType:
        return EventType.PASS


@dataclass
class FaultReceivedEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.FAULT_RECEIVED


@dataclass
class ChallengeEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.CHALLENGE


@dataclass
class CardEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.CARD


@dataclass
class RecoveryEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.RECOVERY


@dataclass
class BallLossEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.BALL_LOST


@dataclass
class BallOutEvent(Event):
    @property
    def event_type(self) -> EventType:
        return EventType.BALL_OUT


@dataclass
class PassEvent(Event):
    receiver_player_jersey_no: str
    receiver_position: Point

    @property
    def event_type(self) -> EventType:
        return EventType.PASS


@dataclass
class EventDataSet(DataSet):
    records: List[Union[
        SetPieceEvent, ShotEvent
    ]]

    @property
    def events(self):
        return self.records


if __name__ == '__main__':


    data_file = "Sample_Game_1_RawEventsData.csv"

    with open(data_file, 'r') as read_obj:
        csv_reader = reader(read_obj)
        next(csv_reader) # skip the header

        for team_, Type, subtype, period, start_f, start_t, end_f, end_t, From, to, start_x, start_y, end_x, end_y in csv_reader:

            ## iron out any formatting issues
            Type = Type.upper()
            subtype = subtype.upper()
            period = int(period)
            team_ = team_.title()
            From = From.title()
            to = to.title()


            team = Team.HOME if team_ == "Home" else Team.AWAY

            eventtype = EventType_map[Type]

            periodid = PeriodEvent(period)

            player = Player(From)
            next_player = Player(to)

            start_frame = frame_id(start_f)
            end_frame = frame_id(end_t)

            start_time = time_id(start_t)
            end_time = time_id(end_f)

            start_location = Point(start_x, start_y)
            end_location = Point(end_x, end_y)


            print("-"*50)
            print(team, eventtype, periodid, player, next_player, start_frame, end_frame, start_time, end_time, start_location, end_location)

            subtypes = subtype.split('-')

            if subtype == "":
                pass
            else:
                challenge_type, fault, result, intf1, intf2, intv, atmp, ofsid, bdy, dflc, shtdir, shotres, chall, crd, setp, fk, rtake= build_subtypes(subtypes, [ChallengeType, Fault, ChallengeResult, Interference1, Interference2, Intervention, Attempt, Offside, BodyPart, Deflection, ShotDirection, ShotResult, Challenge, Card, SetPiece, FKAttempt, Retaken])
                print(challenge_type, fault, result, intf1, intf2, intv, atmp, ofsid, bdy, dflc, shtdir, shotres, chall, crd, setp, fk, rtake)