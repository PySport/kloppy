from datetime import timedelta
from enum import Enum
from typing import Dict, List, Union

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
    GoalkeeperActionType,
    GoalkeeperQualifier,
    InterceptionResult,
    PassQualifier,
    PassResult,
    PassType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    Team,
    UnderPressureQualifier,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.impect.helpers import (
    get_period_by_id,
    get_team_by_id,
    parse_coordinates,
    parse_shot_end_coordinates,
    parse_timestamp,
)


class EVENT_TYPE(Enum):
    """The list of event types that compose all of Impect data."""

    PASS = "PASS"
    DRIBBLE = "DRIBBLE"
    SHOT = "SHOT"
    RECEPTION = "RECEPTION"
    LOOSE_BALL_REGAIN = "LOOSE_BALL_REGAIN"
    INTERCEPTION = "INTERCEPTION"
    CLEARANCE = "CLEARANCE"
    GROUND_DUEL = "GROUND_DUEL"
    BLOCK = "BLOCK"
    KICK_OFF = "KICK_OFF"
    THROW_IN = "THROW_IN"
    FREE_KICK = "FREE_KICK"
    PENALTY_KICK = "PENALTY_KICK"
    GOAL_KICK = "GOAL_KICK"
    CORNER = "CORNER"
    GK_CATCH = "GK_CATCH"
    GK_SAVE = "GK_SAVE"
    GOAL = "GOAL"  # we do not handle this because they have a separate event for a goal and a shot
    OWN_GOAL = "OWN_GOAL"
    OUT = "OUT"
    OFFSIDE = "OFFSIDE"
    FOUL = "FOUL"
    FINAL_WHISTLE = "FINAL_WHISTLE"
    REFEREE_INTERCEPTION = "REFEREE_INTERCEPTION"
    NO_VIDEO = "NO_VIDEO"
    YELLOW_CARD = "YELLOW_CARD"
    SECOND_YELLOW_CARD = "SECOND_YELLOW_CARD"
    RED_CARD = "RED_CARD"


class BODYPART(Enum):
    """The list of body parts used in Impect data."""

    FOOT_RIGHT = "FOOT_RIGHT"
    FOOT_LEFT = "FOOT_LEFT"
    FOOT = "FOOT"
    BODY = "BODY"
    HEAD = "HEAD"
    HAND = "HAND"


class DUELTYPE(Enum):
    """The list of duel types used in Impect data."""

    AERIAL_DUEL = "AERIAL_DUEL"
    GROUND_DUEL = "GROUND_DUEL"


