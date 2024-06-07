from dataclasses import dataclass, field
from datetime import timedelta, datetime
from typing import overload, Union, Optional

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
    def duration(self) -> timedelta:
        return self.end_timestamp - self.start_timestamp

    def __eq__(self, other):
        return isinstance(other, Period) and other.id == self.id

    def __lt__(self, other: 'Period'):
        return self.id < other.id

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
    period: 'Period'
    timestamp: timedelta

    @overload
    def __sub__(self, other: timedelta) -> 'AbsTime':
        ...

    @overload
    def __sub__(self, other: 'AbsTime') -> timedelta:
        ...

    def __sub__(self, other: Union['AbsTime', timedelta]) -> Union['AbsTime', timedelta]:
        """
        Subtract a timedelta or AbsTime from the current AbsTime.

        AbsTime - AbsTime = timedelta
        AbsTime - timedelta = AbsTime

        The period duration must be taking into account.
        """
        if isinstance(other, timedelta):
            pass
        elif isinstance(other, AbsTime):
            pass
        else:
            raise ValueError(f'Cannot subtract {other}')

    def __add__(self, other: timedelta) -> 'AbsTime':
        assert isinstance(other, timedelta)
        return self.__sub__(-other)

    def __radd__(self, other: timedelta) -> 'AbsTime':
        assert isinstance(other, timedelta)
        return self.__add__(other)

    def __rsub__(self, other):
        raise RuntimeError("Doesn't make sense.")