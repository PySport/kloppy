from dataclasses import dataclass, field
from datetime import timedelta, datetime
from typing import (
    overload,
    Union,
    Optional,
    TypeVar,
    Generic,
    List,
    Tuple,
    NamedTuple,
)

from sortedcontainers import SortedList

from kloppy.exceptions import KloppyError


@dataclass
class Period:
    """
    Period

    Attributes:
        id: `1` for first half, `2` for second half, `3` for first half of
            overtime, `4` for second half of overtime, `5` for penalty shootout
        start_timestamp: The UTC datetime of the kick-off or, if the
            absolute datetime is not available, the offset between the start
            of the data feed and the period's kick-off
        end_timestamp: The UTC datetime of the final whistle or, if the
            absolute datetime is not available, the offset between the start
            of the data feed and the period's final whistle
        attacking_direction: See [`AttackingDirection`][kloppy.domain.models.common.AttackingDirection]
    """

    id: int
    start_timestamp: Union[datetime, timedelta]
    end_timestamp: Union[datetime, timedelta]

    prev_period: Optional["Period"] = field(init=False)
    next_period: Optional["Period"] = field(init=False)

    def contains(self, timestamp: datetime):
        if isinstance(self.start_timestamp, datetime) and isinstance(
            self.end_timestamp, datetime
        ):
            return self.start_timestamp <= timestamp <= self.end_timestamp
        raise KloppyError(
            "This method can only be used when start_timestamp and end_timestamp are a datetime"
        )

    @property
    def start_abs_time(self) -> "AbsTime":
        return AbsTime(period=self, timestamp=self.start_timestamp)

    @property
    def end_abs_time(self) -> "AbsTime":
        return AbsTime(period=self, timestamp=self.end_timestamp)

    @property
    def duration(self) -> timedelta:
        return self.end_timestamp - self.start_timestamp

    def __eq__(self, other):
        return isinstance(other, Period) and other.id == self.id

    def __lt__(self, other: "Period"):
        return self.id < other.id

    def __ge__(self, other):
        return self == other or other < self

    def __hash__(self):
        return id(self.id)

    def set_refs(
        self,
        prev: Optional["Period"],
        next_: Optional["Period"],
    ):
        """
        Set references to other periods

        Parameters:
            prev: Period before this period
            next_: Period after this period
        """
        self.prev_period = prev
        self.next_period = next_


@dataclass
class AbsTime:
    period: "Period"
    timestamp: timedelta

    @overload
    def __sub__(self, other: timedelta) -> "AbsTime":
        ...

    @overload
    def __sub__(self, other: "AbsTime") -> timedelta:
        ...

    def __sub__(
        self, other: Union["AbsTime", timedelta]
    ) -> Union["AbsTime", timedelta]:
        """
        Subtract a timedelta or AbsTime from the current AbsTime.

        AbsTime - AbsTime = timedelta
        AbsTime - timedelta = AbsTime

        The period duration must be taking into account.
        """
        if isinstance(other, timedelta):
            current_timestamp = self.timestamp
            current_period = self.period
            while other > current_timestamp:
                other -= current_timestamp
                if not current_period.prev_period:
                    # We reached start of the match, lets just return start itself
                    return AbsTime(
                        period=current_period, timestamp=timedelta(0)
                    )

                current_period = current_period.prev_period
                current_timestamp = current_period.duration

            return AbsTime(
                period=current_period, timestamp=current_timestamp - other
            )

        elif isinstance(other, AbsTime):
            if self.period >= other.period:
                diff = self.timestamp
                current_period = self.period
                while current_period > other.period:
                    current_period = current_period.prev_period
                    diff += current_period.duration

                return diff - other.timestamp
            else:
                return -other.__sub__(self)
        else:
            raise ValueError(f"Cannot subtract {other}")

    def __add__(self, other: timedelta) -> "AbsTime":
        assert isinstance(other, timedelta)
        current_timestamp = self.timestamp
        current_period = self.period
        while (current_timestamp + other) > current_period.duration:
            # Subtract time left in this period

            other -= current_period.duration - current_timestamp
            if not current_period.next_period:
                # We reached start of the match, lets just return start itself
                return AbsTime(
                    period=current_period, timestamp=current_period.duration
                )

            current_period = current_period.next_period
            current_timestamp = timedelta(0)

        return AbsTime(
            period=current_period, timestamp=current_timestamp + other
        )

    def __radd__(self, other: timedelta) -> "AbsTime":
        assert isinstance(other, timedelta)
        return self.__add__(other)

    def __rsub__(self, other):
        raise RuntimeError("Doesn't make sense.")

    def __lt__(self, other):
        return self.period < other.period or (
            self.period == other.period and self.timestamp < other.timestamp
        )

    def __str__(self):
        m, s = divmod(self.timestamp.total_seconds(), 60)
        return f"P{self.period.id}T{m:02.0f}:{s:02.0f}"


T = TypeVar("T")


class Pair(NamedTuple):
    key: AbsTime
    item: T


class AbsTimeContainer(Generic[T]):
    def __init__(self):
        self.items: SortedList = SortedList(key=lambda pair: pair.key)

    def add(self, abs_time: AbsTime, item: T):
        self.items.add(Pair(key=abs_time, item=item))

    def value_at(self, abs_time: AbsTime) -> T:
        idx = self.items.bisect_left(Pair(key=abs_time, item=None)) - 1
        if idx < 0:
            raise ValueError("Not found")
        return self.items[idx].item

    def ranges(self, add_end: bool = True) -> List[Tuple[AbsTime, AbsTime, T]]:
        items = list(self.items)
        if not items:
            return []

        if add_end:
            items.append(
                Pair(
                    # Ugly way to get us to the end of the last period
                    key=items[0].key + timedelta(seconds=10_000_000),
                    item=None,
                )
            )

        if len(items) < 2:
            raise ValueError("Cannot create ranges when length < 2")

        ranges_ = []
        for start_pair, end_pair in zip(items[:-1], items[1:]):
            ranges_.append((start_pair.key, end_pair.key, start_pair.item))
        return ranges_