class EVENT:
    """Base class for Impect events.

    This class is used to deserialize Impect events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event

    def set_refs(self, periods, teams, events):
        self.period = get_period_by_id(self.raw_event["periodId"], periods)
        self.team = (
            get_team_by_id(self.raw_event["squadId"], teams)
            if self.raw_event["squadId"]
            else None
        )
        self.possession_team = (
            get_team_by_id(self.raw_event["currentAttackingSquadId"], teams)
            if self.raw_event["currentAttackingSquadId"]
            else None
        )
        self.player = (
            self.team.get_player_by_id(self.raw_event["player"]["id"])
            if self.raw_event["player"]
            else None
        )
        self.statistics = []

        return self

    def deserialize(
        self, event_factory: EventFactory, teams: List[Team]
    ) -> List[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.
            periods: The periods in the match.
            teams: The teams in the match.
            events: All events in the match.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()
        events = self._create_events(
            event_factory, teams, **generic_event_kwargs
        )

        # Add UnderPressureQualifier to events if pressure > 0
        for event in events:
            self._add_under_pressure_qualifier(event)

        return events

    def _add_under_pressure_qualifier(self, event: Event) -> Event:
        """Add UnderPressureQualifier if pressure > 0."""
        pressure = self.raw_event.get("pressure")
        if pressure and pressure > 0:
            q = UnderPressureQualifier(True)
            event.qualifiers = event.qualifiers or []
            event.qualifiers.append(q)

        return event

    def _parse_generic_kwargs(self) -> Dict:
        timestamp, _ = parse_timestamp(self.raw_event["gameTime"]["gameTime"])
        return {
            "period": self.period,
            "timestamp": timestamp,
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.ALIVE,
            "event_id": str(self.raw_event["id"]),
            "team": self.team,
            "player": self.player,
            "coordinates": (
                parse_coordinates(self.raw_event["start"]["adjCoordinates"])
                if self.raw_event["start"]
                else None
            ),
            "statistics": self.statistics,
            "related_event_ids": self.raw_event.get("related_events", []),
            "raw_event": self.raw_event,
        }

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["actionType"],
            **generic_event_kwargs,
        )
        return [generic_event]


class PASS(EVENT):
    """Impect Pass event."""

    class ACTION(Enum):
        LOW_PASS = "LOW_PASS"
        LOW_CROSS = "LOW_CROSS"
        HIGH_CROSS = "HIGH_CROSS"
        DIAGONAL_PASS = "DIAGONAL_PASS"
        CHIPPED_PASS = "CHIPPED_PASS"
        SHORT_AERIAL_PASS = "SHORT_AERIAL_PASS"
        HEADER = "HEADER"

    class RESULT(Enum):
        FAIL = "FAIL"
        SUCCESS = "SUCCESS"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        (
            qualifiers,
            receive_timestamp,
            receiver_coordinates,
            receiver_player,
            result,
        ) = create_pass_props(self, generic_event_kwargs)

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


class DRIBBLE(EVENT):
    """Impect Dribble event."""

    class ACTION(Enum):
        DRIBBLE = "DRIBBLE"

    class RESULT(Enum):
        FAIL = "FAIL"
        SUCCESS = "SUCCESS"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        result = (
            CarryResult.COMPLETE
            if self.raw_event["result"] == "SUCCESS"
            else CarryResult.INCOMPLETE
        )
        end_coordinates_info = self.raw_event["end"]
        if end_coordinates_info:
            end_coordinates = parse_coordinates(
                end_coordinates_info["adjCoordinates"]
            )
        else:
            end_coordinates = None
        duration = (
            self.raw_event["duration"] if self.raw_event["duration"] else 0
        )
        end_timestamp = generic_event_kwargs["timestamp"] + timedelta(
            seconds=duration
        )

        body_part = BODYPART(self.raw_event["bodyPartExtended"])

        qualifiers = _get_body_part_qualifiers(body_part)

        carry_event = event_factory.build_carry(
            result=result,
            end_coordinates=end_coordinates,
            end_timestamp=end_timestamp,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [carry_event]


class SHOT(EVENT):
    """Impect Shot event."""

    class ACTION(Enum):
        LONG_RANGE_SHOT = "LONG_RANGE_SHOT"
        MID_RANGE_SHOT = "MID_RANGE_SHOT"
        CLOSE_RANGE_SHOT = "CLOSE_RANGE_SHOT"
        ONE_VS_ONE_AGAINST_GK = "ONE_VS_ONE_AGAINST_GK"
        OPEN_GOAL_SHOT = "OPEN_GOAL_SHOT"
        PENALTY_KICK = "PENALTY_KICK"
        HEADER = "HEADER"
        DIRECT_FREE_KICK = "DIRECT_FREE_KICK"
        BLOCK = "BLOCK"

    class RESULT(Enum):
        FAIL = "FAIL"
        SUCCESS = "SUCCESS"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        shot_dict = self.raw_event["shot"]
        result = self.RESULT(self.raw_event["result"])

        shot_end_coordinates, shot_result = parse_shot_end_coordinates(
            shot_dict, result
        )

        body_part = BODYPART(self.raw_event["bodyPartExtended"])

        qualifiers = _get_body_part_qualifiers(body_part)
        if self.raw_event["action"]:
            action = self.ACTION(self.raw_event["action"])
            if action == self.ACTION.PENALTY_KICK:
                qualifiers.append(
                    SetPieceQualifier(value=SetPieceType.PENALTY)
                )
            elif action == self.ACTION.DIRECT_FREE_KICK:
                qualifiers.append(
                    SetPieceQualifier(value=SetPieceType.FREE_KICK)
                )
            elif (
                action == self.ACTION.BLOCK and shot_result != ShotResult.GOAL
            ):
                shot_result = ShotResult.BLOCKED

        shot_event = event_factory.build_shot(
            result=shot_result,
            result_coordinates=shot_end_coordinates,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [shot_event]


class LOOSE_BALL_REGAIN(EVENT):
    class ACTION(Enum):
        LOOSE_BALL_REGAIN = "LOOSE_BALL_REGAIN"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        duel_type_mapping = {
            DUELTYPE.AERIAL_DUEL: DuelType.AERIAL,
            DUELTYPE.GROUND_DUEL: DuelType.GROUND,
        }
        built_events = []

        body_part = BODYPART(self.raw_event["bodyPartExtended"])
        qualifiers = _get_body_part_qualifiers(body_part)

        duel_info = self.raw_event["duel"]
        if duel_info:
            impect_duel_type = DUELTYPE(duel_info["duelType"])
            kloppy_duel_type = duel_type_mapping[impect_duel_type]
            aerial_duel_qualifiers = [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=kloppy_duel_type),
            ]

            aerial_duel_generic_event_kwargs = generic_event_kwargs.copy()
            player_id = generic_event_kwargs["player"].player_id
            aerial_duel_generic_event_kwargs[
                "event_id"
            ] = f"{player_id}-aerial-duel-{generic_event_kwargs['event_id']}"
            aerial_duel_event = event_factory.build_duel(
                result=DuelResult.WON,
                qualifiers=aerial_duel_qualifiers,
                **aerial_duel_generic_event_kwargs,
            )
            built_events.append(aerial_duel_event)

            opponent_aerial_duel_generic_event_kwargs = (
                generic_event_kwargs.copy()
            )
            opponent_team = next(
                team for team in teams if team.team_id != self.team.team_id
            )
            opponent_player = opponent_team.get_player_by_id(
                str(duel_info["playerId"])
            )
            opponent_aerial_duel_generic_event_kwargs.update(
                {
                    "team": opponent_team,
                    "player": opponent_player,
                    "event_id": f"{opponent_player.player_id}-aerial-duel-{generic_event_kwargs['event_id']}",
                }
            )
            opponent_aerial_duel_event = event_factory.build_duel(
                result=DuelResult.LOST,
                qualifiers=aerial_duel_qualifiers,
                **opponent_aerial_duel_generic_event_kwargs,
            )
            built_events.append(opponent_aerial_duel_event)

        recovery_event = event_factory.build_recovery(
            qualifiers=qualifiers,
            result=None,
            **generic_event_kwargs,
        )
        built_events.append(recovery_event)

        return built_events


class INTERCEPTION(EVENT):
    class ACTION(Enum):
        INTERCEPTION = "INTERCEPTION"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])

        qualifiers = _get_body_part_qualifiers(body_part)

        interception_event = event_factory.build_interception(
            qualifiers=qualifiers,
            result=InterceptionResult.SUCCESS,
            **generic_event_kwargs,
        )

        return [interception_event]


class CLEARANCE(EVENT):
    class ACTION(Enum):
        CLEARANCE = "CLEARANCE"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])

        qualifiers = _get_body_part_qualifiers(body_part)

        clearance_event = event_factory.build_clearance(
            qualifiers=qualifiers,
            result=None,
            **generic_event_kwargs,
        )

        return [clearance_event]


class GROUND_DUEL(EVENT):
    class ACTION(Enum):
        DUEL = "DUEL"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])

        qualifiers = _get_body_part_qualifiers(body_part)
        qualifiers.append(DuelQualifier(value=DuelType.GROUND))

        duel_event = event_factory.build_duel(
            qualifiers=qualifiers,
            result=DuelResult.WON,
            **generic_event_kwargs,
        )

        opponent_event_kwargs = generic_event_kwargs.copy()
        opponent_team = next(
            team for team in teams if team.team_id != self.team.team_id
        )
        opponent_player = opponent_team.get_player_by_id(
            str(self.raw_event["duel"]["playerId"])
        )
        opponent_event_kwargs.update(
            {
                "team": opponent_team,
                "player": opponent_player,
                "event_id": f"{opponent_player.player_id}-ground-duel-{generic_event_kwargs['event_id']}",
            }
        )
        opponent_duel_event = event_factory.build_duel(
            qualifiers=[DuelQualifier(value=DuelType.GROUND)],
            result=DuelResult.LOST,
            **opponent_event_kwargs,
        )

        return [duel_event, opponent_duel_event]


class KICK_OFF(EVENT):
    class ACTION(Enum):
        KICKOFF_WHISTLE = "KICKOFF_WHISTLE"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        (
            qualifiers,
            receive_timestamp,
            receiver_coordinates,
            receiver_player,
            result,
        ) = create_pass_props(self, generic_event_kwargs)

        qualifiers.append(SetPieceQualifier(value=SetPieceType.KICK_OFF))

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


class THROW_IN(EVENT):
    class ACTION(Enum):
        THROW_IN = "THROW_IN"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        (
            qualifiers,
            receive_timestamp,
            receiver_coordinates,
            receiver_player,
            result,
        ) = create_pass_props(self, generic_event_kwargs)

        qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


class FREE_KICK(EVENT):
    class ACTION(Enum):
        FREE_KICK = "FREE_KICK"
        DIRECT_FREE_KICK = "DIRECT_FREE_KICK"

    class RESULT(Enum):
        FAIL = "FAIL"
        SUCCESS = "SUCCESS"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        if self.raw_event["pass"]:
            (
                qualifiers,
                receive_timestamp,
                receiver_coordinates,
                receiver_player,
                result,
            ) = create_pass_props(self, generic_event_kwargs)
            # For passes, always use FREE_KICK regardless of action type
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))
            pass_event = event_factory.build_pass(
                result=result,
                receive_timestamp=receive_timestamp,
                receiver_coordinates=receiver_coordinates,
                receiver_player=receiver_player,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
            return [pass_event]
        elif self.raw_event["shot"]:
            shot_dict = self.raw_event["shot"]
            result = self.RESULT(self.raw_event["result"])
            shot_end_coordinates, shot_result = parse_shot_end_coordinates(
                shot_dict, result
            )
            body_part = BODYPART(self.raw_event["bodyPartExtended"])
            qualifiers = _get_body_part_qualifiers(body_part)
            # For shots, always use FREE_KICK regardless of action type
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))

            shot_event = event_factory.build_shot(
                result=shot_result,
                result_coordinates=shot_end_coordinates,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
            return [shot_event]
        else:
            raise DeserializationError(
                "Free kick event must have either a pass or a shot."
            )


class GOAL_KICK(EVENT):
    class ACTION(Enum):
        GOAL_KICK = "GOAL_KICK"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        (
            qualifiers,
            receive_timestamp,
            receiver_coordinates,
            receiver_player,
            result,
        ) = create_pass_props(self, generic_event_kwargs)

        qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


class CORNER(EVENT):
    class ACTION(Enum):
        CORNER = "CORNER"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        (
            qualifiers,
            receive_timestamp,
            receiver_coordinates,
            receiver_player,
            result,
        ) = create_pass_props(self, generic_event_kwargs)

        qualifiers.append(SetPieceQualifier(value=SetPieceType.CORNER_KICK))

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


class GK_CATCH(EVENT):
    class ACTION(Enum):
        CATCH = "CATCH"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])
        qualifiers = _get_body_part_qualifiers(body_part)
        qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.CLAIM)
        )

        gk_event = event_factory.build_goalkeeper_event(
            qualifiers=qualifiers,
            result=None,
            **generic_event_kwargs,
        )

        return [gk_event]


class GK_SAVE(EVENT):
    class ACTION(Enum):
        SAVE = "SAVE"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])
        qualifiers = _get_body_part_qualifiers(body_part)
        qualifiers.append(GoalkeeperQualifier(value=GoalkeeperActionType.SAVE))

        gk_event = event_factory.build_goalkeeper_event(
            qualifiers=qualifiers,
            result=None,
            **generic_event_kwargs,
        )

        return [gk_event]


class OUT(EVENT):
    class ACTION(Enum):
        BALL_OUT_OF_GOAL_LINE = "BALL_OUT_OF_GOAL_LINE"
        BALL_OUT_OF_SIDE_LINE = "BALL_OUT_OF_SIDE_LINE"
        BALL_OUT_OF_UNKNOWN = "BALL_OUT_OF_UNKNOWN"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        generic_event_kwargs["ball_state"] = BallState.DEAD

        ball_out_event = event_factory.build_ball_out(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [ball_out_event]


class FOUL(EVENT):
    class ACTION(Enum):
        FOUL = "FOUL"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        foul_event = event_factory.build_foul_committed(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [foul_event]


class YELLOW_CARD(EVENT):
    class ACTION(Enum):
        YELLOW_CARD = "YELLOW_CARD"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        card_event = event_factory.build_card(
            result=None,
            qualifiers=None,
            card_type=CardType.FIRST_YELLOW,
            **generic_event_kwargs,
        )
        return [card_event]


class SECOND_YELLOW_CARD(EVENT):
    class ACTION(Enum):
        SECOND_YELLOW_CARD = "SECOND_YELLOW_CARD"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        card_event = event_factory.build_card(
            result=None,
            qualifiers=None,
            card_type=CardType.SECOND_YELLOW,
            **generic_event_kwargs,
        )
        return [card_event]


class RED_CARD(EVENT):
    class ACTION(Enum):
        RED_CARD = "RED_CARD"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        card_event = event_factory.build_card(
            result=None,
            qualifiers=None,
            card_type=CardType.RED,
            **generic_event_kwargs,
        )
        return [card_event]


class OWN_GOAL(EVENT):
    class ACTION(Enum):
        OWN_GOAL = "OWN_GOAL"

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        **generic_event_kwargs,
    ) -> List[Event]:
        body_part = BODYPART(self.raw_event["bodyPartExtended"])
        qualifiers = _get_body_part_qualifiers(body_part)

        own_goal_event = event_factory.build_shot(
            result=ShotResult.OWN_GOAL,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [own_goal_event]


def create_pass_props(
    event: Union[PASS, KICK_OFF, THROW_IN, FREE_KICK, GOAL_KICK, CORNER],
    generic_event_kwargs,
):
    team = generic_event_kwargs["team"]
    pass_dict = event.raw_event["pass"]
    result = (
        PassResult.COMPLETE
        if event.raw_event["result"] == "SUCCESS"
        else PassResult.INCOMPLETE
    )
    receiver_info = pass_dict["receiver"]
    if receiver_info and receiver_info["type"] == "TEAMMATE":
        receiver_player = team.get_player_by_id(receiver_info["playerId"])
    else:
        receiver_player = None
    end_coordinates_info = event.raw_event["end"]
    if end_coordinates_info:
        receiver_coordinates = parse_coordinates(
            end_coordinates_info["adjCoordinates"]
        )
    else:
        receiver_coordinates = None
    duration = (
        event.raw_event["duration"] if event.raw_event["duration"] else 0
    )
    receive_timestamp = generic_event_kwargs["timestamp"] + timedelta(
        seconds=duration
    )
    body_part = BODYPART(event.raw_event["bodyPartExtended"])
    if event.raw_event["action"]:
        action = event.ACTION(event.raw_event["action"])
    else:
        action = None
    qualifiers = _get_pass_qualifiers(
        action, body_part
    ) + _get_body_part_qualifiers(body_part)

    return (
        qualifiers,
        receive_timestamp,
        receiver_coordinates,
        receiver_player,
        result,
    )


def _get_body_part_qualifiers(
    body_part: BODYPART,
) -> List[BodyPartQualifier]:
    impect_to_kloppy_body_part_mapping = {
        BODYPART.FOOT_LEFT: BodyPart.LEFT_FOOT,
        BODYPART.FOOT_RIGHT: BodyPart.RIGHT_FOOT,
        BODYPART.FOOT: BodyPart.RIGHT_FOOT,
        BODYPART.HEAD: BodyPart.HEAD,
        BODYPART.BODY: BodyPart.OTHER,
        BODYPART.HAND: BodyPart.KEEPER_ARM,
    }

    return [
        BodyPartQualifier(value=impect_to_kloppy_body_part_mapping[body_part])
    ]


def _get_pass_qualifiers(action, body_part) -> List[PassQualifier]:
    action_qualifier_mapping = {
        PASS.ACTION.LOW_CROSS: [PassType.CROSS],
        PASS.ACTION.HIGH_CROSS: [PassType.CROSS, PassType.HIGH_PASS],
        PASS.ACTION.SHORT_AERIAL_PASS: [PassType.CHIPPED_PASS],
        PASS.ACTION.CHIPPED_PASS: [PassType.CHIPPED_PASS],
    }
    body_part_qualifier_mapping = {
        BODYPART.HEAD: [PassType.HEAD_PASS],
        BODYPART.HAND: [PassType.HAND_PASS],
    }

    action_qualifier_values = action_qualifier_mapping.get(action, [])
    body_part_qualifier_value = body_part_qualifier_mapping.get(body_part, [])
    qualifier_values = action_qualifier_values + body_part_qualifier_value

    qualifiers = [PassQualifier(value=value) for value in qualifier_values]

    return qualifiers


def create_impect_events(
    raw_events: List[Dict],
) -> Dict[str, Union[EVENT, Dict]]:
    impect_events = {}
    for raw_event in raw_events:
        impect_events[raw_event["id"]] = event_decoder(raw_event)

    return impect_events


def event_decoder(raw_event: Dict) -> Union[EVENT, Dict]:
    type_to_event = {
        EVENT_TYPE.PASS: PASS,
        EVENT_TYPE.DRIBBLE: DRIBBLE,
        EVENT_TYPE.SHOT: SHOT,
        EVENT_TYPE.LOOSE_BALL_REGAIN: LOOSE_BALL_REGAIN,
        EVENT_TYPE.INTERCEPTION: INTERCEPTION,
        EVENT_TYPE.CLEARANCE: CLEARANCE,
        EVENT_TYPE.GROUND_DUEL: GROUND_DUEL,
        EVENT_TYPE.KICK_OFF: KICK_OFF,
        EVENT_TYPE.THROW_IN: THROW_IN,
        EVENT_TYPE.FREE_KICK: FREE_KICK,
        EVENT_TYPE.GOAL_KICK: GOAL_KICK,
        EVENT_TYPE.CORNER: CORNER,
        EVENT_TYPE.GK_CATCH: GK_CATCH,
        EVENT_TYPE.GK_SAVE: GK_SAVE,
        EVENT_TYPE.OUT: OUT,
        EVENT_TYPE.FOUL: FOUL,
        EVENT_TYPE.YELLOW_CARD: YELLOW_CARD,
        EVENT_TYPE.SECOND_YELLOW_CARD: SECOND_YELLOW_CARD,
        EVENT_TYPE.RED_CARD: RED_CARD,
        EVENT_TYPE.OWN_GOAL: OWN_GOAL,
    }
    event_type = EVENT_TYPE(raw_event["actionType"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
