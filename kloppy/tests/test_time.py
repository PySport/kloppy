from datetime import timedelta
from typing import Tuple

import pytest

from kloppy import statsbomb
from kloppy.domain import AbsTime, Period, AbsTimeContainer


@pytest.fixture
def periods() -> Tuple[Period, Period, Period]:
    period1 = Period(
        id=1,
        start_timestamp=timedelta(seconds=0),
        end_timestamp=timedelta(seconds=2700),
    )
    period2 = Period(
        id=2,
        start_timestamp=timedelta(seconds=0),
        end_timestamp=timedelta(seconds=3000),
    )
    period3 = Period(
        id=3,
        start_timestamp=timedelta(seconds=0),
        end_timestamp=timedelta(seconds=1000),
    )
    period1.set_refs(None, period2)
    period2.set_refs(period1, period3)
    period3.set_refs(period2, None)
    return period1, period2, period3


class TestAbsTime:
    def test_subtract_timedelta_same_period(self, periods):
        """Test subtract with non-period overlapping timedelta."""
        period1, *_ = periods

        abs_time = AbsTime(period=period1, timestamp=timedelta(seconds=1800))

        assert abs_time - timedelta(seconds=1000) == AbsTime(
            period=period1, timestamp=timedelta(seconds=800)
        )

    def test_subtract_timedelta_spans_periods(self, periods):
        """Test subtract that goes over spans multiple period.


        +-------+-------+------+
        | 2700  | 3000  | 1000 |
        +-------+-------+------+
                           ^ 800

        In period 3:  800 -   3200 left -    0
        In period 2: 3000 -    200 left -    0
        In period 1:  200 -      0 left - 2500
        """
        period1, period2, period3 = periods

        abs_time = AbsTime(period=period3, timestamp=timedelta(seconds=800))

        assert abs_time - timedelta(seconds=4000) == AbsTime(
            period=period1, timestamp=timedelta(seconds=2500)
        )

    def test_subtract_timedelta_over_start(self, periods):
        """Test subtract that goes over start of first period. This should return start of match."""
        period1, *_ = periods

        abs_time = AbsTime(period=period1, timestamp=timedelta(seconds=1800))

        assert abs_time - timedelta(seconds=2000) == AbsTime(
            period=period1, timestamp=timedelta(0)
        )

    def test_subtract_two_abstime(self, periods):
        """Subtract two AbsTime in same period"""
        period1, *_ = periods
        abs_time1 = AbsTime(period=period1, timestamp=timedelta(seconds=1000))
        abs_time2 = AbsTime(period=period1, timestamp=timedelta(seconds=800))

        assert abs_time1 - abs_time2 == timedelta(seconds=200)

    def test_subtract_two_abstime_spans_periods(self, periods):
        """Subtract AbsTime over multiple periods."""
        period1, period2, period3 = periods
        abs_time1 = AbsTime(period=period1, timestamp=timedelta(seconds=800))
        abs_time2 = AbsTime(period=period2, timestamp=timedelta(seconds=800))

        assert abs_time2 - abs_time1 == timedelta(seconds=2700)

    def test_add_timedelta_same_period(self, periods):
        """Test add timedelta in same period"""
        period1, *_ = periods

        abs_time = AbsTime(period=period1, timestamp=timedelta(seconds=800))
        assert abs_time + timedelta(seconds=100) == AbsTime(
            period=period1, timestamp=timedelta(seconds=900)
        )

    def test_add_timedelta_spans_periods(self, periods):
        """
        +-------+-------+------+
        | 2700  | 3000  | 1000 |
        +-------+-------+------+
           ^ 800

        In period 3:  1900 -   3100 left
        In period 2:  3000 -    100 left
        In period 1:   100 -      0 left
        """
        period1, period2, period3 = periods

        abs_time = AbsTime(period=period1, timestamp=timedelta(seconds=800))
        assert abs_time + timedelta(seconds=5000) == AbsTime(
            period=period3, timestamp=timedelta(seconds=100)
        )

        assert abs_time + timedelta(seconds=2600) == AbsTime(
            period=period2, timestamp=timedelta(seconds=700)
        )

    def test_statsbomb(self, base_dir):
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )
        formation_changes = dataset.filter("formation_change")

        # Determine time until first formation change
        diff = (
            formation_changes[0].abs_time
            - dataset.metadata.periods[0].start_abs_time
        )
        assert diff == timedelta(seconds=2705.267)

        # Time until last formation change
        diff = (
            formation_changes[-1].abs_time
            - dataset.metadata.periods[0].start_abs_time
        )
        assert diff == timedelta(seconds=5067.367)


class TestAbsTimeContainer:
    def test_value_at(self, periods):
        period1, *_ = periods

        abs_time1 = AbsTime(period=period1, timestamp=timedelta(seconds=800))
        container = AbsTimeContainer()
        container.add(abs_time1, 10)

        value = container.value_at(abs_time1 + timedelta(seconds=1))
        assert value == 10

        value = container.value_at(abs_time1 + timedelta(seconds=10000))
        assert value == 10

        with pytest.raises(ValueError):
            container.value_at(abs_time1 - timedelta(seconds=1))

    def test_ranges(self, periods):
        period1, period2, _ = periods

        abs_time1 = AbsTime(
            period=period1, timestamp=timedelta(seconds=60 * 15)
        )
        container = AbsTimeContainer()

        # Player gets on the pitch
        container.add(abs_time1, "LB")

        # Switches to RB
        container.add(abs_time1 + timedelta(seconds=2400), "RB")

        # Player gets of the pitch
        container.add(
            AbsTime(period=period2, timestamp=timedelta(seconds=60 * 20)), None
        )

        print("")
        for start, end, item in container.ranges(add_end=False):
            print(f"{start} - {end} = {end - start} -> {item}")
