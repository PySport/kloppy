from datetime import timedelta
from enum import Enum
from typing import Dict, List, Union, Optional

from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
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
    TakeOnResult,
    Team,
    Point,
    Point3D,
    CardType,
)
from kloppy.infra.serializers.event.korastats.helpers import (
    get_period_by_id,
    get_team_by_id,
    check_pass_receiver,
)


class EVENT_CATEGORY_TYPE(Enum):
    # Administrative events
    ADMINISTRATIVE_FOUL = (1, 1)
    ADMINISTRATIVE_OFFSIDE = (1, 2)
    ADMINISTRATIVE_HANDBALL = (1, 3)
    ADMINISTRATIVE_PENALTY = (1, 4)
    ADMINISTRATIVE_BAD_BEHAVIOR = (1, 5)
    ADMINISTRATIVE_ADVANTAGE = (1, 52)
    ADMINISTRATIVE_GK_6_SEC = (1, 53)
    ADMINISTRATIVE_GK_HAND = (1, 54)
    ADMINISTRATIVE_SUBSTITUTION = (1, 28)
    ADMINISTRATIVE_END_OF_HALF = (1, 47)
    ADMINISTRATIVE_END_OF_MATCH = (1, 48)

    # Goalkeeper events
    GOALKEEPER_CROSS = (2, 6)
    GOALKEEPER_FREEKICK = (2, 7)
    GOALKEEPER_PENALTY = (2, 8)
    GOALKEEPER_ONE_ON_ONE = (2, 9)
    GOALKEEPER_SHOOT = (2, 10)
    GOALKEEPER_OWN_GOAL_CONCEDED = (2, 49)

    # Defensive events
    DEFENSIVE_BLOCK = (3, 11)
    DEFENSIVE_TACKLE_CLEAR = (3, 36)
    DEFENSIVE_INTERCEPT_CLEAR = (3, 37)
    DEFENSIVE_CLEAR = (3, 38)
    DEFENSIVE_SHIELD = (3, 44)
    DEFENSIVE_OWN_GOAL = (3, 14)
    DEFENSIVE_OUT_OF_POSITION = (3, 55)
    DEFENSIVE_COVERING_OFFSIDE = (3, 56)
    DEFENSIVE_PRESSING = (3, 57)

    # Possession events
    POSSESSION_PASS = (4, 15)
    POSSESSION_AERIAL_BALL = (4, 16)
    POSSESSION_CROSS = (4, 17)
    POSSESSION_POSSESSION = (4, 18)
    POSSESSION_DRIBBLE = (4, 19)
    POSSESSION_EFFECTIVE_PASS = (4, 20)
    POSSESSION_FREEKICK_CROSS = (4, 26)
    POSSESSION_CORNER_CROSS = (4, 27)
    POSSESSION_LONG_PASS = (4, 29)
    POSSESSION_CORNER_PASS = (4, 31)
    POSSESSION_BALL_RECEIVED = (4, 32)
    POSSESSION_TACKLE = (4, 33)
    POSSESSION_INTERCEPTION = (4, 34)
    POSSESSION_RECOVER = (4, 35)
    POSSESSION_FREEKICK_PASS = (4, 39)
    POSSESSION_FREEKICK_LONG_PASS = (4, 40)
    POSSESSION_THROW_IN_SHORT_PASS = (4, 41)
    POSSESSION_THROW_IN_LONG_PASS = (4, 42)
    POSSESSION_THROW_IN_CROSS = (4, 43)
    POSSESSION_GK_PASS = (4, 58)
    POSSESSION_GK_LONG_PASS = (4, 59)
    POSSESSION_MISS_TOUCH = (4, 64)
    POSSESSION_TAKE_ON_AGAINST = (4, 65)
    POSSESSION_TAKE_ON = (4, 66)

    # Attack events
    ATTACK_SHOOT = (5, 21)
    ATTACK_ONE_ON_ONE = (5, 22)
    ATTACK_PENALTY = (5, 23)
    ATTACK_OWN_GOAL_IN_OPPONENT = (5, 30)
    ATTACK_SHOOT_LOCATION = (5, 50)
    ATTACK_CORNER = (5, 24)
    ATTACK_FREEKICK = (5, 25)
    ATTACK_PENALTY_SHOOTOUT = (5, 45)

    # Ball actions
    BALL_ACTIONS_BALL_PAST_LINE = (6, 60)


