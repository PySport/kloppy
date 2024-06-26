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
    Literal,
)

from sortedcontainers import SortedDict

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
    def start_time(self) -> "Time":
        return Time(period=self, timestamp=timedelta(0))

    @property
    def end_time(self) -> "Time":
        return Time(
            period=self, timestamp=self.end_timestamp - self.start_timestamp
        )

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
class Time:
    period: "Period"
    timestamp: timedelta

    @classmethod
    def from_period(
        cls,
        period: Period,
        type_: Union[Literal["start"], Literal["end"]] = "start",
    ):
        return cls(
            period=period,
            timestamp=timedelta(0) if type_ == "start" else period.duration,
        )

    @overload
    def __sub__(self, other: timedelta) -> "Time":
        ...

    @overload
    def __sub__(self, other: "Time") -> timedelta:
        ...

    def __sub__(
        self, other: Union["Time", timedelta]
    ) -> Union["Time", timedelta]:
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
                    return Time(period=current_period, timestamp=timedelta(0))

                current_period = current_period.prev_period
                current_timestamp = current_period.duration

            return Time(
                period=current_period, timestamp=current_timestamp - other
            )

        elif isinstance(other, Time):
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

    def __add__(self, other: timedelta) -> "Time":
        assert isinstance(other, timedelta)
        current_timestamp = self.timestamp
        current_period = self.period
        while (current_timestamp + other) > current_period.duration:
            # Subtract time left in this period

            other -= current_period.duration - current_timestamp
            if not current_period.next_period:
                # We reached start of the match, lets just return start itself
                return Time(
                    period=current_period, timestamp=current_period.duration
                )

            current_period = current_period.next_period
            current_timestamp = timedelta(0)

        return Time(period=current_period, timestamp=current_timestamp + other)

    def __radd__(self, other: timedelta) -> "Time":
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

    def __hash__(self):
        return hash((self.period.id, self.timestamp.total_seconds()))


SENTINEL = object()

T = TypeVar("T")


class TimeContainer(Generic[T]):
    def __init__(self):
        self.items: SortedDict = SortedDict()

    def set(self, time: Time, item: Optional[T]):
        self.items[time] = item  # Pair(key=time, item=item)

    def value_at(self, time: Time) -> Optional[T]:
        idx = self.items.bisect_right(time) - 1
        if idx < 0:
            raise KeyError("Not found")
        return self.items.values()[idx]

    def __getitem__(self, item: Time):
        return self.value_at(item)

    def __setitem__(self, key: Time, value: Optional[T]):
        self.set(key, value)

    def ranges(self) -> List[Tuple[Time, Time, T]]:
        items = list(self.items)
        if not items:
            return []

        # When last item isn't None (meaning 'end'), make sure to add it
        if self.items[items[-1]] is not None:
            current_period = items[0].period
            while current_period.next_period:
                current_period = current_period.next_period
            items.append(current_period.end_time)

        if len(items) < 2:
            raise ValueError("Cannot create ranges when length < 2")

        ranges_ = []
        for start_time, end_time in zip(items[:-1], items[1:]):
            ranges_.append((start_time, end_time, self.items[start_time]))
        return ranges_

    def last(self, include_time: bool = False, default=SENTINEL):
        if not len(self.items):
            if default == SENTINEL:
                raise KeyError
            else:
                return default

        time = self.items.keys()[-1]
        if include_time:
            return time, self.items[time]
        else:
            return self.items[time]

    def at_start(self):
        """Return the value at the beginning of the match"""
        if not self.items:
            raise KeyError

        first_item: Time = self.items.keys()[0]

        tmp_period = first_item.period
        while tmp_period.prev_period:
            tmp_period = tmp_period.prev_period

        return self.value_at(Time.from_period(tmp_period, "start"))

    def __repr__(self):
        if not self.items:
            return "<TimeContainer>"

        item_type = type(self.items.values()[0]).__name__
        str_items = {str(key): value for key, value in self.items.items()}
        return f"TimeContainer[{item_type}]({str_items})"
