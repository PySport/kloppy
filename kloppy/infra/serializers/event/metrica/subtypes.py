from typing import List, Type, Union, Dict, Callable

from kloppy.domain.models.event import (
    Retaken,
    FKAttempt,
    SetPiece,
    Card,
    Challenge,
    ShotResult,
    ShotDirection,
    Deflection,
    BodyPart,
    Offside,
    Attempt,
    Intervention,
    Interference1,
    Interference2,
    ChallengeType,
    ChallengeResult,
    Fault,
    SubType,
    OwnGoal,
)


def build_retaken(string: str) -> Retaken:
    if string == "RETAKEN":
        return Retaken.Retaken
    else:
        raise ValueError(f"Unknown retaken type: {string}")


def build_fkattempt(string: str) -> FKAttempt:
    if string == "DIRECT":
        return FKAttempt.Direct
    elif string == "INDIRECT":
        return FKAttempt.Indirect
    else:
        raise ValueError(f"Unknown fkattempt type: {string}")


def build_setpiece(string: str) -> SetPiece:
    if string == "KICK OFF":
        return SetPiece.Kick_off
    elif string == "THROW IN":
        return SetPiece.Throw_In
    elif string == "CORNER KICK":
        return SetPiece.Corner_Kick
    elif string == "GOAL KICK":
        return SetPiece.Goal_Kick
    elif string == "FREE KICK":
        return SetPiece.Free_Kick
    else:
        raise ValueError(f"Unknown setpiece type: {string}")


def build_card(string: str) -> Card:
    if string == "YELLOW":
        return Card.Yellow
    elif string == "RED":
        return Card.Red
    elif string == "DISMISSAL":
        return Card.Dismissal
    else:
        raise ValueError(f"Unknown card type: {string}")


def build_challenge(string: str) -> Challenge:
    if string == "TACKLE":
        return Challenge.Tackle
    elif string == "DRIBBLE":
        return Challenge.Dribble
    elif string == "GROUND":
        return Challenge.Ground
    elif string == "AERIAL":
        return Challenge.Aerial
    else:
        raise ValueError(f"Unknown challenge type: {string}")


def build_shotresult(string: str) -> ShotResult:
    if string == "GOAL":
        return ShotResult.Goal
    elif string == "OUT":
        return ShotResult.Out
    elif string == "BLOCKED":
        return ShotResult.Blocked
    elif string == "SAVED":
        return ShotResult.Saved
    else:
        raise ValueError(f"Unknown deflection type: {string}")


def build_shotdirection(string: str) -> ShotDirection:
    if string == "ON TARGET":
        return ShotDirection.On_Target
    elif string == "OFF TARGET":
        return ShotDirection.Off_Target
    else:
        raise ValueError(f"Unknown shotdirection type: {string}")


def build_deflection(string: str) -> Deflection:
    if string == "WOODWORK":
        return Deflection.Woodwork
    elif string == "REFEREE HIT":
        return Deflection.Referee_hit
    elif string == "HANDBALL":
        return Deflection.Handball
    else:
        raise ValueError(f"Unknown deflection type: {string}")


def build_bodypart(string: str) -> BodyPart:
    if string == "HEAD":
        return BodyPart.Head
    elif string == "FOOT":
        return BodyPart.Foot
    else:
        raise ValueError(f"Unknown bodypart type: {string}")


def build_offside(string: str) -> Offside:
    if string == "OFFSIDE":
        return Offside.Offside
    else:
        raise ValueError(f"Unknown offside type: {string}")


def build_attempt(string: str) -> Attempt:
    if string == "CLEARANCE":
        return Attempt.Clearance
    elif string == "CROSS":
        return Attempt.Cross
    elif string == "THROUGH BALL":
        return Attempt.Through_Ball
    elif string == "DEEP BALL":
        return Attempt.Deep_Ball
    elif string == "GOAL KICK":
        return Attempt.Goal_Kick
    else:
        raise ValueError(f"Unknown attempt type: {string}")


def build_intervention(string: str) -> Intervention:
    if string == "VOLUNTARY":
        return Intervention.Voluntary
    elif string == "FORCED":
        return Intervention.Forced
    elif string == "END HALF":
        return Intervention.End_Half
    else:
        raise ValueError(f"Unknown intervention type: {string}")


def build_interference1(string: str) -> Interference1:
    if string == "INTERCEPTION":
        return Interference1.Interception
    elif string == "THEFT":
        return Interference1.Theft
    else:
        raise ValueError(f"Unknown interference1 type: {string}")


def build_interference2(string: str) -> Interference2:
    if string == "BLOCKED":
        return Interference2.Blocked
    elif string == "SAVED":
        return Interference2.Saved
    else:
        raise ValueError(f"Unknown interference2 type: {string}")


def build_challenge_type(string: str) -> ChallengeType:
    if string == "GROUND":
        return ChallengeType.Ground
    else:
        raise ValueError(f"Unknown challenge type: {string}")


def build_fault(string: str) -> Fault:
    if string == "FAULT":
        return Fault.Fault
    elif string == "ADVANTAGE":
        return Fault.Advantage
    else:
        raise ValueError(f"Unknown fault type: {string}")


def build_challenge_result(string: str) -> ChallengeResult:
    if string == "WON":
        return ChallengeResult.Won
    elif string == "LOST":
        return ChallengeResult.Lost
    else:
        raise ValueError(f"Unknown challenge result: {string}")


def build_owngoal(string: str) -> OwnGoal:
    if string == "GOAL":
        return OwnGoal.OwnGoal
    else:
        raise ValueError(f"Unknown owngoal type: {string}")


factories: Dict[Type[SubType], Callable] = {
    ChallengeType: build_challenge_type,
    Fault: build_fault,
    ChallengeResult: build_challenge_result,
    Interference1: build_interference1,
    Interference2: build_interference2,
    Intervention: build_intervention,
    Attempt: build_attempt,
    Offside: build_offside,
    BodyPart: build_bodypart,
    Deflection: build_deflection,
    ShotDirection: build_shotdirection,
    ShotResult: build_shotresult,
    Challenge: build_challenge,
    Card: build_card,
    SetPiece: build_setpiece,
    FKAttempt: build_fkattempt,
    Retaken: build_retaken,
    OwnGoal: build_owngoal,
}


def build_subtypes(
    items: List[str], subtype_types: List[Type[SubType]]
) -> List[Union[SubType, None]]:
    result = [None] * len(subtype_types)
    for item in items:
        if not item:
            continue

        for i, subtype_type in enumerate(subtype_types):
            assert (
                subtype_type in factories
            ), f"Factory missing for {subtype_type}"

            try:
                subtype = factories[subtype_type](item)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Cannot determine subtype type of {item}")

        result[i] = subtype

    return result
