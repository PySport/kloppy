from datetime import timedelta
from enum import Enum, EnumMeta
from typing import List, Dict, NamedTuple, Union

from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    CarryResult,
    CounterAttackQualifier,
    DuelQualifier,
    DuelResult,
    DuelType,
    Event,
    EventFactory,
    ExpectedGoals,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    InterceptionResult,
    PassQualifier,
    PassResult,
    PassType,
    PositionType,
    PostShotExpectedGoals,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
)
from kloppy.domain.models.event import (
    CardEvent,
    FoulCommittedEvent,
    UnderPressureQualifier,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.pff.helpers import (
    collect_qualifiers,
    get_period_by_id,
    get_team_by_id,
    parse_coordinates,
)


position_types_mapping: dict[str, PositionType] = {
    "GK": PositionType.Goalkeeper,  # Provider: Goalkeeper
    "RB": PositionType.RightBack,  # Provider: Right Back
    "RCB": PositionType.RightCenterBack,  # Provider: Right Center Back
    "CB": PositionType.CenterBack,  # Provider: Center Back
    "MCB": PositionType.CenterBack,  # Provider: Mid Center Back
    "LCB": PositionType.LeftCenterBack,  # Provider: Left Center Back
    "LB": PositionType.LeftBack,  # Provider: Left Back
    "LWB": PositionType.LeftWingBack,  # Provider: Left Wing Back
    "RWB": PositionType.RightWingBack,  # Provider: Right Wing Back
    "D": PositionType.Defender,  # Provider: Defender
    "M": PositionType.Midfielder,  # Provider: Midfielder
    "DM": PositionType.DefensiveMidfield,  # Provider: Defensive Midfield
    "RM": PositionType.RightMidfield,  # Provider: Right Midfield
    "CM": PositionType.CenterMidfield,  # Provider: Center Midfield
    "LM": PositionType.LeftMidfield,  # Provider: Left Midfield
    "RW": PositionType.RightWing,  # Provider: Right Wing
    "AM": PositionType.AttackingMidfield,  # Provider: Attacking Midfield
    "LW": PositionType.LeftWing,  # Provider: Left Wing
    "CF": PositionType.Striker,  # Provider: Center Forward (mapped to Striker)
    "F": PositionType.Attacker,  # Provider: Forward (mapped to Attacker)
}


class TypesEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        if isinstance(value, dict):
            if value["id"] not in cls._value2member_map_:
                raise DeserializationError(
                    "Unknown PFF {}: {}/{}".format(
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
                "Unknown PFF {}: {}".format(
                    (
                        cls.__qualname__.replace("_", " ")
                        .replace(".", " ")
                        .title()
                    ),
                    value,
                )
            )
        return super().__call__(value, *args, **kw)


class END_TYPE(Enum, metaclass=TypesEnumMeta):
    """ "The list of end of half types used in PFF data."""

    FIRST_HALF_END = "FIRST"
    SECOND_HALF_END = "SECOND"
    THIRD_HALF_END = "F"
    FOURTH_HALF_END = "S"
    GAME_END = "G"


class EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of game event types used in PFF data."""

    FIRST_HALF_KICKOFF = "FIRSTKICKOFF"
    SECOND_HALF_KICKOFF = "SECONDKICKOFF"
    THIRD_HALF_KICKOFF = "THIRDKICKOFF"
    FOURTH_HALF_KICKOFF = "FOURTHKICKOFF"
    GAME_CLOCK_OBSERVATION = "CLK"
    END_OF_HALF = "END"
    GROUND = "G"
    PLAYER_OFF = "OFF"
    PLAYER_ON = "ON"
    POSSESSION = "OTB"
    BALL_OUT_OF_PLAY = "OUT"
    PAUSE_OF_GAME_TIME = "PAU"
    SUB = "SUB"
    VIDEO = "VID"


class POSSESSION_EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of possession event types used in PFF data."""

    BALL_CARRY = "BC"
    CHALLENGE = "CH"
    CLEARANCE = "CL"
    CROSS = "CR"
    FOUL = "FO"
    PASS = "PA"
    REBOUND = "RE"
    SHOT = "SH"
    TOUCHES = "TC"
    EVT_START = "IT"


class PFF_BODYPART(Enum, metaclass=TypesEnumMeta):
    """The list of body parts used in PFF data."""

    BACK = "BA"
    BOTTOM = "BO"
    TWO_HAND_CATCH = "CA"
    CHEST = "CH"
    HEAD = "HE"
    LEFT_FOOT = "L"
    LEFT_ARM = "LA"
    LEFT_BACK_HEEL = "LB"
    LEFT_SHOULDER = "LC"
    LEFT_HAND = "LH"
    LEFT_KNEE = "LK"
    LEFT_SHIN = "LS"
    LEFT_THIGH = "LT"
    TWO_HAND_PALM = "PA"
    TWO_HAND_PUNCH = "PU"
    RIGHT_FOOT = "R"
    RIGHT_ARM = "RA"
    RIGHT_BACK_HEEL = "RB"
    RIGHT_SHOULDER = "RC"
    RIGHT_HAND = "RH"
    RIGHT_KNEE = "RK"
    RIGHT_SHIN = "RS"
    RIGHT_THIGH = "RT"
    TWO_HANDS = "TWOHANDS"
    VIDEO_MISSING = "VM"


class PFF_SET_PIECE(Enum, metaclass=TypesEnumMeta):
    """The list of set piece types used in PFF data."""

    CORNER = 'C'
    DROP_BALL = 'D'
    FREE_KICK = 'F'
    GOAL_KICK = 'G'
    KICK_OFF = 'K'
    PENALTY = 'P'
    THROW_IN = 'T'


class FOUL_TYPE(Enum, metaclass=TypesEnumMeta):
    ADVANTAGE = "A"
    INFRIGEMENT = "I"
    MISSED_INFRIGEMENT = "M"


class FOUL_OUTCOME(Enum, metaclass=TypesEnumMeta):
    FIRST_YELLOW = "Y"
    SECOND_YELLOW = "S"
    RED = "R"
    WARNING = "W"
    NO_FOUL = "F"
    NO_WARNING = "N"


class EVENT:
    """Base class for PFF events.

    This class is used to deserialize PFF events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event

    @property
    def game_event(self) -> Dict[str, Union[int, float, str, bool, None]]:
        return self.raw_event['gameEvents']

    @property
    def possession_event(self) -> Dict[str, Union[int, float, str, bool, None]]:
        return self.raw_event['possessionEvents']

    def set_refs(self, periods, teams, events):
        # temp: some PFF events do not have a 'teamId' assigned but we can get
        # the team using the player id. Until this is fixed in the PFF data,
        # both teams are being "carried over" in the event.
        self.teams = teams

        self.period = get_period_by_id(
            self.raw_event["gameEvents"]["period"], periods
        )

        self.team = get_team_by_id(
            self.raw_event["gameEvents"]["teamId"], teams
        )

        self.possession_team = get_team_by_id(
            self.raw_event["gameEvents"]["teamId"], teams
        )

        self.player = (
            self.team.get_player_by_id(
                self.raw_event["gameEvents"]["playerId"]
            )
            if self.team
            and self.raw_event["gameEvents"]["playerId"] is not None
            else None
        )

        self.related_events = [
            events[event_id]
            for event_id in events.keys()
            if event_id.split("_")[0] == str(self.raw_event["gameEventId"])
        ]

        return self

    def deserialize(self, event_factory: EventFactory) -> list[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()

        # create events
        base_events = self._create_events(
            event_factory, **generic_event_kwargs
        )

        foul_events = self._create_foul(event_factory, **generic_event_kwargs)

        # return events (note: order is important)
        return base_events + foul_events

    def _get_set_piece_qualifier(self) -> SetPieceQualifier | None:
        pff_set_piece_type = self.raw_event['gameEvents']['setpieceType']

        if pff_set_piece_type is None or pff_set_piece_type == 'O':
            return None

        pff_to_kloppy_set_piece = {
            PFF_SET_PIECE.GOAL_KICK: SetPieceType.GOAL_KICK,
            PFF_SET_PIECE.FREE_KICK: SetPieceType.FREE_KICK,
            PFF_SET_PIECE.THROW_IN: SetPieceType.THROW_IN,
            PFF_SET_PIECE.CORNER: SetPieceType.CORNER_KICK,
            PFF_SET_PIECE.PENALTY: SetPieceType.PENALTY,
            PFF_SET_PIECE.KICK_OFF: SetPieceType.KICK_OFF,
        }

        try:
            pff_set_piece = PFF_SET_PIECE(pff_set_piece_type)
            set_piece_type = pff_to_kloppy_set_piece[pff_set_piece]
            return SetPieceQualifier(value=set_piece_type)
        except KeyError:
            return None

    def _get_body_part_qualifier(self) -> BodyPartQualifier | None:
        """Get the body part qualifier from the PFF body part type."""

        pff_body_part_type = self.raw_event['possessionEvents']['bodyType']

        if pff_body_part_type is None:
            return None

        pff_to_kloppy_body_part = {
            PFF_BODYPART.HEAD: BodyPart.HEAD,

            PFF_BODYPART.LEFT_FOOT: BodyPart.LEFT_FOOT,
            PFF_BODYPART.LEFT_BACK_HEEL: BodyPart.LEFT_FOOT,
            PFF_BODYPART.LEFT_SHIN: BodyPart.LEFT_FOOT,
            PFF_BODYPART.LEFT_THIGH: BodyPart.LEFT_FOOT,
            PFF_BODYPART.LEFT_KNEE: BodyPart.LEFT_FOOT,

            PFF_BODYPART.RIGHT_FOOT: BodyPart.RIGHT_FOOT,
            PFF_BODYPART.RIGHT_BACK_HEEL: BodyPart.RIGHT_FOOT,
            PFF_BODYPART.RIGHT_SHIN: BodyPart.RIGHT_FOOT,
            PFF_BODYPART.RIGHT_THIGH: BodyPart.RIGHT_FOOT,
            PFF_BODYPART.RIGHT_KNEE: BodyPart.RIGHT_FOOT,

            PFF_BODYPART.LEFT_ARM: BodyPart.LEFT_HAND,
            PFF_BODYPART.LEFT_HAND: BodyPart.LEFT_HAND,
            PFF_BODYPART.LEFT_SHOULDER: BodyPart.LEFT_HAND,

            PFF_BODYPART.RIGHT_ARM: BodyPart.RIGHT_HAND,
            PFF_BODYPART.RIGHT_HAND: BodyPart.RIGHT_HAND,
            PFF_BODYPART.RIGHT_SHOULDER: BodyPart.RIGHT_HAND,

            PFF_BODYPART.TWO_HAND_PALM: BodyPart.BOTH_HANDS,
            PFF_BODYPART.TWO_HAND_CATCH: BodyPart.BOTH_HANDS,
            PFF_BODYPART.TWO_HAND_PUNCH: BodyPart.BOTH_HANDS,
            PFF_BODYPART.TWO_HANDS: BodyPart.BOTH_HANDS,

            PFF_BODYPART.BACK: BodyPart.OTHER,
            PFF_BODYPART.BOTTOM: BodyPart.OTHER,

            PFF_BODYPART.CHEST: BodyPart.CHEST,
        }

        try:
            pff_body_part = PFF_BODYPART(pff_body_part_type)
            body_part = pff_to_kloppy_body_part[pff_body_part]
            return BodyPartQualifier(value=body_part)
        except KeyError:
            return None

    def _parse_generic_kwargs(self) -> dict:
        return {
            "period": self.period,
            "timestamp": timedelta(seconds=self.raw_event["eventTime"]),
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.DEAD,
            "event_id": self.raw_event["gameEventId"],
            "team": self.team,
            "player": self.player,
            "coordinates": parse_coordinates(self.player, self.raw_event),
            "raw_event": self.raw_event,
        }

    def _create_foul(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[CardEvent | FoulCommittedEvent]:
        foul_type = self.raw_event["fouls"].get("foulType")

        if foul_type != FOUL_TYPE.INFRIGEMENT.value:
            return []

        card_map = {
            FOUL_OUTCOME.FIRST_YELLOW: CardType.FIRST_YELLOW,
            FOUL_OUTCOME.SECOND_YELLOW: CardType.SECOND_YELLOW,
            FOUL_OUTCOME.RED: CardType.RED,
        }

        committer_id = self.raw_event["fouls"]["finalCulpritPlayerId"]
        team = next(t for t in self.teams if t.get_player_by_id(committer_id))

        generic_event_kwargs["team"] = team
        generic_event_kwargs["player"] = team.get_player_by_id(committer_id)
        generic_event_kwargs["ball_state"] = BallState.DEAD

        foul_outcome = self.raw_event["fouls"]["finalFoulOutcomeType"]
        card_type = card_map.get(FOUL_OUTCOME(foul_outcome))
        card_qualifier = [CardQualifier(value=card_type)] if card_type else []

        foul = [
            event_factory.build_foul_committed(
                result=None,
                qualifiers=card_qualifier,
                **generic_event_kwargs,
            )
        ]

        if card_type:
            card = [
                event_factory.build_card(
                    result=None,
                    qualifiers=None,
                    card_type=card_type,
                    **generic_event_kwargs,
                )
            ]
        else:
            card = []

        return foul + card

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["gameEvents"]["gameEventType"],
            **generic_event_kwargs,
        )
        return [generic_event]


class SUBSTITUTION(EVENT):
    """PFF Substitution event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        # As of now, PFF Substitution events do not set teamId.
        # team = generic_event_kwargs['team']

        player_off_id = self.raw_event["gameEvents"]["playerOffId"]
        player_on_id = self.raw_event["gameEvents"]["playerOnId"]

        team = next(t for t in self.teams if t.get_player_by_id(player_off_id))

        player_off = team.get_player_by_id(player_off_id)
        player_on = team.get_player_by_id(player_on_id)

        generic_event_kwargs["team"] = team
        generic_event_kwargs["player"] = player_off

        return [
            event_factory.build_substitution(
                result=None,
                qualifiers=None,
                replacement_player=player_on,
                **generic_event_kwargs,
            )
        ]


class PLAYER_OFF(EVENT):
    """PFF Player Off event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_player_off(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class PLAYER_ON(EVENT):
    """PFF Player On event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_player_on(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class BALL_OUT(EVENT):
    """PFF OUT/Ball out of play event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class POSSESSION_EVENT(EVENT):
    def _parse_generic_kwargs(self) -> dict:
        event_id = (
            self.raw_event["possessionEventId"] 
            if self.raw_event["possessionEventId"] is not None
            else self.raw_event["gameEventId"]
        )

        return {
            "period": self.period,
            "timestamp": timedelta(seconds=self.raw_event["eventTime"]),
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.ALIVE,
            "event_id": event_id,
            "team": self.team,
            "player": self.player,
            "coordinates": parse_coordinates(self.player, self.raw_event),
            "raw_event": self.raw_event,
        }


class PASS(POSSESSION_EVENT):
    """PFF Pass event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        CUTBACK = 'B'
        CREATE_CONTEST = 'C'
        FLICK_ON = 'F'
        LONG_THROW = 'H'
        LONG_PASS = 'L'
        MISS_HIT = 'M'
        BALL_OVER_THE_TOP = 'O'
        STANDARD_PASS = 'S'
        THROUGH_BALL = 'T'
        SWITCH = 'W'

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        BLOCKED = 'B'
        COMPLETE = 'C'
        DEFENSIVE_INTERCEPTION = 'D'
        INADVERTENT_SHOT_OWN_GOAL = 'G'
        INADVERTENT_SHOT_GOAL = 'I'
        OUT_OF_PLAY = 'O'
        STOPPAGE = 'S'

    class CROSS_TYPE(Enum, metaclass=TypesEnumMeta):
        DRILLED = 'D'
        FLOATED = 'F'
        SWING_IN = 'I'
        SWING_OUT = 'O'
        PLACED = 'P'

    class CROSS_OUTCOME(Enum, metaclass=TypesEnumMeta):
        BLOCKED = 'B'
        COMPLETE = 'C'
        DEFENSIVE_INTERCEPTION = 'D'
        INADVERTENT_SHOT_GOAL = 'I'
        OUT_OF_PLAY = 'O'
        STOPPAGE = 'S'
        UNTOUCHED = 'U'

    class HEIGHT(Enum, metaclass=TypesEnumMeta):
        ABOVE_HEAD = "A"
        GROUND = "G"
        BETWEEN_WAIST_AND_HEAD = "H"
        OFF_GROUND_BUT_BELOW_WAIST = "L"
        VIDEO_MISSING = "M"
        HALF_VOLLEY = "V"

    @property
    def outcome(self) -> Union[OUTCOME, CROSS_OUTCOME, None]:
        try:
            return (
                self.OUTCOME(self.possession_event['passOutcomeType'])
                or self.CROSS_OUTCOME(
                    self.possession_event['crossOutcomeType']
                )
            )
        except Exception:
            return None

    def _pass_outcome_to_result(self) -> PassResult | None:
        if self.outcome is None:
            return None

        outcome_mapping = {
            PASS.OUTCOME.COMPLETE: PassResult.COMPLETE,
            PASS.OUTCOME.BLOCKED: PassResult.INCOMPLETE,
            PASS.OUTCOME.DEFENSIVE_INTERCEPTION: PassResult.INCOMPLETE,
            PASS.OUTCOME.OUT_OF_PLAY: PassResult.OUT,
            PASS.OUTCOME.INADVERTENT_SHOT_OWN_GOAL: None,
            PASS.OUTCOME.INADVERTENT_SHOT_GOAL: None,
            PASS.OUTCOME.STOPPAGE: None,

            PASS.CROSS_OUTCOME.COMPLETE: PassResult.COMPLETE,
            PASS.CROSS_OUTCOME.BLOCKED: PassResult.INCOMPLETE,
            PASS.CROSS_OUTCOME.DEFENSIVE_INTERCEPTION: PassResult.INCOMPLETE,
            PASS.CROSS_OUTCOME.UNTOUCHED: PassResult.INCOMPLETE,
            PASS.CROSS_OUTCOME.OUT_OF_PLAY: PassResult.OUT,
            PASS.CROSS_OUTCOME.INADVERTENT_SHOT_GOAL: None,
            PASS.CROSS_OUTCOME.STOPPAGE: None,
        }

        return outcome_mapping[self.outcome]
 

    def _get_pass_qualifiers(
        self, body_part: BodyPartQualifier | None
    ) -> list[PassQualifier]:
        qualifiers = []

        if self.possession_event['possessionEventType'] == 'CR':
            qualifiers.append(PassQualifier(value=PassType.CROSS))

        pass_type = self.possession_event['passType']
        if pass_type is not None:
            pass_type = PASS.TYPE(pass_type)
            if pass_type == PASS.TYPE.THROUGH_BALL:
                qualifiers.append(PassQualifier(value=PassType.THROUGH_BALL))
            if pass_type == PASS.TYPE.FLICK_ON:
                qualifiers.append(PassQualifier(value=PassType.FLICK_ON))
            if pass_type == PASS.TYPE.STANDARD_PASS:
                qualifiers.append(PassQualifier(value=PassType.SIMPLE_PASS))

        if body_part is not None:
            if body_part.value in [BodyPart.LEFT_HAND, BodyPart.RIGHT_HAND]:
                qualifiers.append(PassQualifier(value=PassType.HAND_PASS))

            if body_part.value == BodyPart.HEAD:
                qualifiers.append(PassQualifier(value=PassType.HEAD_PASS))

        return qualifiers

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        set_piece = self._get_set_piece_qualifier()
        body_part = self._get_body_part_qualifier()
        pass_quals = self._get_pass_qualifiers(body_part)

        qualifiers = collect_qualifiers(body_part, set_piece, *pass_quals)
        result = self._pass_outcome_to_result()

        return [
            event_factory.build_pass(
                result=result,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
        ]


class SHOT(POSSESSION_EVENT):
    """PFF Shot event."""

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        ON_TARGET_BLOCKED = "B"
        OFF_TARGET_BLOCKED = "C"
        SAVED_OFF_TARGET = "F"
        GOAL = "G"
        GOAL_LINE_CLEARANCE = "L"
        OFF_TARGET = "O"
        ON_TARGET = "S"

    @property
    def outcome(self) -> Union[OUTCOME, None]:
        try:
            return self.OUTCOME(self.possession_event['shotOutcomeType'])
        except Exception:
            return None

    def _shot_outcome_to_result(self) -> ShotResult | None:
        if self.outcome is None:
            return None

        outcome_map = {
            SHOT.OUTCOME.ON_TARGET_BLOCKED: ShotResult.BLOCKED,
            SHOT.OUTCOME.OFF_TARGET_BLOCKED: ShotResult.BLOCKED,
            SHOT.OUTCOME.SAVED_OFF_TARGET: ShotResult.SAVED,
            SHOT.OUTCOME.GOAL: ShotResult.GOAL,
            SHOT.OUTCOME.GOAL_LINE_CLEARANCE: ShotResult.BLOCKED,
            SHOT.OUTCOME.OFF_TARGET: ShotResult.OFF_TARGET,
            SHOT.OUTCOME.ON_TARGET: ShotResult.SAVED,
        }

        return outcome_map.get(self.outcome)

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        body_part = self._get_body_part_qualifier()
        set_piece = self._get_set_piece_qualifier()

        qualifiers = collect_qualifiers(body_part, set_piece)
        result = self._shot_outcome_to_result()

        return [
            event_factory.build_shot(
                result=result,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
        ]


class CLEARANCE(POSSESSION_EVENT):
    """PFF Clearance event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_clearance(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class DUEL(POSSESSION_EVENT):
    """PFF Challenge event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        AERIAL_DUEL = 'A'
        FROM_BEHIND = 'B'
        DRIBBLE = 'D'
        FIFTY = 'FIFTY'
        GK_SMOTHERS = 'G'
        SHIELDING = 'H'
        HAND_TACKLE = 'K'  # GK specific event
        SLIDE_TACKLE = 'L'
        SHOULDER_TO_SHOULDER = 'S'
        STANDING_TACKLE = 'T'

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        DISTRIBUTION_DISRUPTED = 'B'
        FORCED_OUT_OF_PLAY = 'C'
        DISTRIBUTES_BALL = 'D'
        FOUL = 'F'
        SHIELDS_IN_PLAY = 'I'
        KEEPS_BALL_WITH_CONTACT = 'K'
        ROLLS = 'L'
        BEATS_MAN_LOSES_BALL = 'M'
        NO_WIN_KEEP_BALL = 'N'
        OUT_OF_PLAY = 'O'
        PLAYER = 'P'
        RETAIN = 'R'
        SHIELDS_OUT_OF_PLAY = 'S'

    @property
    def outcome(self):
        try:
            return self.OUTCOME(
                self.raw_event['possessionEvents']['challengeOutcomeType']
            )
        except Exception:
            return None

    @property
    def duel_type(self):
        try:
            return self.TYPE(
                self.raw_event['possessionEvents']['challengeType']
            )
        except Exception:
            return None

    def _handle_dribble(
            self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        if self.outcome in [
            DUEL.OUTCOME.OUT_OF_PLAY,
            DUEL.OUTCOME.FORCED_OUT_OF_PLAY
        ]:
            result = TakeOnResult.OUT
        elif self.outcome in [
            DUEL.OUTCOME.NO_WIN_KEEP_BALL,
            DUEL.OUTCOME.ROLLS,
            DUEL.OUTCOME.DISTRIBUTION_DISRUPTED,
            DUEL.OUTCOME.DISTRIBUTES_BALL,
            DUEL.OUTCOME.PLAYER,
        ]:
            result = TakeOnResult.INCOMPLETE
        else:
            result = TakeOnResult.COMPLETE

        return [
            event_factory.build_take_on(
                result=result,
                qualifiers=[DuelQualifier(value=DuelType.GROUND)],
                **generic_event_kwargs
            )
        ]

    def _handle_aerial(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        events = []

        qualifiers = [
            DuelQualifier(value=DuelType.LOOSE_BALL),
            DuelQualifier(value=DuelType.AERIAL)
        ]

        aerialChallengeColumns = [
            'homeDuelPlayerId',
            'awayDuelPlayerId',
            'challengeKeeperPlayerId',
            'additionalDuelerPlayerId'
        ]

        players_involved = [
            find_player(self.possession_event[col], self.teams)
            for col in aerialChallengeColumns
            if self.raw_event['possessionEvents'][col] is not None
        ]

        winner = find_player(
            self.raw_event['possessionEvents']['challengeWinnerPlayerId'],
            self.teams
        )

        if winner is None:
            player_duel_result = [
                (player, DuelResult.NEUTRAL)
                for player in players_involved
                if player is not None
            ]
        else:
            player_duel_result = [
                (
                    player,
                    (
                        DuelResult.WON
                        if player.team == winner.team
                        else DuelResult.LOST
                    )
                )
                for player in players_involved
                if player is not None
            ]

        for (player, result) in player_duel_result:
            kwargs = deepcopy(generic_event_kwargs)
            kwargs['team'] = player.team
            kwargs['player'] = player
            events.append(
                event_factory.build_duel(
                    result=result,
                    qualifiers=qualifiers,
                    **kwargs,
                )
            )

        return events

    def _handle_tackle(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        events = []

        qualifiers = [DuelQualifier(value=DuelType.GROUND)]

        if self.duel_type == DUEL.TYPE.SLIDE_TACKLE:
            qualifiers.append(DuelQualifier(value=DuelType.SLIDING_TACKLE))
        elif self.duel_type == DUEL.TYPE.FIFTY:
            qualifiers.append(DuelQualifier(value=DuelType.LOOSE_BALL))

        challengeColumns = [
            'ballCarrierPlayerId',
            'challengerPlayerId',
            'challengeKeeperPlayerId',
            'additionalDuelerPlayerId',
        ]

        players_involved = [
            find_player(self.raw_event['possessionEvents'][col], self.teams)
            for col in challengeColumns 
            if self.raw_event['possessionEvents'][col] is not None
        ]

        winner = find_player(
            self.raw_event['possessionEvents']['challengeWinnerPlayerId'],
            self.teams
        )

        if not winner:
            player_duel_result = [
                (player, DuelResult.NEUTRAL)
                for player in players_involved
                if player is not None
            ]
        else:
            player_duel_result = [
                (
                    player,
                    (
                        DuelResult.WON
                        if player.team == winner.team
                        else DuelResult.LOST
                    )
                )
                for player in players_involved
                if player is not None
            ]

        for (player, result) in player_duel_result:
            kwargs = deepcopy(generic_event_kwargs)
            kwargs['team'] = player.team
            kwargs['player'] = player
            events.append(
                event_factory.build_duel(
                    result=result,
                    qualifiers=qualifiers,
                    **kwargs,
                )
            )

        return events

    def _handle_gk(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        qualifiers = [
            GoalkeeperQualifier(value=GoalkeeperActionType.SMOTHER)
        ]

        return [
            event_factory.build_goalkeeper_event(
                result=None,
                qualifiers=qualifiers,
                **generic_event_kwargs
            )
        ]

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        if self.duel_type == DUEL.TYPE.DRIBBLE:
            return self._handle_dribble(event_factory, **generic_event_kwargs)
        elif self.duel_type == DUEL.TYPE.AERIAL_DUEL:
            return self._handle_aerial(event_factory, **generic_event_kwargs)
        elif self.duel_type in [
            DUEL.TYPE.SLIDE_TACKLE,
            DUEL.TYPE.FIFTY,
            DUEL.TYPE.FROM_BEHIND,
            DUEL.TYPE.STANDING_TACKLE,
            DUEL.TYPE.SHOULDER_TO_SHOULDER,
            DUEL.TYPE.SHIELDING,
            DUEL.TYPE.HAND_TACKLE # GK Event
        ]:
            return self._handle_tackle(event_factory, **generic_event_kwargs)
        elif self.duel_type == DUEL.TYPE.GK_SMOTHERS:
            return self._handle_gk(event_factory, **generic_event_kwargs)
 
        return [event_factory.build_generic(**generic_event_kwargs)]


class CARRY(POSSESSION_EVENT):
    """PFF Carry event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_carry(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class PRESSURE(POSSESSION_EVENT):
    """PFF Pressure event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_pressure_event(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class INTERCEPTION(POSSESSION_EVENT):
    """PFF Interception event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_interception(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class RECOVERY(POSSESSION_EVENT):
    """PFF Recovery event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_recovery(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class MISCONTROL(POSSESSION_EVENT):
    """PFF Miscontrol event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_miscontrol(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class GOALKEEPER(POSSESSION_EVENT):
    """PFF Goalkeeper event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        return [
            event_factory.build_goalkeeper_event(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


def possession_event_decoder(raw_event: dict) -> POSSESSION_EVENT:
    type_to_possession_event = {
        POSSESSION_EVENT_TYPE.CROSS: PASS,
        POSSESSION_EVENT_TYPE.PASS: PASS,
        POSSESSION_EVENT_TYPE.SHOT: SHOT,
        POSSESSION_EVENT_TYPE.CLEARANCE: CLEARANCE,
        POSSESSION_EVENT_TYPE.BALL_CARRY: CARRY,
        POSSESSION_EVENT_TYPE.CHALLENGE: DUEL,
        POSSESSION_EVENT_TYPE.REBOUND: POSSESSION_EVENT,
        POSSESSION_EVENT_TYPE.TOUCHES: POSSESSION_EVENT,
        POSSESSION_EVENT_TYPE.EVT_START: BALL_RECEIPT,
    }

    p_evt_type = raw_event["possessionEvents"]["possessionEventType"]

    if p_evt_type is None:
        return POSSESSION_EVENT(raw_event)

    event_type = POSSESSION_EVENT_TYPE(p_evt_type)
    event_creator = type_to_possession_event.get(event_type, POSSESSION_EVENT)
    return event_creator(raw_event)


def event_decoder(raw_event: dict) -> EVENT:
    type_to_event = {
        EVENT_TYPE.POSSESSION: possession_event_decoder,
        EVENT_TYPE.FIRST_HALF_KICKOFF: possession_event_decoder,
        EVENT_TYPE.SECOND_HALF_KICKOFF: possession_event_decoder,
        EVENT_TYPE.THIRD_HALF_KICKOFF: possession_event_decoder,
        EVENT_TYPE.FOURTH_HALF_KICKOFF: possession_event_decoder,
        EVENT_TYPE.GAME_CLOCK_OBSERVATION: EVENT,
        EVENT_TYPE.GROUND: EVENT,
        EVENT_TYPE.BALL_OUT_OF_PLAY: BALL_OUT,
        EVENT_TYPE.SUB: SUBSTITUTION,
        EVENT_TYPE.PLAYER_ON: PLAYER_ON,
        EVENT_TYPE.PLAYER_OFF: PLAYER_OFF,
    }

    event_type = EVENT_TYPE(raw_event["gameEvents"]["gameEventType"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
