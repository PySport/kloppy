from datetime import timedelta
from enum import IntEnum, Enum, EnumMeta
from typing import Dict, List, Optional, Union

from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardType,
    CarryResult,
    DuelQualifier,
    DuelResult,
    DuelType,
    Event,
    EventFactory,
    EventType,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    InterceptionResult,
    PassQualifier,
    PassResult,
    PassType,
    PositionType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
    Time,
    Point,
)
from kloppy.exceptions import DeserializationError


class TypesEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        if isinstance(value, dict):
            if value["id"] not in cls._value2member_map_:
                raise DeserializationError(
                    "Unknown SciSports {}: {}/{}".format(
                        (
                            cls.__qualname__.replace("_", " ")
                            .replace(".", " ")
                            .title()
                        ),
                        value["id"],
                        value["name"],
                    )
                )
            value = cls(value["id"])
        elif value not in cls._value2member_map_:
            raise DeserializationError(
                "Unknown SciSports {}: {}".format(
                    (
                        cls.__qualname__.replace("_", " ")
                        .replace(".", " ")
                        .title()
                    ),
                    value,
                )
            )
        return super().__call__(value, *args, **kw)


class EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """SciSports event types mapping"""

    PASS = 1
    CROSS = 2
    DRIBBLE = 3
    DEFENSIVE_DUEL = 4
    INTERCEPTION = 5
    SHOT = 6
    FOUL = 7
    BALL_DEAD = 8
    CLEARANCE = 10
    BAD_TOUCH = 11
    KEEPER_SAVE = 12
    BLOCK = 13
    PERIOD = 14
    CARD = 15
    SUBSTITUTE = 16
    FORMATION = 17
    POSITION = 18
    OTHER = 19


class BODY_PART(Enum, metaclass=TypesEnumMeta):
    """SciSports body part types"""

    UNKNOWN = -2
    NOT_APPLICABLE = -1
    FEET = 0
    LEFT_FOOT = 1
    RIGHT_FOOT = 2
    HEAD = 3
    HANDS = 4
    OTHER = 5
    UNKNOWN_ALT = 6


BODY_PART_MAPPING = {
    BODY_PART.UNKNOWN: BodyPart.OTHER,
    BODY_PART.NOT_APPLICABLE: BodyPart.OTHER,
    BODY_PART.FEET: BodyPart.OTHER,
    BODY_PART.LEFT_FOOT: BodyPart.LEFT_FOOT,
    BODY_PART.RIGHT_FOOT: BodyPart.RIGHT_FOOT,
    BODY_PART.HEAD: BodyPart.HEAD,
    BODY_PART.HANDS: BodyPart.BOTH_HANDS,
    BODY_PART.OTHER: BodyPart.OTHER,
    BODY_PART.UNKNOWN_ALT: BodyPart.OTHER,
}


class POSITION_TYPE(Enum, metaclass=TypesEnumMeta):
    """SciSports position types"""

    UNKNOWN = -2
    NOT_APPLICABLE = -1
    GOALKEEPER = 0
    LEFT_BACK = 1
    LEFT_WING_BACK = 2
    LEFT_CENTER_BACK = 3
    CENTER_BACK = 4
    RIGHT_CENTER_BACK = 5
    RIGHT_WING_BACK = 6
    RIGHT_BACK = 7
    LEFT_DEFENSIVE_MIDFIELDER = 8
    DEFENSIVE_MIDFIELDER = 9
    RIGHT_DEFENSIVE_MIDFIELDER = 10
    LEFT_CENTER_MIDFIELDER = 11
    CENTER_MIDFIELDER = 12
    RIGHT_CENTER_MIDFIELDER = 13
    LEFT_WING = 14
    RIGHT_WING = 15
    LEFT_WING_FORWARD = 16
    RIGHT_WING_FORWARD = 17
    LEFT_ATTACKING_MIDFIELDER = 18
    RIGHT_ATTACKING_MIDFIELDER = 19
    ATTACKING_MIDFIELDER = 20
    LEFT_CENTER_FORWARD = 21
    RIGHT_CENTER_FORWARD = 22
    CENTER_FORWARD = 23
    RIGHT_MIDFIELDER = 24
    LEFT_MIDFIELDER = 25