class RESULT(Enum):
    ADMINISTRATIVE_NONE = 1  # "None"
    ADMINISTRATIVE_YELLOW_CARD = 2  # "YellowCard"
    ADMINISTRATIVE_SECOND_YELLOW_CARD = 18  # "SecondYellowCard"
    ADMINISTRATIVE_RED_CARD = 3  # "RedCard"

    GOALKEEPER_GOAL_CONCEDED = 4  # "GoalConceded"
    GOALKEEPER_SAVE = 5  # "Save"
    GOALKEEPER_OFF = 19  # "Off"
    GOALKEEPER_BARS = 20  # "Bars"

    DEFENSIVE_GOAL_KICK = 6  # "GoalKick"
    DEFENSIVE_CLEAR = 7  # "Clear"
    DEFENSIVE_CORNER_KICK = 8  # "CornerKick"
    DEFENSIVE_OWN_GOAL = 9  # "OwnGoal"
    POSSESSION_SUCCESS = 10  # "Success"
    POSSESSION_FAIL = 11  # "Fail"

    ATTACK_OFF_TARGET = 12  # "OffTarget"
    ATTACK_BARS = 13  # "Bars"
    ATTACK_ON_TARGET = 14  # "OnTarget"
    ATTACK_BLOCK_BY_DEFENSE = 15  # "BlockByDefense"
    ATTACK_CORNER_KICK = 16  # "CornerKick"
    ATTACK_GOAL = 17  # "Goal"

    BALL_ACTIONS_OUTSIDE = 21  # "Outside"
    BALL_ACTIONS_GOAL_KICK = 22  # "Goalkick"
    BALL_ACTIONS_CORNER = 23  # "Corner"
    BALL_ACTIONS_GOAL_POST = 24  # "Goal Post"


class EXTRA(Enum):
    NA = 1  # "N/A"
    AWARDED = 2  # "Awarded"
    COMMITTED = 3  # "Committed"
    RIGHT_FOOT = 4  # "RightFoot"
    LEFT_FOOT = 5  # "LeftFoot"
    HEADER = 6  # "Header"
    OTHER = 7  # "Other"
    ASSIST = 8  # "Assist"
    SUBSTITUTE_IN = 9  # "SubstituteIn"
    SUBSTITUTE_OUT = 10  # "SubstituteOut"
    KEY_PASS = 11  # "KeyPass"
    SIDE_LINE = 12  # "Side Line"
    END_LINE = 13  # "End Line"
    GOAL_LINE = 14  # "Goal Line"
    ERROR_LEAD_TO_GOAL = 15  # "ErrorLeadToGoal"
    ERROR_LEAD_TO_OPPORTUNITY = 16  # "ErrorLeadToOpportunity"
    COVERING_OFFSIDE = 17  # "Covering Offside"
    OPPORTUNITY_SAVED = 18  # "Opportunity Saved"
    GOAL_SAVED = 19  # "Goal Saved"


pass_result_mapping = {
    RESULT.POSSESSION_SUCCESS: PassResult.COMPLETE,
    RESULT.POSSESSION_FAIL: PassResult.INCOMPLETE,
}

shot_result_mapping = {
    RESULT.ATTACK_GOAL: ShotResult.GOAL,
    RESULT.ATTACK_ON_TARGET: ShotResult.SAVED,
    RESULT.ATTACK_OFF_TARGET: ShotResult.OFF_TARGET,
    RESULT.ATTACK_BARS: ShotResult.POST,
    RESULT.ATTACK_BLOCK_BY_DEFENSE: ShotResult.BLOCKED,
}

take_on_result_mapping = {
    RESULT.POSSESSION_SUCCESS: TakeOnResult.COMPLETE,
    RESULT.POSSESSION_FAIL: TakeOnResult.INCOMPLETE,
}

