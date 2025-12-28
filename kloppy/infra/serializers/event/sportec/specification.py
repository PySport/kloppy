from enum import Enum, EnumMeta
from typing import Optional, Union

from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DuelQualifier,
    DuelResult,
    DuelType,
    Event,
    EventFactory,
    ExpectedGoals,
    PassQualifier,
    PassResult,
    PassType,
    Point,
    Qualifier,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
    Team,
)
from kloppy.exceptions import DeserializationError

from .helpers import get_period_by_timestamp, get_team_by_id, parse_datetime


class TypesEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        if isinstance(value, dict):
            if value["id"] not in cls._value2member_map_:
                raise DeserializationError(
                    "Unknown Sportec {}: {}/{}".format(
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
                "Unknown Sportec {}: {}".format(
                    (
                        cls.__qualname__.replace("_", " ")
                        .replace(".", " ")
                        .title()
                    ),
                    value,
                )
            )
        return super().__call__(value, *args, **kw)


class PERIOD(Enum, metaclass=TypesEnumMeta):
    """The list of period names used in Sportec data."""

    FIRST_HALF = "firstHalf"
    SECOND_HALF = "secondHalf"
    # TODO: handle extra time periods

    @property
    def id(self) -> int:
        period_to_id = {
            PERIOD.FIRST_HALF: 1,
            PERIOD.SECOND_HALF: 2,
        }
        return period_to_id[self]


class SET_PIECE_TYPE(Enum, metaclass=TypesEnumMeta):
    KICK_OFF = "KickOff"
    FREE_KICK = "FreeKick"
    CORNER_KICK = "CornerKick"
    THROW_IN = "ThrowIn"
    GOAL_KICK = "GoalKick"
    PENALTY = "Penalty"


class CARD_TYPE(Enum, metaclass=TypesEnumMeta):
    FIRST_YELLOW = "yellow"
    SECOND_YELLOW = "yellowRed"
    RED = "red"


class EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of event types that compose all of Sportec data."""

    FINAL_WHISTLE = "FinalWhistle"
    SHOT = "ShotAtGoal"
    PLAY = "Play"
    BALL_CLAIMING = "BallClaiming"
    SUBSTITUTION = "Substitution"
    CAUTION = "Caution"
    FOUL = "Foul"
    TACKLING_GAME = "TacklingGame"
    OTHER = "OtherBallAction"
    DELETE = "Delete"
    FAIR_PLAY = "FairPlay"
    OFFSIDE = "Offside"
    SPECTACULAR_PLAY = "SpectacularPlay"
    PENALTY_NOT_AWARDED = "PenaltyNotAwarded"
    RUN = "Run"
    POSSESSION_LOSS_BEFORE_GOAL = "PossessionLossBeforeGoal"
    NUTMEG = "Nutmeg"
    REFEREE_BALL = "RefereeBall"
    BALL_DEFLECTION = "BallDeflection"
    CHANCE_WITHOUT_SHOT = "ChanceWithoutShot"
    GOAL_DISALLOWED = "GoalDisallowed"
    OWN_GOAL = "OwnGoal"
    VIDEO_ASSISTANT_ACTION = "VideoAssistantAction"


class EVENT:
    """Base class for Sportec events.

    This class is used to deserialize Sportec events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event
    """

    def __init__(self, raw_event: dict):
        self.raw_event = raw_event

    def set_refs(self, periods, teams, prev_events=None, next_events=None):
        event_type = self.raw_event["EventType"]
        event_attr = self.raw_event["extra"][event_type]
        self.period = get_period_by_timestamp(
            parse_datetime(self.raw_event["EventTime"]), periods
        )
        self.team = (
            get_team_by_id(event_attr["Team"], teams)
            if "Team" in event_attr
            else None
        )
        self.player = (
            self.team.get_player_by_id(event_attr["Player"])
            if "Player" in event_attr and self.team
            else None
        )
        self._teams = teams
        self.prev_events = prev_events
        self.next_events = next_events
        return self

    def deserialize(self, event_factory: EventFactory) -> list[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()

        base_events = self._create_events(event_factory, **generic_event_kwargs)
        return base_events

    def _parse_generic_kwargs(self) -> dict:
        return {
            "period": self.period,
            "timestamp": (
                parse_datetime(self.raw_event["EventTime"])
                - self.period.start_timestamp
            ),
            "ball_owning_team": None,
            "ball_state": BallState.ALIVE,
            "event_id": self.raw_event["EventId"],
            "team": self.team,
            "player": self.player,
            "coordinates": (
                Point(
                    x=float(self.raw_event["X-Position"]),
                    y=float(self.raw_event["Y-Position"]),
                )
                if "X-Position" in self.raw_event
                and "Y-Position" in self.raw_event
                else None
            ),
            "related_event_ids": [],
            "raw_event": self.raw_event,
            "statistics": [],
        }

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        name = "GenericEvent"
        if self.raw_event.get("EventType") is not None:
            name = self.raw_event["EventType"]
        if self.raw_event.get("SubEventType") is not None:
            name = self.raw_event["SubEventType"]

        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=name,
            **generic_event_kwargs,
        )
        return [generic_event]


class SHOT(EVENT):
    """Sportec ShotAtGoal event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        SHOT_WIDE = "ShotWide"
        SHOT_SAVED = "SavedShot"
        SHOT_BLOCKED = "BlockedShot"
        SHOT_WOODWORK = "ShotWoodWork"
        SHOT_OTHER = "OtherShot"
        SHOT_GOAL = "SuccessfulShot"

    class BODYPART(Enum, metaclass=TypesEnumMeta):
        LEFT_LEG = "leftLeg"
        RIGHT_LEG = "rightLeg"
        HEAD = "head"

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        shot_dict = self.raw_event["extra"]["ShotAtGoal"]
        outcome_id = SHOT.TYPE(self.raw_event["SubEventType"])

        outcome_mapping = {
            SHOT.TYPE.SHOT_WIDE: ShotResult.OFF_TARGET,
            SHOT.TYPE.SHOT_SAVED: ShotResult.SAVED,
            SHOT.TYPE.SHOT_BLOCKED: ShotResult.BLOCKED,
            SHOT.TYPE.SHOT_WOODWORK: ShotResult.POST,
            SHOT.TYPE.SHOT_OTHER: None,
            SHOT.TYPE.SHOT_GOAL: ShotResult.GOAL,
        }

        result = outcome_mapping.get(outcome_id)

        qualifiers = _get_set_piece_qualifiers(
            self.raw_event
        ) + _get_body_part_qualifiers(EVENT_TYPE.SHOT, shot_dict)

        for statistic_cls, prop_name in {
            ExpectedGoals: "xG",
        }.items():
            value = shot_dict.get(prop_name, None)
            if value is not None:
                generic_event_kwargs["statistics"].append(
                    statistic_cls(value=float(value))
                )

        shot_event = event_factory.build_shot(
            result=result,
            qualifiers=qualifiers,
            result_coordinates=None,
            **generic_event_kwargs,
        )

        return [shot_event]


class PLAY(EVENT):
    """Sportec Play event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        PASS = "Pass"
        CROSS = "Cross"

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        SUCCESSFUL_COMPLETE = "successfullyCompleted"
        SUCCESSFUL = "successful"
        UNSUCCSESSFUL = "unsuccessful"

    class HEIGHT(Enum, metaclass=TypesEnumMeta):
        GROUND = "flat"
        HIGH = "high"

    class DIRECTION(Enum, metaclass=TypesEnumMeta):
        DIAGONAL_BALL = "diagonalBall"
        THROUGH_BALL = "throughBall"
        SQUARE_BALL = "squarePass"
        BACK_PASS = "backPass"

    class DISTANCE(Enum, metaclass=TypesEnumMeta):
        LONG = "long"
        MEDIUM = "medium"
        SHORT = "short"

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        pass_dict = self.raw_event["extra"]["Play"]

        # Parse result
        result = None
        if "Evaluation" in pass_dict:
            outcome_name = pass_dict["Evaluation"]
            outcome_mapping = {
                PLAY.OUTCOME.SUCCESSFUL_COMPLETE: PassResult.COMPLETE,
                PLAY.OUTCOME.SUCCESSFUL: PassResult.COMPLETE,  # TODO: infer more specific outcome?
                PLAY.OUTCOME.UNSUCCSESSFUL: PassResult.INCOMPLETE,
            }
            result = outcome_mapping.get(PLAY.OUTCOME(outcome_name))
        else:
            result = None

        if result == PassResult.INCOMPLETE and _before_ball_out_restart(self):
            result = PassResult.OUT
        if result == PassResult.INCOMPLETE and _before_offside_event(self):
            result = PassResult.OFFSIDE

        # Parse recipient
        if "Recipient" in pass_dict:
            team = generic_event_kwargs["team"]
            receiver_player = team.get_player_by_id(pass_dict["Recipient"])
        else:
            receiver_player = None

        # Parse qualifiers
        add_qualifier = lambda v: qualifiers.append(PassQualifier(value=v))

        subevent_type = self.raw_event["SubEventType"]
        subevent_attr = self.raw_event["extra"].get(subevent_type, {})

        qualifiers: list[Qualifier] = _get_set_piece_qualifiers(self.raw_event)
        if (
            subevent_type is not None
            and PLAY.TYPE(subevent_type) == PLAY.TYPE.CROSS
        ):
            add_qualifier(PassType.CROSS)
        if (
            "Direction" in subevent_attr
            and PLAY.DIRECTION(subevent_attr["Direction"])
            == PLAY.DIRECTION.THROUGH_BALL
        ):
            add_qualifier(PassType.THROUGH_BALL)
        if (
            "Direction" in subevent_attr
            and PLAY.DIRECTION(subevent_attr["Direction"])
            == PLAY.DIRECTION.DIAGONAL_BALL
        ):
            add_qualifier(PassType.SWITCH_OF_PLAY)
        if (
            "Height" in pass_dict
            and PLAY.HEIGHT(pass_dict["Height"]) == PLAY.HEIGHT.HIGH
        ):
            add_qualifier(PassType.HIGH_PASS)
        if (
            "Distance" in pass_dict
            and PLAY.DISTANCE(pass_dict["Distance"]) == PLAY.DISTANCE.LONG
        ):
            add_qualifier(PassType.LONG_BALL)

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=None,
            receiver_coordinates=None,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        is_restart = any(
            qualifier.value
            in {
                SetPieceType.THROW_IN,
                SetPieceType.GOAL_KICK,
                SetPieceType.CORNER_KICK,
            }
            for qualifier in qualifiers
            if isinstance(qualifier, SetPieceQualifier)
        )
        if is_restart:
            set_piece_type = self.raw_event["SetPieceType"]
            set_piece_attr = self.raw_event["extra"][set_piece_type]

            if "DecisionTimestamp" in set_piece_attr:
                decision_ts = parse_datetime(
                    set_piece_attr["DecisionTimestamp"]
                )
                out_event = event_factory.build_ball_out(
                    period=self.period,
                    timestamp=(decision_ts - self.period.start_timestamp),
                    ball_owning_team=None,
                    ball_state=BallState.DEAD,
                    event_id=f"{self.raw_event['EventId']}-out",
                    team=None,
                    player=None,
                    coordinates=None,
                    raw_event={},
                    result=None,
                    qualifiers=None,
                )
                return [out_event, pass_event]

        return [pass_event]


class BALL_CLAIMING(EVENT):
    """Sportec BallClaiming event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        BALL_CLAIMED = "BallClaimed"
        BALL_HELD = "BallHeld"
        INTERCEPTED_BALL = "InterceptedBall"

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        recovery_dict = self.raw_event["extra"]["BallClaiming"]
        recovery_type = BALL_CLAIMING.TYPE(recovery_dict["Type"])
        if recovery_type == BALL_CLAIMING.TYPE.BALL_CLAIMED:
            recovery_event = event_factory.build_recovery(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        elif recovery_type == BALL_CLAIMING.TYPE.INTERCEPTED_BALL:
            recovery_event = event_factory.build_interception(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        elif recovery_type == BALL_CLAIMING.TYPE.BALL_HELD:
            # TODO: What is a BallClaiming>BallHeld event?
            recovery_event = event_factory.build_generic(
                event_name="BallClaiming:BallHeld",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        else:
            raise DeserializationError(
                f"Unknown recovery type: {recovery_type}"
            )
        return [recovery_event]


class CAUTION(EVENT):
    """Sportec Caution event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        card_type = _get_card_type(self.raw_event["extra"]["Caution"])
        if card_type:
            card_event = event_factory.build_card(
                result=None,
                qualifiers=None,
                card_type=card_type,
                **generic_event_kwargs,
            )
            return [card_event]

        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [generic_event]


class FOUL(EVENT):
    """Sportec Foul event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        foul_dict = self.raw_event["extra"]["Foul"]
        # Parse team and player
        team = (
            get_team_by_id(foul_dict["TeamFouler"], self._teams)
            if "TeamFouler" in foul_dict
            else None
        )
        player = (
            team.get_player_by_id(foul_dict["Fouler"])
            if "Fouler" in foul_dict and team
            else None
        )
        generic_event_kwargs = {
            **generic_event_kwargs,
            "player": player,
            "team": team,
            "ball_state": BallState.DEAD,
        }

        # Parse card qualifier
        qualifiers = None
        card_event = _before_card_event(self)
        if card_event:
            card_type = _get_card_type(card_event.raw_event["extra"]["Caution"])
            if card_type:
                qualifiers = (
                    [CardQualifier(value=card_type)] if card_type else []
                )

        foul_committed_event = event_factory.build_foul_committed(
            result=None,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )
        return [foul_committed_event]


class OTHER_BALL_ACTION(EVENT):
    """Sportec OtherBallAction event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        event_attr = self.raw_event["extra"]["OtherBallAction"]
        if event_attr.get("DefensiveClearance", False):
            return [
                event_factory.build_clearance(
                    result=None,
                    qualifiers=None,
                    **generic_event_kwargs,
                )
            ]
        return [
            event_factory.build_generic(
                event_name="OtherBallAction",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class SUBSTITUTION(EVENT):
    """Sportec Substitution event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        sub_dict = self.raw_event["extra"]["Substitution"]
        generic_event_kwargs["player"] = self.team.get_player_by_id(
            sub_dict["PlayerOut"]
        )

        substitution_event = event_factory.build_substitution(
            replacement_player=self.team.get_player_by_id(sub_dict["PlayerIn"]),
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [substitution_event]


class TACKLING_GAME(EVENT):
    """Sportec TacklingGame event."""

    class WINNER_RESULT(Enum, metaclass=TypesEnumMeta):
        BALL_CONTROL_RETAINED = "ballControlRetained"
        BALL_CONTACT_SUCCEEDED = "ballcontactSucceeded"
        DRIBBLED_AROUND = "dribbledAround"
        FOULED = "fouled"
        LAYOFF = "layoff"
        BALL_CLAIMED = "ballClaimed"

    class ROLE(Enum, metaclass=TypesEnumMeta):
        # Recorded when DUEL.TYPE is DUEL_TACKLE
        WON = "withBallControl"
        LOST_IN_PLAY = "withoutBallControl"

    class DRIBBLING_TYPE(Enum, metaclass=TypesEnumMeta):
        AT_THE_FOOT = "atTheFoot"
        OVERRUN = "overrun"

    class DRIBBLING_EVALUATION(Enum, metaclass=TypesEnumMeta):
        SUCCESSFUL = "successful"
        UNSUCCESSFUL = "unsuccessful"

    class DRIBBLING_SIDE(Enum, metaclass=TypesEnumMeta):
        LEFT = "left"
        RIGHT = "right"

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        duel_dict = self.raw_event["extra"]["TacklingGame"]

        def q_tackle(source: str) -> list[Qualifier]:
            dt = DuelType.AERIAL if source == "air" else DuelType.GROUND
            return [
                DuelQualifier(value=dt),
                DuelQualifier(value=DuelType.TACKLE),
            ]

        def q_duel(source: str) -> list[Qualifier]:
            dt = DuelType.AERIAL if source == "air" else DuelType.GROUND
            return [DuelQualifier(value=dt)]

        if (
            duel_dict.get("DribbleEvaluation")
            == TACKLING_GAME.DRIBBLING_EVALUATION.SUCCESSFUL.value
            and duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.DRIBBLED_AROUND.value
        ):
            return [
                event_factory.build_take_on(
                    result=TakeOnResult.COMPLETE,
                    qualifiers=[],
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_duel(
                    result=DuelResult.LOST,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("DribbleEvaluation")
            == TACKLING_GAME.DRIBBLING_EVALUATION.UNSUCCESSFUL.value
            and duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.BALL_CLAIMED.value
        ):
            return [
                event_factory.build_take_on(
                    result=TakeOnResult.INCOMPLETE,
                    qualifiers=[],
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_duel(
                    result=DuelResult.WON,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("DribbleEvaluation")
            == TACKLING_GAME.DRIBBLING_EVALUATION.SUCCESSFUL.value
            and duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.FOULED.value
        ):
            return [
                event_factory.build_take_on(
                    result=TakeOnResult.COMPLETE,
                    qualifiers=[],
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                # the foul is also provided as a separate event
            ]

        elif (
            duel_dict.get("DribbleEvaluation")
            == TACKLING_GAME.DRIBBLING_EVALUATION.UNSUCCESSFUL.value
            and duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.FOULED.value
        ):
            return [
                event_factory.build_take_on(
                    result=TakeOnResult.COMPLETE,  # FIXME: Maybe we do not have a good result type for this one
                    qualifiers=[],
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                # the foul is also provided as a separate event
            ]

        elif (
            duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.BALL_CLAIMED.value
        ):
            return [
                event_factory.build_duel(
                    result=DuelResult.WON,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_duel(
                    result=DuelResult.LOST,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.BALL_CONTROL_RETAINED.value
        ):
            return [
                event_factory.build_duel(
                    result=DuelResult.WON,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_duel(
                    result=DuelResult.LOST,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.BALL_CONTACT_SUCCEEDED.value
        ):
            return [
                event_factory.build_duel(
                    result=DuelResult.NEUTRAL,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_duel(
                    result=DuelResult.NEUTRAL,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.LAYOFF.value
        ):
            return [
                event_factory.build_generic(
                    event_name="TacklingGame:Layoff",
                    result=None,
                    qualifiers=[],
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                event_factory.build_generic(
                    event_name="TacklingGame:Layoff",
                    result=None,
                    qualifiers=[],
                    **_parse_loser(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
            ]

        elif (
            duel_dict.get("WinnerResult")
            == TACKLING_GAME.WINNER_RESULT.FOULED.value
        ):
            return [
                event_factory.build_duel(
                    result=DuelResult.WON,
                    qualifiers=q_duel(duel_dict.get("Type", "ground")),
                    **_parse_winner(
                        generic_event_kwargs, duel_dict, self._teams
                    ),
                ),
                # the foul is also provided as a separate event
            ]

        return [
            event_factory.build_generic(
                event_name="TacklingGame:Unknown",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class DELETE(EVENT):
    """Sportec Delete event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return []


class OWN_GOAL(EVENT):
    """Sportec OwnGoal event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        shot_event = event_factory.build_shot(
            result=ShotResult.OWN_GOAL,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [shot_event]


def _get_body_part_qualifiers(
    event_type: EVENT_TYPE,
    event_dict: dict,
) -> list[BodyPartQualifier]:
    sportec_to_kloppy_body_part_mapping = {
        SHOT.BODYPART.LEFT_LEG: BodyPart.LEFT_FOOT,
        SHOT.BODYPART.RIGHT_LEG: BodyPart.RIGHT_FOOT,
        SHOT.BODYPART.HEAD: BodyPart.HEAD,
    }

    body_part_name = None
    if event_type == EVENT_TYPE.SHOT:
        if "TypeOfShot" in event_dict:
            body_part_name = SHOT.BODYPART(event_dict["TypeOfShot"])
    else:
        raise RuntimeError(
            f"Sportec does not annotate body parts for events of type {event_type}"
        )
    if body_part_name in sportec_to_kloppy_body_part_mapping:
        body_part = sportec_to_kloppy_body_part_mapping[body_part_name]
        return [BodyPartQualifier(value=body_part)]

    return []


def _get_card_type(event_dict: dict) -> Optional[CardType]:
    sportec_to_kloppy_card_mappings = {
        CARD_TYPE.FIRST_YELLOW: CardType.FIRST_YELLOW,
        CARD_TYPE.SECOND_YELLOW: CardType.SECOND_YELLOW,
        CARD_TYPE.RED: CardType.RED,
    }
    if "CardColor" in event_dict:
        card_name = CARD_TYPE(event_dict["CardColor"])
        return sportec_to_kloppy_card_mappings[card_name]
    return None


def _get_set_piece_qualifiers(event_dict: dict) -> list[SetPieceQualifier]:
    mapping = {
        SET_PIECE_TYPE.THROW_IN: SetPieceType.THROW_IN,
        SET_PIECE_TYPE.GOAL_KICK: SetPieceType.GOAL_KICK,
        SET_PIECE_TYPE.PENALTY: SetPieceType.PENALTY,
        SET_PIECE_TYPE.CORNER_KICK: SetPieceType.CORNER_KICK,
        SET_PIECE_TYPE.KICK_OFF: SetPieceType.KICK_OFF,
        SET_PIECE_TYPE.FREE_KICK: SetPieceType.FREE_KICK,
    }
    if event_dict.get("SetPieceType") is not None:
        type_name = SET_PIECE_TYPE(event_dict["SetPieceType"])
        if type_name in mapping:
            set_piece_type = mapping[type_name]
            return [SetPieceQualifier(value=set_piece_type)]
    return []


def _parse_duel_actor(
    base_kwargs: dict, attributes: dict, teams: list[Team], role_key: str
) -> dict:
    team_id = attributes.get(f"{role_key}Team")
    team = get_team_by_id(team_id, teams)
    player = team.get_player_by_id(attributes.get(role_key))
    base_kwargs["event_id"] = base_kwargs["event_id"] + f"-{role_key}"
    base_kwargs["team"] = team
    base_kwargs["player"] = player
    return base_kwargs


def _parse_winner(base_kwargs, attrs, teams):
    return _parse_duel_actor(dict(base_kwargs), attrs, teams, "Winner")


def _parse_loser(base_kwargs, attrs, teams):
    return _parse_duel_actor(dict(base_kwargs), attrs, teams, "Loser")


def _before_ball_out_restart(event: Event) -> Optional[Event]:
    """Check if the event is before another event that brings the ball back into play."""
    for e in event.next_events or []:
        event_type = e.raw_event["EventType"]
        set_piece_type = e.raw_event["SetPieceType"]
        if EVENT_TYPE(event_type) in {
            # skip these event types
            EVENT_TYPE.DELETE,
            EVENT_TYPE.PENALTY_NOT_AWARDED,
            EVENT_TYPE.RUN,
            EVENT_TYPE.POSSESSION_LOSS_BEFORE_GOAL,
            EVENT_TYPE.VIDEO_ASSISTANT_ACTION,
        }:
            continue
        elif set_piece_type is not None and SET_PIECE_TYPE(set_piece_type) in {
            SET_PIECE_TYPE.CORNER_KICK,
            SET_PIECE_TYPE.THROW_IN,
            SET_PIECE_TYPE.GOAL_KICK,
        }:
            return e
        else:
            return None
    return None


def _before_card_event(event: Event) -> Optional[Event]:
    """Check if the event is before a card event."""
    for e in event.next_events or []:
        event_type = EVENT_TYPE(e.raw_event["EventType"])
        if event_type in {
            # skip these event types
            EVENT_TYPE.DELETE,
            EVENT_TYPE.PENALTY_NOT_AWARDED,
            EVENT_TYPE.RUN,
            EVENT_TYPE.POSSESSION_LOSS_BEFORE_GOAL,
            EVENT_TYPE.VIDEO_ASSISTANT_ACTION,
        }:
            continue
        elif event_type == EVENT_TYPE.CAUTION:
            return e
        else:
            return None
    return None


def _before_offside_event(event: Event) -> Optional[Event]:
    """Check if the event is before an offside event."""
    for e in event.next_events or []:
        event_type = EVENT_TYPE(e.raw_event["EventType"])
        if event_type in {
            # skip these event types
            EVENT_TYPE.DELETE,
            EVENT_TYPE.PENALTY_NOT_AWARDED,
            EVENT_TYPE.RUN,
            EVENT_TYPE.POSSESSION_LOSS_BEFORE_GOAL,
            EVENT_TYPE.VIDEO_ASSISTANT_ACTION,
        }:
            continue
        elif event_type == EVENT_TYPE.OFFSIDE:
            return e
        else:
            return None
    return None


def event_decoder(raw_event: dict) -> Union[EVENT, dict]:
    type_to_event = {
        EVENT_TYPE.SHOT: SHOT,
        EVENT_TYPE.PLAY: PLAY,
        EVENT_TYPE.BALL_CLAIMING: BALL_CLAIMING,
        EVENT_TYPE.CAUTION: CAUTION,
        EVENT_TYPE.FOUL: FOUL,
        EVENT_TYPE.OTHER: OTHER_BALL_ACTION,
        EVENT_TYPE.SUBSTITUTION: SUBSTITUTION,
        EVENT_TYPE.TACKLING_GAME: TACKLING_GAME,
        EVENT_TYPE.DELETE: DELETE,
        EVENT_TYPE.OWN_GOAL: OWN_GOAL,
    }
    event_type = EVENT_TYPE(raw_event["EventType"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