POSITION_TYPE_MAPPING = {
    POSITION_TYPE.UNKNOWN: None,
    POSITION_TYPE.NOT_APPLICABLE: None,
    POSITION_TYPE.GOALKEEPER: PositionType.Goalkeeper,
    POSITION_TYPE.LEFT_BACK: PositionType.LeftBack,
    POSITION_TYPE.LEFT_WING_BACK: PositionType.LeftWingBack,
    POSITION_TYPE.LEFT_CENTER_BACK: PositionType.CenterBack,
    POSITION_TYPE.CENTER_BACK: PositionType.CenterBack,
    POSITION_TYPE.RIGHT_CENTER_BACK: PositionType.CenterBack,
    POSITION_TYPE.RIGHT_WING_BACK: PositionType.RightWingBack,
    POSITION_TYPE.RIGHT_BACK: PositionType.RightBack,
    POSITION_TYPE.LEFT_DEFENSIVE_MIDFIELDER: PositionType.LeftDefensiveMidfield,
    POSITION_TYPE.DEFENSIVE_MIDFIELDER: PositionType.DefensiveMidfield,
    POSITION_TYPE.RIGHT_DEFENSIVE_MIDFIELDER: PositionType.RightDefensiveMidfield,
    POSITION_TYPE.LEFT_CENTER_MIDFIELDER: PositionType.LeftCentralMidfield,
    POSITION_TYPE.CENTER_MIDFIELDER: PositionType.CenterMidfield,
    POSITION_TYPE.RIGHT_CENTER_MIDFIELDER: PositionType.RightCentralMidfield,
    POSITION_TYPE.LEFT_WING: PositionType.LeftWing,
    POSITION_TYPE.RIGHT_WING: PositionType.RightWing,
    POSITION_TYPE.LEFT_WING_FORWARD: PositionType.LeftWing,
    POSITION_TYPE.RIGHT_WING_FORWARD: PositionType.RightWing,
    POSITION_TYPE.LEFT_ATTACKING_MIDFIELDER: PositionType.LeftAttackingMidfield,
    POSITION_TYPE.RIGHT_ATTACKING_MIDFIELDER: PositionType.RightAttackingMidfield,
    POSITION_TYPE.ATTACKING_MIDFIELDER: PositionType.AttackingMidfield,
    POSITION_TYPE.LEFT_CENTER_FORWARD: PositionType.LeftForward,
    POSITION_TYPE.RIGHT_CENTER_FORWARD: PositionType.RightForward,
    POSITION_TYPE.CENTER_FORWARD: PositionType.Striker,
    POSITION_TYPE.RIGHT_MIDFIELDER: PositionType.RightMidfield,
    POSITION_TYPE.LEFT_MIDFIELDER: PositionType.LeftMidfield,
}


# class POSSESSION_TYPE(Enum, metaclass=TypesEnumMeta):
#     """SciSports possession types"""
#
#     UNKNOWN = -2
#     NOT_APPLICABLE = -1
#     OPEN_PLAY = 0
#     THROW_IN = 1
#     FREE_KICK = 2
#     GOAL_KICK = 3
#     CORNER = 4
#     PENALTY = 5
#     COUNTER = 6
#     NONE = 7
#     BROADCAST_INTERRUPTION = 8


class RESULT(Enum, metaclass=TypesEnumMeta):
    """SciSports result types"""

    UNKNOWN = -2
    NOT_APPLICABLE = -1
    UNSUCCESSFUL = 0
    SUCCESSFUL = 1
    OTHER = 2


# SET_PIECE_TYPE_MAPPING = {
#     POSSESSION_TYPE.THROW_IN: SetPieceType.THROW_IN,
#     POSSESSION_TYPE.CORNER: SetPieceType.CORNER_KICK,
#     POSSESSION_TYPE.FREE_KICK: SetPieceType.FREE_KICK,
#     POSSESSION_TYPE.PENALTY: SetPieceType.PENALTY,
#     POSSESSION_TYPE.GOAL_KICK: SetPieceType.GOAL_KICK,
# }