duel_result_mapping = {
    RESULT.POSSESSION_SUCCESS: DuelResult.WON,
    RESULT.POSSESSION_FAIL: DuelResult.LOST,
}

interception_result_mapping = {
    RESULT.POSSESSION_SUCCESS: InterceptionResult.SUCCESS,
    RESULT.POSSESSION_FAIL: InterceptionResult.LOST,
}

carry_result_mapping = {
    RESULT.POSSESSION_SUCCESS: CarryResult.COMPLETE,
    RESULT.POSSESSION_FAIL: CarryResult.INCOMPLETE,
}

body_part_mapping = {
    EXTRA.RIGHT_FOOT: BodyPart.RIGHT_FOOT,
    EXTRA.LEFT_FOOT: BodyPart.LEFT_FOOT,
    EXTRA.HEADER: BodyPart.HEAD,
    EXTRA.OTHER: BodyPart.OTHER,
}


class EVENT:
    """Base class for KoraStats events.

    This class is used to deserialize KoraStats events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event
        self.event_category_type = EVENT_CATEGORY_TYPE(
            (self.raw_event["category_id"], self.raw_event["event_id"])
        )
        self.result = (
            RESULT(self.raw_event["result_id"])
            if "result_id" in self.raw_event
            else None
        )
        self.extra = (
            EXTRA(self.raw_event["extra_id"])
            if "extra_id" in self.raw_event
            else None
        )

    def set_refs(self, periods, teams):
        self.period = get_period_by_id(self.raw_event["half"], periods)
        self.team = (
            get_team_by_id(self.raw_event["team_id"], teams)
            if self.raw_event["team_id"]
            else None
        )
        self.player = (
            self.team.get_player_by_id(self.raw_event["player_id"])
            if self.team and self.raw_event["player_id"]
            else None
        )

        return self

    def deserialize(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
    ) -> List[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.
            teams: The teams in the match.
            next_event: The next event in the sequence.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs(teams)
        events = self._create_events(
            event_factory,
            teams,
            prior_event,
            next_event,
            **generic_event_kwargs,
        )

        return events

    def _parse_generic_kwargs(self, teams: List[Team]) -> Dict:
        # defensive events
        if self.event_category_type.value[0] == 3:
            ball_owning_team = next(t for t in teams if t != self.team)
        else:
            ball_owning_team = self.team
        return {
            "period": self.period,
            "timestamp": timedelta(seconds=self.raw_event["timeInSec"]),
            "ball_owning_team": ball_owning_team,
            "ball_state": None,
            "event_id": str(self.raw_event["_id"]),
            "team": self.team,
            "player": self.player,
            "coordinates": Point(self.raw_event["x"], self.raw_event["y"]),
            "raw_event": self.raw_event,
        }

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["event"],
            **generic_event_kwargs,
        )
        return [generic_event]


class PASS(EVENT):
    """KoraStats Pass event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        result = pass_result_mapping[self.result]

        # Determine receiver and coordinates for successful passes
        receiver_player = None
        receiver_coordinates = Point(self.raw_event["x"], self.raw_event["y"])
        if next_event:
            receive_timestamp = timedelta(seconds=next_event["timeInSec"])
        else:
            receive_timestamp = generic_event_kwargs["timestamp"] + timedelta(
                milliseconds=500
            )
        if next_event:
            receiver_player, receiver_coordinates = check_pass_receiver(
                self.raw_event, teams, next_event
            )
            pass

        # Build qualifiers
        qualifiers = []

        if self.extra == EXTRA.KEY_PASS:
            qualifiers.append(PassQualifier(value=PassType.SMART_PASS))
        if self.extra == EXTRA.ASSIST:
            qualifiers.append(PassQualifier(value=PassType.ASSIST))

        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_LONG_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_GK_LONG_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_LONG_PASS,
        ]:
            qualifiers.append(PassQualifier(value=PassType.LONG_BALL))
        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_CROSS,
            EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_CROSS,
            EVENT_CATEGORY_TYPE.POSSESSION_CORNER_CROSS,
        ]:
            qualifiers.append(PassQualifier(value=PassType.CROSS))
        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_CORNER_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_CORNER_CROSS,
        ]:
            qualifiers.append(
                SetPieceQualifier(value=SetPieceType.CORNER_KICK)
            )
        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_LONG_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_CROSS,
        ]:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))
        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_GK_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_GK_LONG_PASS,
        ]:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))
        if self.event_category_type in [
            EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_SHORT_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_LONG_PASS,
            EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_CROSS,
        ]:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))

        first_event_of_period = (
            prior_event is None
            or prior_event["half"] != self.raw_event["half"]
        )
        if first_event_of_period:
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