FORMATION_MAPPING = {
    -2: FormationType.UNKNOWN,  # Unknown
    -1: None,  # Not Applicable
    0: FormationType.THREE_FOUR_THREE,  # 3-4-3
    1: FormationType.UNKNOWN,  # 3-2-2-3 (not in kloppy)
    2: FormationType.THREE_ONE_TWO_ONE_THREE,  # 3-1-2-1-3
    3: FormationType.UNKNOWN,  # 3-3-1-3 (not in kloppy)
    4: FormationType.UNKNOWN,  # 3-1-3-3 (not in kloppy)
    5: FormationType.THREE_FIVE_TWO,  # 3-5-2
    6: FormationType.THREE_TWO_THREE_TWO,  # 3-2-3-2
    7: FormationType.THREE_THREE_TWO_TWO,  # 3-3-2-2
    8: FormationType.THREE_ONE_FOUR_TWO,  # 3-1-4-2
    9: FormationType.THREE_FOUR_ONE_TWO,  # 3-4-1-2
    10: FormationType.FOUR_THREE_THREE,  # 4-3-3
    11: FormationType.UNKNOWN,  # 4-2-1-3 (not in kloppy)
    12: FormationType.UNKNOWN,  # 4-1-2-3 (not in kloppy)
    13: FormationType.FOUR_FOUR_TWO,  # 4-4-2
    14: FormationType.FOUR_ONE_TWO_ONE_TWO,  # 4-1-2-1-2
    15: FormationType.FOUR_TWO_TWO_TWO,  # 4-2-2-2
    16: FormationType.FOUR_ONE_THREE_TWO,  # 4-1-3-2
    17: FormationType.UNKNOWN,  # 4-3-1-2 (not in kloppy)
    18: FormationType.FOUR_FIVE_ONE,  # 4-5-1
    19: FormationType.FOUR_TWO_THREE_ONE,  # 4-2-3-1
    20: FormationType.FOUR_THREE_TWO_ONE,  # 4-3-2-1
    21: FormationType.FOUR_FOUR_ONE_ONE,  # 4-4-1-1
    22: FormationType.FOUR_ONE_FOUR_ONE,  # 4-1-4-1
    23: FormationType.FIVE_THREE_TWO,  # 5-3-2
    24: FormationType.UNKNOWN,  # 5-1-2-2 (not in kloppy)
    26: FormationType.FIVE_FOUR_ONE,  # 5-4-1
    27: FormationType.UNKNOWN,  # 5-1-2-1-1 (not in kloppy)
    28: FormationType.FIVE_TWO_TWO_ONE,  # 5-2-2-1
    29: FormationType.UNKNOWN,  # 5-3-1-1 (not in kloppy)
    30: FormationType.UNKNOWN,  # 5-1-3-1 (not in kloppy)
    31: FormationType.UNKNOWN,  # 5-2-3 (not in kloppy)
    32: FormationType.UNKNOWN,  # Unknown
}


class EVENT:
    """Base class for SciSports events.

    This class is used to deserialize SciSports events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event

    def set_refs(self, teams, periods):
        """Set references to teams and periods"""
        from .helpers import get_team_by_id, get_period_by_id

        self.team = get_team_by_id(self.raw_event.get("teamId"), teams)
        self.period = get_period_by_id(
            self.raw_event.get("partId", 1), periods
        )

        self.player = None
        if self.team:
            player_id = str(self.raw_event.get("playerId", -1))
            self.player = self.team.get_player_by_id(player_id)

        return self

    def deserialize(
        self, event_factory: EventFactory, **kwargs
    ) -> List[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.
            **kwargs: Additional arguments to pass to event creation (e.g., replacement_player for substitutions).

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()

        # Add any additional kwargs (like replacement_player for substitutions)
        generic_event_kwargs.update(kwargs)

        # Create events
        base_events = self._create_events(
            event_factory, **generic_event_kwargs
        )

        return base_events

    def _parse_generic_kwargs(self) -> Dict:
        """Parse generic event kwargs from SciSports raw event"""
        # Convert time from milliseconds to seconds, relative to period start
        timestamp_ms = self.raw_event.get("startTimeMs", 0)
        absolute_timestamp_seconds = timestamp_ms / 1000.0

        # Make timestamp relative to period start
        period_start_seconds = self.period.start_timestamp.total_seconds()
        relative_timestamp_seconds = (
            absolute_timestamp_seconds - period_start_seconds
        )
        timestamp = timedelta(seconds=relative_timestamp_seconds)

        # Get coordinates
        start_x = self.raw_event.get("startPosXM", 0.0)
        start_y = self.raw_event.get("startPosYM", 0.0)
        coordinates = (
            Point(x=start_x, y=start_y)
            if start_x is not None and start_y is not None
            else None
        )

        return {
            "period": self.period,
            "timestamp": timestamp,
            "team": self.team,
            "player": self.player,
            "coordinates": coordinates,
            "ball_owning_team": self.team,  # Assume the team performing the action owns the ball
            "ball_state": BallState.ALIVE,
            "event_id": str(self.raw_event.get("eventId", "")),
            "raw_event": self.raw_event,
        }

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        """Create the base event - override in subclasses"""
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event.get("baseTypeName", "Unknown"),
            **generic_event_kwargs,
        )
        return [generic_event]


class PASS(EVENT):
    """SciSports 1/Pass and 2/Cross events."""

    class SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        PASS = 100
        THROW_IN = 101
        FREE_KICK = 102
        CORNER_SHORT = 103
        GOAL_KICK = 104
        GK_THROW = 105
        KICK_OFF = 106
        OFFSIDE_PASS = 107
        LAUNCH = 108

    class CROSS_SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        CROSS = 200
        CORNER_CROSSED = 201
        FREE_KICK_CROSSED = 202
        CROSS_BLOCKED = 203
        CUTBACK_CROSS = 204
        THROW_IN_CROSSED = 205

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Determine result based on SciSports data
        result = RESULT(self.raw_event["resultId"])
        if result == RESULT.SUCCESSFUL:
            result = PassResult.COMPLETE
        elif result == RESULT.UNSUCCESSFUL:
            result = PassResult.INCOMPLETE
        else:
            raise DeserializationError(f"Unknown pass result: {result}")

        # Add qualifiers based on event type
        qualifiers = []
        event_type = EVENT_TYPE(self.raw_event["baseTypeId"])

        if event_type == EVENT_TYPE.CROSS:
            qualifiers.append(PassQualifier(value=PassType.CROSS))

        # Handle all pass subtypes according to SciSports documentation
        sub_type_id = self.raw_event["subTypeId"]

        # Define mappings using enum values
        PASS_QUALIFIER_MAPPING = {
            PASS.SUB_TYPE.PASS: [],  # Regular open play pass
            PASS.SUB_TYPE.THROW_IN: [
                SetPieceQualifier(value=SetPieceType.THROW_IN)
            ],
            PASS.SUB_TYPE.FREE_KICK: [
                SetPieceQualifier(value=SetPieceType.FREE_KICK)
            ],
            PASS.SUB_TYPE.CORNER_SHORT: [
                SetPieceQualifier(value=SetPieceType.CORNER_KICK)
            ],
            PASS.SUB_TYPE.GOAL_KICK: [
                SetPieceQualifier(value=SetPieceType.GOAL_KICK)
            ],
            PASS.SUB_TYPE.GK_THROW: [
                PassQualifier(value=PassType.LAUNCH)
            ],  # Goalkeeper Throw
            PASS.SUB_TYPE.KICK_OFF: [
                SetPieceQualifier(value=SetPieceType.KICK_OFF)
            ],
            PASS.SUB_TYPE.OFFSIDE_PASS: PassResult.OFFSIDE,  # Offside Pass
            PASS.SUB_TYPE.LAUNCH: [
                PassQualifier(value=PassType.LAUNCH)
            ],  # Launch Pass
        }

        CROSS_QUALIFIER_MAPPING = {
            PASS.CROSS_SUB_TYPE.CROSS: [
                PassQualifier(value=PassType.CROSS)
            ],  # Regular cross
            PASS.CROSS_SUB_TYPE.CORNER_CROSSED: [
                SetPieceQualifier(value=SetPieceType.CORNER_KICK),
                PassQualifier(value=PassType.CROSS),
            ],
            PASS.CROSS_SUB_TYPE.FREE_KICK_CROSSED: [
                SetPieceQualifier(value=SetPieceType.FREE_KICK),
                PassQualifier(value=PassType.CROSS),
            ],
            PASS.CROSS_SUB_TYPE.CROSS_BLOCKED: PassResult.INCOMPLETE,  # Blocked cross
            PASS.CROSS_SUB_TYPE.CUTBACK_CROSS: [
                PassQualifier(value=PassType.CROSS)
            ],  # Cross cutback
            PASS.CROSS_SUB_TYPE.THROW_IN_CROSSED: [
                SetPieceQualifier(value=SetPieceType.THROW_IN),
                PassQualifier(value=PassType.CROSS),
            ],
        }

        # Convert sub_type_id to enum and apply mapping
        # First try pass sub types
        if sub_type_id in [e.value for e in PASS.SUB_TYPE]:
            sub_type_enum = PASS.SUB_TYPE(sub_type_id)
            if sub_type_enum in PASS_QUALIFIER_MAPPING:
                value = PASS_QUALIFIER_MAPPING[sub_type_enum]
                if isinstance(value, list):
                    qualifiers.extend(value)
                else:
                    result = value
        # Then try cross sub types
        elif sub_type_id in [e.value for e in PASS.CROSS_SUB_TYPE]:
            cross_sub_type_enum = PASS.CROSS_SUB_TYPE(sub_type_id)
            if cross_sub_type_enum in CROSS_QUALIFIER_MAPPING:
                value = CROSS_QUALIFIER_MAPPING[cross_sub_type_enum]
                if isinstance(value, list):
                    qualifiers.extend(value)
                else:
                    result = value
        elif sub_type_id is not None:
            # Unknown sub_type_id - let the enum constructor raise a proper error
            # This will trigger TypesEnumMeta's error handling
            PASS.SUB_TYPE(sub_type_id)

        # Add body part qualifiers if available
        body_part_id = self.raw_event.get("bodyPartId")
        if body_part_id is not None:
            body_part_enum = BODY_PART(body_part_id)
            body_part = BODY_PART_MAPPING.get(body_part_enum, BodyPart.OTHER)
            qualifiers.append(BodyPartQualifier(value=body_part))
            if body_part == BodyPart.HEAD:
                qualifiers.append(PassQualifier(value=PassType.HEAD_PASS))

        # Get end coordinates
        end_x = self.raw_event.get("endPosXM")
        end_y = self.raw_event.get("endPosYM")
        receiver_coordinates = (
            Point(x=end_x, y=end_y)
            if end_x is not None and end_y is not None
            else None
        )

        # Calculate receive timestamp (add duration if available)
        receive_timestamp = generic_event_kwargs["timestamp"]
        duration = self.raw_event.get("durationMs", 0)
        if duration > 0:
            # Use Time object addition which handles period boundaries
            receive_timestamp = receive_timestamp + timedelta(
                milliseconds=duration
            )

        # Try to find receiver player
        receiver_player = None
        receiver_id = self.raw_event.get("receiverId")
        if receiver_id and receiver_id != -1:
            team = generic_event_kwargs["team"]
            # Check if receiver is on the same team
            receiver_team_id = self.raw_event.get("receiverTeamId")
            if receiver_team_id and str(receiver_team_id) == str(team.team_id):
                receiver_player = team.get_player_by_id(str(receiver_id))

        pass_event = event_factory.build_pass(
            result=result,
            qualifiers=qualifiers,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            **generic_event_kwargs,
        )
        return [pass_event]


class SHOT(EVENT):
    """SciSports 6/Shot event."""

    class SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        SHOT = 600
        SHOT_FREE_KICK = 601
        SHOT_PENALTY = 602
        SHOT_CORNER = 603

    class RESULT_TYPE(Enum, metaclass=TypesEnumMeta):
        """Shot result types from shotTypeId"""

        UNKNOWN = -2
        NOT_APPLICABLE = -1
        WIDE = 1
        POST = 2
        ON_TARGET = 3
        BLOCKED = 4

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        qualifiers = []
        result = ShotResult.OFF_TARGET  # Default assumption

        # Primary result determination based on resultId (successful/unsuccessful)
        result_id = self.raw_event.get("resultId")

        # According to documentation: Shot (6) -> Shot (600) -> Unsuccessful (0) / Successful (1)
        # Successful (1) = goal, Unsuccessful (0) = not a goal
        result_enum = RESULT(result_id)
        if result_enum == RESULT.SUCCESSFUL:
            result = ShotResult.GOAL
        elif result_enum == RESULT.UNSUCCESSFUL:
            # For unsuccessful shots, determine specific result type from shotTypeId
            shot_type_id = self.raw_event.get("shotTypeId")
            if shot_type_id is not None:
                shot_result_enum = SHOT.RESULT_TYPE(shot_type_id)
                # Map shotTypeId to specific shot results
                if shot_result_enum == SHOT.RESULT_TYPE.WIDE:
                    result = ShotResult.OFF_TARGET
                elif shot_result_enum == SHOT.RESULT_TYPE.POST:
                    result = ShotResult.POST
                elif shot_result_enum == SHOT.RESULT_TYPE.ON_TARGET:
                    result = (
                        ShotResult.SAVED
                    )  # On target but unsuccessful = saved
                elif shot_result_enum == SHOT.RESULT_TYPE.BLOCKED:
                    result = ShotResult.BLOCKED

        # Add set piece qualifiers based on sub_type
        sub_type_id = self.raw_event.get("subTypeId")
        if sub_type_id is not None:
            sub_type_enum = SHOT.SUB_TYPE(sub_type_id)
            if sub_type_enum == SHOT.SUB_TYPE.SHOT_FREE_KICK:
                qualifiers.append(
                    SetPieceQualifier(value=SetPieceType.FREE_KICK)
                )
            elif sub_type_enum == SHOT.SUB_TYPE.SHOT_PENALTY:
                qualifiers.append(
                    SetPieceQualifier(value=SetPieceType.PENALTY)
                )
            elif sub_type_enum == SHOT.SUB_TYPE.SHOT_CORNER:
                qualifiers.append(
                    SetPieceQualifier(value=SetPieceType.CORNER_KICK)
                )

        # Add body part qualifiers
        body_part_id = self.raw_event.get("bodyPartId")
        if body_part_id is not None:
            body_part_enum = BODY_PART(body_part_id)
            body_part = BODY_PART_MAPPING.get(body_part_enum, BodyPart.OTHER)
            qualifiers.append(BodyPartQualifier(value=body_part))

        # Get result coordinates (where the shot ended up)
        end_x = self.raw_event.get("endPosXM")
        end_y = self.raw_event.get("endPosYM")
        result_coordinates = (
            Point(x=end_x, y=end_y)
            if end_x is not None and end_y is not None
            else None
        )

        shot_event = event_factory.build_shot(
            result=result,
            qualifiers=qualifiers,
            result_coordinates=result_coordinates,
            **generic_event_kwargs,
        )
        return [shot_event]


class DRIBBLE(EVENT):
    """SciSports 3/Dribble event."""

    class SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        CARRY = 300
        TAKE_ON = 301

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Get end coordinates
        end_x = self.raw_event.get("endPosXM")
        end_y = self.raw_event.get("endPosYM")
        end_coordinates = (
            Point(x=end_x, y=end_y)
            if end_x is not None and end_y is not None
            else None
        )

        # Calculate end timestamp
        end_timestamp = generic_event_kwargs["timestamp"]
        duration = self.raw_event.get("durationMs", 0)
        if duration > 0:
            # Use Time object addition which handles period boundaries
            end_timestamp = end_timestamp + timedelta(milliseconds=duration)

        # Determine event type based on subtype
        sub_type_id = self.raw_event.get("subTypeId")
        sub_type = DRIBBLE.SUB_TYPE(sub_type_id)

        # Determine result based on SciSports data
        result_id = self.raw_event.get("resultId", 1)  # Default to successful
        result_enum = RESULT(result_id)

        if sub_type == DRIBBLE.SUB_TYPE.CARRY:
            # Create CarryEvent
            if result_enum == RESULT.SUCCESSFUL:
                carry_result = CarryResult.COMPLETE
            else:
                carry_result = CarryResult.INCOMPLETE

            carry_event = event_factory.build_carry(
                result=carry_result,
                qualifiers=None,
                end_timestamp=end_timestamp,
                end_coordinates=end_coordinates,
                **generic_event_kwargs,
            )
            return [carry_event]

        elif sub_type == DRIBBLE.SUB_TYPE.TAKE_ON:
            # Create TakeOnEvent
            if result_enum == RESULT.SUCCESSFUL:
                takeon_result = TakeOnResult.COMPLETE
            else:
                takeon_result = TakeOnResult.INCOMPLETE

            takeon_event = event_factory.build_take_on(
                result=takeon_result,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [takeon_event]

        else:
            # Unknown subtype, fallback to generic
            return super()._create_events(
                event_factory, **generic_event_kwargs
            )


class INTERCEPTION(EVENT):
    """SciSports 5/Interception event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Most interceptions are successful by definition
        result = InterceptionResult.SUCCESS

        interception_event = event_factory.build_interception(
            result=result,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [interception_event]


class DEFENSIVE_DUEL(EVENT):
    """SciSports 4/Defensive Duel event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Determine if duel was won or lost
        result = DuelResult.WON  # Default assumption for defensive actions

        # Add ground duel qualifier
        qualifiers = [DuelQualifier(value=DuelType.GROUND)]

        duel_event = event_factory.build_duel(
            result=result,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [duel_event]


class CLEARANCE(EVENT):
    """SciSports 10/Clearance event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Add body part qualifiers if available
        qualifiers = []
        body_part_id = self.raw_event.get("bodyPartId")
        if body_part_id is not None:
            body_part = BODY_PART_MAPPING.get(body_part_id, BodyPart.OTHER)
            qualifiers.append(BodyPartQualifier(value=body_part))

        clearance_event = event_factory.build_clearance(
            result=None,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [clearance_event]


class BAD_TOUCH(EVENT):
    """SciSports 11/Bad Touch event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        miscontrol_event = event_factory.build_miscontrol(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [miscontrol_event]


class KEEPER_SAVE(EVENT):
    """SciSports 12/Keeper Save event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Add goalkeeper qualifiers
        qualifiers = [GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)]

        # Add body part qualifiers if available
        body_part_id = self.raw_event.get("bodyPartId")
        if body_part_id is not None:
            body_part = BODY_PART_MAPPING.get(body_part_id, BodyPart.OTHER)
            qualifiers.append(BodyPartQualifier(value=body_part))

        goalkeeper_event = event_factory.build_goalkeeper_event(
            result=None,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [goalkeeper_event]


class BLOCK(EVENT):
    """SciSports 13/Block event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Blocks are treated as interceptions
        qualifiers = []
        body_part_id = self.raw_event.get("bodyPartId")
        if body_part_id is not None:
            body_part = BODY_PART_MAPPING.get(body_part_id, BodyPart.OTHER)
            qualifiers.append(BodyPartQualifier(value=body_part))

        interception_event = event_factory.build_interception(
            result=InterceptionResult.LOST,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [interception_event]


class FOUL(EVENT):
    """SciSports 7/Foul event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        """Foul types from foulTypeId"""

        UNKNOWN = -2
        NOT_APPLICABLE = -1
        HANDS = 1
        TACKLE = 2
        AERIAL = 3
        PROTESTING = 4
        PASSING = 5
        OFFSIDE = 6
        UNSPORTSMANLIKE = 7
        DANGEROUS = 8
        BENCH = 9
        OBSTRUCTION = 10
        NONE = 11

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        foul_event = event_factory.build_foul_committed(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [foul_event]


class CARD(EVENT):
    """SciSports 15/Card event."""

    class SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        YELLOW_CARD = 1500
        SECOND_YELLOW = 1501
        RED_CARD = 1502

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Map card types from SciSports data based on subTypeName
        sub_type_name = self.raw_event.get("subTypeName", "")

        if sub_type_name == "YELLOW_CARD":
            card_type = CardType.FIRST_YELLOW
        elif sub_type_name == "SECOND_YELLOW_CARD":
            card_type = CardType.SECOND_YELLOW
        elif sub_type_name == "RED_CARD":
            card_type = CardType.RED
        else:
            # Default to first yellow if we can't determine
            card_type = CardType.FIRST_YELLOW

        card_event = event_factory.build_card(
            card_type=card_type,
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [card_event]


class SUBSTITUTE(EVENT):
    """SciSports 16/Substitute event."""

    class SUB_TYPE(Enum, metaclass=TypesEnumMeta):
        SUBBED_OUT = 1600
        SUBBED_IN = 1601

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # SciSports has separate SUBBED_OUT and SUBBED_IN events
        # Only create SubstitutionEvent for SUBBED_OUT events with replacement player info
        sub_type = self.raw_event.get("subTypeName")

        if sub_type == "SUBBED_OUT":
            # Check if replacement player was provided by the deserializer
            replacement_player = generic_event_kwargs.get("replacement_player")

            if replacement_player:
                substitution_event = event_factory.build_substitution(
                    replacement_player=replacement_player,
                    result=None,
                    qualifiers=None,
                    **{
                        k: v
                        for k, v in generic_event_kwargs.items()
                        if k != "replacement_player"
                    },
                )
                return [substitution_event]
            else:
                # Fallback to generic event if we can't find replacement player
                return super()._create_events(
                    event_factory, **generic_event_kwargs
                )

        elif sub_type == "SUBBED_IN":
            # This is handled by the SUBBED_OUT event, so skip it
            return []

        else:
            # Unknown substitution type, fallback to generic
            return super()._create_events(
                event_factory, **generic_event_kwargs
            )


class BALL_DEAD(EVENT):
    """SciSports 8/Ball Dead event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        # Update ball state to dead
        generic_event_kwargs["ball_state"] = BallState.DEAD

        ball_out_event = event_factory.build_ball_out(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [ball_out_event]


class FORMATION(EVENT):
    """SciSports 17/Formation event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        sub_type_id = self.raw_event.get("subTypeId")

        # Only process FORMATION_CHANGE events (1701), skip TEAM_STARTING_FORMATION (1700)
        if sub_type_id == 1701:  # FORMATION_CHANGE
            formation_type_id = self.raw_event.get("formationTypeId", -2)
            formation_type = get_formation_type(formation_type_id)

            formation_event = event_factory.build_formation_change(
                formation_type=formation_type,
                player_positions=None,  # TODO: Parse player positions if available
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [formation_event]
        else:
            # Skip TEAM_STARTING_FORMATION events as they are handled in metadata
            return []


class POSITION(EVENT):
    """SciSports 18/Position event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        sub_type_id = self.raw_event.get("subTypeId")

        # Only process PLAYER_POSITION_CHANGE events (1801), skip PLAYER_STARTING_POSITION (1800)
        if sub_type_id == 1801:  # PLAYER_POSITION_CHANGE
            # Get the player and their new position
            player = generic_event_kwargs.get("player")
            team = generic_event_kwargs.get("team")
            new_position_type_id = self.raw_event.get("positionTypeId", -1)
            new_position_type = get_position_type(new_position_type_id)

            # Create a FormationChangeEvent where the formation stays the same
            # but the specific player's position changes
            player_positions = None
            if player and new_position_type:
                player_positions = {player: new_position_type}

            # Keep the current formation type (we don't change the overall formation)
            current_formation = (
                team.starting_formation if team else FormationType.UNKNOWN
            )

            formation_event = event_factory.build_formation_change(
                formation_type=current_formation,
                player_positions=player_positions,
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [formation_event]
        else:
            # Skip PLAYER_STARTING_POSITION events as they are handled in metadata
            return []


def _get_body_part_qualifiers(raw_event: Dict) -> List[BodyPartQualifier]:
    """Get body part qualifiers from SciSports event"""
    qualifiers = []
    body_part_id = raw_event.get("bodyPartId")
    if body_part_id is not None:
        body_part = BODY_PART_MAPPING.get(body_part_id, BodyPart.OTHER)
        qualifiers.append(BodyPartQualifier(value=body_part))
    return qualifiers


def get_body_part(body_part_id: int) -> BodyPart:
    """Get kloppy BodyPart from SciSports bodyPartId"""
    body_part_enum = BODY_PART(body_part_id)
    return BODY_PART_MAPPING.get(body_part_enum, BodyPart.OTHER)


def get_position_type(position_type_id: int) -> PositionType:
    """Get kloppy PositionType from SciSports positionTypeId"""
    position_enum = POSITION_TYPE(position_type_id)
    return POSITION_TYPE_MAPPING.get(position_enum)


# def get_set_piece_type(base_type_id: int) -> SetPieceType:
#     """Get kloppy SetPieceType from SciSports baseTypeId"""
#     return SET_PIECE_TYPE_MAPPING.get(base_type_id)


def get_formation_type(formation_type_id: int) -> FormationType:
    """Get kloppy FormationType from SciSports formationTypeId"""
    return FORMATION_MAPPING.get(formation_type_id, FormationType.UNKNOWN)


def event_decoder(raw_event: Union[Dict, int]) -> Optional[EVENT]:
    """Decode SciSports raw event into appropriate event class"""
    # Handle case where raw_event is not a dict (malformed data)
    # if not isinstance(raw_event, dict):
    #     return None

    base_type_id = raw_event.get("baseTypeId")
    sub_type_id = raw_event.get("subTypeId")

    # Convert base_type_id to EVENT_TYPE enum
    event_type = EVENT_TYPE(base_type_id)

    # Skip metadata-only events
    if event_type == EVENT_TYPE.PERIOD:
        return None

    # Skip PLAYER_STARTING_POSITION events as they are handled in metadata
    if event_type == EVENT_TYPE.POSITION and sub_type_id == 1800:
        return None

    # Skip TEAM_STARTING_FORMATION events as they are handled in metadata
    if event_type == EVENT_TYPE.FORMATION and sub_type_id == 1700:
        return None

    type_to_event = {
        EVENT_TYPE.PASS: PASS,
        EVENT_TYPE.CROSS: PASS,
        EVENT_TYPE.DRIBBLE: DRIBBLE,
        EVENT_TYPE.DEFENSIVE_DUEL: DEFENSIVE_DUEL,
        EVENT_TYPE.INTERCEPTION: INTERCEPTION,
        EVENT_TYPE.SHOT: SHOT,
        EVENT_TYPE.FOUL: FOUL,
        EVENT_TYPE.BALL_DEAD: BALL_DEAD,
        EVENT_TYPE.CLEARANCE: CLEARANCE,
        EVENT_TYPE.BAD_TOUCH: BAD_TOUCH,
        EVENT_TYPE.KEEPER_SAVE: KEEPER_SAVE,
        EVENT_TYPE.BLOCK: BLOCK,
        EVENT_TYPE.CARD: CARD,
        EVENT_TYPE.SUBSTITUTE: SUBSTITUTE,
        EVENT_TYPE.FORMATION: FORMATION,
        EVENT_TYPE.POSITION: POSITION,
    }

    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