class BALL_RECEIVED(EVENT):
    """KoraStats Ball Received event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        # Ball received events are typically handled as part of pass events
        # This might be a separate event in some cases
        return [
            event_factory.build_generic(
                event_name="ball_received",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class SHOT(EVENT):
    """KoraStats Shot event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        result = shot_result_mapping[self.result]
        # Build qualifiers
        qualifiers = []

        # Body part qualifiers
        if self.extra in body_part_mapping:
            qualifiers.append(
                BodyPartQualifier(value=body_part_mapping[self.extra])
            )

        # Set piece qualifiers
        if self.event_category_type in [EVENT_CATEGORY_TYPE.ATTACK_PENALTY]:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.PENALTY))
        if self.event_category_type in [EVENT_CATEGORY_TYPE.ATTACK_CORNER]:
            qualifiers.append(
                SetPieceQualifier(value=SetPieceType.CORNER_KICK)
            )
        if self.event_category_type in [EVENT_CATEGORY_TYPE.ATTACK_FREEKICK]:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))

        result_coordinates = None
        if next_event["event"] == "Shoot Location":
            x_coordinate = 100
            y_coordinate = (next_event["x"] / 300) * 10 + 50
            z_coordinate = next_event["y"]
            result_coordinates = Point3D(
                x_coordinate, y_coordinate, z_coordinate
            )

        shot_event = event_factory.build_shot(
            result=result,
            qualifiers=qualifiers,
            result_coordinates=result_coordinates,
            **generic_event_kwargs,
        )

        return [shot_event]


class TACKLE(EVENT):
    """KoraStats Tackle event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        if (
            self.event_category_type
            == EVENT_CATEGORY_TYPE.DEFENSIVE_TACKLE_CLEAR
        ):
            result = DuelResult.WON
        else:
            result = interception_result_mapping[self.result]

        qualifiers = [
            DuelQualifier(value=DuelType.TACKLE),
            DuelQualifier(value=DuelType.GROUND),
        ]

        return [
            event_factory.build_duel(
                result=result,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
        ]


class INTERCEPTION(EVENT):
    """KoraStats Interception event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        if (
            self.event_category_type
            == EVENT_CATEGORY_TYPE.DEFENSIVE_INTERCEPT_CLEAR
        ):
            result = InterceptionResult.SUCCESS
        else:
            result = interception_result_mapping[self.result]

        return [
            event_factory.build_interception(
                result=result,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class RECOVER(EVENT):
    """KoraStats Recovery event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_recovery(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class DRIBBLE(EVENT):
    """KoraStats Dribble event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        result = take_on_result_mapping[self.result]

        return [
            event_factory.build_take_on(
                result=result,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class CLEAR(EVENT):
    """KoraStats Clear event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_clearance(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class BLOCK(EVENT):
    """KoraStats Block event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_generic(
                event_name="block",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class AERIAL_BALL(EVENT):
    """KoraStats Aerial Ball event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        result = duel_result_mapping[self.result]

        qualifiers = [DuelQualifier(value=DuelType.AERIAL)]

        return [
            event_factory.build_duel(
                result=result,
                qualifiers=qualifiers,
                **generic_event_kwargs,
            )
        ]


class FOUL(EVENT):
    """KoraStats Foul event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        # Only create event for 'Committed' administrativeType
        if self.extra == EXTRA.AWARDED:
            return []

        events = [
            event_factory.build_foul_committed(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]
        card_provider_results = [
            RESULT.ADMINISTRATIVE_YELLOW_CARD,
            RESULT.ADMINISTRATIVE_SECOND_YELLOW_CARD,
            RESULT.ADMINISTRATIVE_RED_CARD,
        ]
        card_kloppy_types = [
            CardType.FIRST_YELLOW,
            CardType.SECOND_YELLOW,
            CardType.RED,
        ]
        for result, card_type in zip(card_provider_results, card_kloppy_types):
            if self.result == result:
                generic_event_kwargs[
                    "event_id"
                ] = f"{generic_event_kwargs['event_id']}-{card_type.value.lower()}"
                events.append(
                    event_factory.build_card(
                        result=None,
                        qualifiers=None,
                        card_type=card_type,
                        **generic_event_kwargs,
                    )
                )

        return events


class SUBSTITUTION(EVENT):
    """KoraStats Sub event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        # Only parse sub out event
        if self.extra == EXTRA.SUBSTITUTE_IN:
            return []

        if next_event.get("extra") == "SubstituteIn":
            replacement_player_id = next_event["player_id"]
            replacement_player = self.team.get_player_by_id(
                str(replacement_player_id)
            )
        elif prior_event.get("extra") == "SubstituteIn":
            replacement_player_id = prior_event["player_id"]
            replacement_player = self.team.get_player_by_id(
                str(replacement_player_id)
            )
        else:
            raise ValueError("Substitution event without replacement player")

        sub_event = event_factory.build_substitution(
            result=None,
            qualifiers=None,
            replacement_player=replacement_player,
            **generic_event_kwargs,
        )

        return [sub_event]


class OFFSIDE(EVENT):
    """KoraStats Offside event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_generic(
                event_name="offside",
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class BALL_LOST_UNDER_PRESSURE(EVENT):
    """KoraStats Ball Lost Under Pressure event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_miscontrol(
                **generic_event_kwargs,
            )
        ]


class PRESSING(EVENT):
    """KoraStats Pressing event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        # For pressure events, we need end timestamp
        # This might need to be calculated from next event or other logic
        end_timestamp = None
        if next_event:
            end_timestamp = timedelta(seconds=next_event["timeInSec"])

        return [
            event_factory.build_pressure_event(
                end_timestamp=end_timestamp
                or generic_event_kwargs["timestamp"] + timedelta(seconds=1),
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


class GOALKEEPER(EVENT):
    """KoraStats Goalkeeper Save event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        if self.result == RESULT.GOALKEEPER_SAVE:
            qualifiers = [GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)]
            return [
                event_factory.build_goalkeeper_event(
                    result=None,
                    qualifiers=qualifiers,
                    **generic_event_kwargs,
                )
            ]
        else:
            return []


class BALL_OUT(EVENT):
    """KoraStats Ball Out event."""

    def _create_events(
        self,
        event_factory: EventFactory,
        teams: List[Team],
        prior_event: Optional[Dict],
        next_event: Optional[Dict],
        **generic_event_kwargs,
    ) -> List[Event]:
        return [
            event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
        ]


def create_korastats_events(
    raw_events: List[Dict],
) -> Dict[str, Union[EVENT, Dict]]:
    korastats_events = {}
    for ix, raw_event in enumerate(raw_events):
        korastats_event = event_decoder(raw_event)
        if korastats_event:
            korastats_events[raw_event["_id"]] = korastats_event

    return korastats_events


def event_decoder(raw_event: Dict) -> Optional[EVENT]:
    """Decode a raw KoraStats event into the appropriate event class, using both event and category for disambiguation."""
    event_category_type = EVENT_CATEGORY_TYPE(
        (raw_event["category_id"], raw_event["event_id"])
    )

    tuple_type_to_event = {
        # Administrative events
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_FOUL: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_OFFSIDE: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_HANDBALL: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_PENALTY: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_BAD_BEHAVIOR: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_ADVANTAGE: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_GK_6_SEC: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_GK_HAND: FOUL,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_SUBSTITUTION: SUBSTITUTION,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_END_OF_HALF: None,
        EVENT_CATEGORY_TYPE.ADMINISTRATIVE_END_OF_MATCH: None,
        # Goalkeeper events
        EVENT_CATEGORY_TYPE.GOALKEEPER_CROSS: GOALKEEPER,
        EVENT_CATEGORY_TYPE.GOALKEEPER_FREEKICK: GOALKEEPER,
        EVENT_CATEGORY_TYPE.GOALKEEPER_PENALTY: GOALKEEPER,
        EVENT_CATEGORY_TYPE.GOALKEEPER_ONE_ON_ONE: None,
        EVENT_CATEGORY_TYPE.GOALKEEPER_SHOOT: GOALKEEPER,
        # EVENT_CATEGORY_TYPE.GOALKEEPER_PENALTY_SHOOT_OUT: None,
        EVENT_CATEGORY_TYPE.GOALKEEPER_OWN_GOAL_CONCEDED: None,
        # Defensive events
        EVENT_CATEGORY_TYPE.DEFENSIVE_BLOCK: BLOCK,
        # (EVENT_CATEGORY.DEFENSIVE, EVENT_TYPE.OWN_GOAL): None,
        EVENT_CATEGORY_TYPE.DEFENSIVE_TACKLE_CLEAR: TACKLE,
        EVENT_CATEGORY_TYPE.DEFENSIVE_INTERCEPT_CLEAR: INTERCEPTION,
        EVENT_CATEGORY_TYPE.DEFENSIVE_CLEAR: CLEAR,
        EVENT_CATEGORY_TYPE.DEFENSIVE_SHIELD: None,
        EVENT_CATEGORY_TYPE.DEFENSIVE_OUT_OF_POSITION: None,
        # (EVENT_CATEGORY.DEFENSIVE, EVENT_TYPE.COVERING_OFFSIDE): None,
        EVENT_CATEGORY_TYPE.DEFENSIVE_PRESSING: PRESSING,
        # Possession events
        EVENT_CATEGORY_TYPE.POSSESSION_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_AERIAL_BALL: AERIAL_BALL,
        EVENT_CATEGORY_TYPE.POSSESSION_CROSS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_EFFECTIVE_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_POSSESSION: None,
        EVENT_CATEGORY_TYPE.POSSESSION_DRIBBLE: DRIBBLE,
        EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_CROSS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_CORNER_CROSS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_LONG_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_CORNER_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_BALL_RECEIVED: None,
        EVENT_CATEGORY_TYPE.POSSESSION_TACKLE: TACKLE,
        EVENT_CATEGORY_TYPE.POSSESSION_INTERCEPTION: INTERCEPTION,
        EVENT_CATEGORY_TYPE.POSSESSION_RECOVER: RECOVER,
        EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_FREEKICK_LONG_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_SHORT_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_LONG_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_THROW_IN_CROSS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_GK_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_GK_LONG_PASS: PASS,
        EVENT_CATEGORY_TYPE.POSSESSION_TAKE_ON: DRIBBLE,
        # EVENT_CATEGORY_TYPE.POSSESSION_TAKE_ON_AGAINST: DRIBBLE,
        EVENT_CATEGORY_TYPE.ATTACK_SHOOT: SHOT,
        EVENT_CATEGORY_TYPE.ATTACK_ONE_ON_ONE: None,
        EVENT_CATEGORY_TYPE.ATTACK_PENALTY: SHOT,
        EVENT_CATEGORY_TYPE.ATTACK_CORNER: SHOT,
        EVENT_CATEGORY_TYPE.ATTACK_FREEKICK: SHOT,
        EVENT_CATEGORY_TYPE.ATTACK_OWN_GOAL_IN_OPPONENT: SHOT,
        EVENT_CATEGORY_TYPE.ATTACK_SHOOT_LOCATION: None,
        # ATTACK_PENALTY_SHOOTOUT = "PenaltyShootOut"
        # Ball actions
        EVENT_CATEGORY_TYPE.BALL_ACTIONS_BALL_PAST_LINE: BALL_OUT,
    }

    event_creator = tuple_type_to_event[event_category_type]

    if event_creator:
        return event_creator(raw_event)
