from datetime import timedelta
from typing import Tuple

import pytest

from kloppy import statsbomb
from kloppy.domain import Time, Period, TimeContainer
from kloppy.domain.services.aggregators.minutes_played import BreakdownKey, PossessionState


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

        time = Time(period=period1, timestamp=timedelta(seconds=1800))

        assert time - timedelta(seconds=1000) == Time(
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

        time = Time(period=period3, timestamp=timedelta(seconds=800))

        assert time - timedelta(seconds=4000) == Time(
            period=period1, timestamp=timedelta(seconds=2500)
        )

    def test_subtract_timedelta_over_start(self, periods):
        """Test subtract that goes over start of first period. This should return start of match."""
        period1, *_ = periods

        time = Time(period=period1, timestamp=timedelta(seconds=1800))

        assert time - timedelta(seconds=2000) == Time(
            period=period1, timestamp=timedelta(0)
        )

    def test_subtract_two_abstime(self, periods):
        """Subtract two AbsTime in same period"""
        period1, *_ = periods
        time1 = Time(period=period1, timestamp=timedelta(seconds=1000))
        time2 = Time(period=period1, timestamp=timedelta(seconds=800))

        assert time1 - time2 == timedelta(seconds=200)

    def test_subtract_two_abstime_spans_periods(self, periods):
        """Subtract AbsTime over multiple periods."""
        period1, period2, period3 = periods
        time1 = Time(period=period1, timestamp=timedelta(seconds=800))
        time2 = Time(period=period2, timestamp=timedelta(seconds=800))

        assert time2 - time1 == timedelta(seconds=2700)

    def test_add_timedelta_same_period(self, periods):
        """Test add timedelta in same period"""
        period1, *_ = periods

        time = Time(period=period1, timestamp=timedelta(seconds=800))
        assert time + timedelta(seconds=100) == Time(
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

        time = Time(period=period1, timestamp=timedelta(seconds=800))
        assert time + timedelta(seconds=5000) == Time(
            period=period3, timestamp=timedelta(seconds=100)
        )

        assert time + timedelta(seconds=2600) == Time(
            period=period2, timestamp=timedelta(seconds=700)
        )

    def test_statsbomb_formation_changes(self, base_dir):
        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )
        formation_changes = dataset.filter("formation_change")

        # Determine time until first formation change
        diff = (
            formation_changes[0].time - dataset.metadata.periods[0].start_time
        )
        assert diff == timedelta(seconds=2705.267)

        # Time until last formation change
        diff = (
            formation_changes[-1].time - dataset.metadata.periods[0].start_time
        )
        assert diff == timedelta(seconds=5067.367)

    def test_statsbomb_minuted_played(self, base_dir):
        def __period_offset(period_id, dataset):
            for period in dataset.metadata.periods:
                if period.id == period_id - 1:
                    return period.end_time.timestamp.total_seconds()
                else:
                    return 0

        dataset = statsbomb.load(
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )

        minutes_played = dataset.aggregate("minutes_played")

        home_team, away_team = dataset.metadata.teams

        player_minutes_played_map = {
            item.key.player: item.duration for item in minutes_played if item.key.player
        }

        """
        3109 - 0:00:00.000000 - Malcom
        3501 - 0:47:32.053000 - Coutinho
        5203 - 1:24:12.343000 - Busquets
        5211 - 1:32:37.320000 - Ramos
        """

        # Didn't play
        player_malcon = home_team.get_player_by_id(3109)
        assert player_malcon not in player_minutes_played_map

        # Started second half
        player_coutinho = home_team.get_player_by_id(3501)
        assert player_minutes_played_map[player_coutinho] == timedelta(
            seconds=2852.053
        )

        # Replaced in second half
        player_busquets = home_team.get_player_by_id(5203)
        assert player_minutes_played_map[player_busquets] == timedelta(
            seconds=5052.343
        )

        # Played entire match
        player_ramos = home_team.get_player_by_id(5211)
        assert player_minutes_played_map[player_ramos] == (
            dataset.metadata.periods[0].duration
            + dataset.metadata.periods[1].duration
        )

        # Teams played entire match
        for item in minutes_played:
            if item.key.team:
                assert item.duration == (
                    dataset.metadata.periods[0].duration
                    + dataset.metadata.periods[1].duration
                )

        # Check if total difference between start and end time equal minutes played
        for item in minutes_played:
            assert item.duration.total_seconds() == pytest.approx(
                (
                    (
                        item.end_time.timestamp.total_seconds()
                        + __period_offset(
                            period_id=item.end_time.period.id, dataset=dataset
                        )
                    )
                    - (
                        item.start_time.timestamp.total_seconds()
                        + __period_offset(
                            period_id=item.start_time.period.id,
                            dataset=dataset,
                        )
                    )
                ),
                0.001,
            )
    def test_statsbomb_minutes_played_per_possession_state(self, base_dir):
        dataset = statsbomb.load(
            # 3788741
            # 15986
            lineup_data=base_dir / "files/statsbomb_lineup.json",
            event_data=base_dir / "files/statsbomb_event.json",
        )

        minutes_played_per_possession_state = dataset.aggregate("minutes_played", breakdown_key= BreakdownKey.POSSESSION_STATE)


        player_minutes_played_map = {}
        team_minutes_played_map = {}
        for item in minutes_played_per_possession_state:
            if item.key.team:
                team = item.key.team
                if team not in team_minutes_played_map:
                    team_minutes_played_map[team] = {}
                team_minutes_played_map[team][item.key.possession_state] = item.duration
            else:
                player = item.key.player
                possession_state = item.key.possession_state
                duration = item.duration

                if player and possession_state:
                    if player not in player_minutes_played_map:
                        player_minutes_played_map[player] = {}
                    player_minutes_played_map[player][possession_state] = duration


        

        # Teams played entire match
        for item in team_minutes_played_map.values():
            total_duration = sum(item.values(), timedelta())
            assert total_duration == (
                        dataset.metadata.periods[0].duration
                        + dataset.metadata.periods[1].duration
                )

        home_team, away_team = dataset.metadata.teams

        """
        3109 - 0:00:00.000000 - Malcom
        3501 - 0:47:32.053000 - Coutinho
        5203 - 1:24:12.343000 - Busquets
        5211 - 1:32:37.320000 - Ramos
        """
        # Didn't play
        player_malcon = home_team.get_player_by_id(3109)
        assert player_malcon not in player_minutes_played_map

        # Started second half
        player_coutinho = home_team.get_player_by_id(3501)
        playtime_coutinho = player_minutes_played_map[player_coutinho]
        assert sum(playtime_coutinho.values(), timedelta()) == timedelta(
            seconds=2852.053
        )
        assert playtime_coutinho[PossessionState.IN_POSSESSION] == timedelta(seconds=1505.312)
        assert playtime_coutinho[PossessionState.OUT_OF_POSSESSION] == timedelta(seconds=296.958)
        assert playtime_coutinho[PossessionState.BALL_DEAD] == timedelta(seconds=1049.783)


        # Replaced in second half
        player_busquets = home_team.get_player_by_id(5203)
        playtime_busquets = player_minutes_played_map[player_busquets]
        assert sum(playtime_busquets.values(), timedelta()) == timedelta(
            seconds=5052.343
        )
        assert playtime_busquets[PossessionState.IN_POSSESSION] == timedelta(seconds=2917.724)
        assert playtime_busquets[PossessionState.OUT_OF_POSSESSION] == timedelta(seconds=652.343)
        assert playtime_busquets[PossessionState.BALL_DEAD] == timedelta(seconds=1482.276)

        # Played entire match
        player_ramos = home_team.get_player_by_id(5211)
        playtime_ramos = player_minutes_played_map[player_ramos]
        assert sum(playtime_ramos.values(), timedelta()) == (
                dataset.metadata.periods[0].duration
                + dataset.metadata.periods[1].duration
        )
        assert playtime_ramos[PossessionState.IN_POSSESSION] == timedelta(seconds=3020.965)
        assert playtime_ramos[PossessionState.OUT_OF_POSSESSION] == timedelta(seconds=716.177)
        assert playtime_ramos[PossessionState.BALL_DEAD] == timedelta(seconds=1820.178)



class TestAbsTimeContainer:
    def test_value_at(self, periods):
        period1, *_ = periods

        time1 = Time(period=period1, timestamp=timedelta(seconds=800))
        container = TimeContainer()
        container[time1] = 10

        value = container.value_at(time1 + timedelta(seconds=1))
        assert value == 10

        value = container.value_at(time1 + timedelta(seconds=10000))
        assert value == 10

        with pytest.raises(KeyError):
            container.value_at(time1 - timedelta(seconds=1))

        assert repr(container) == "TimeContainer[int]({'P1T13:20': 10})"

    def test_ranges(self, periods):
        period1, period2, _ = periods

        container = TimeContainer()

        # Player gets on the pitch
        substitution_time = Time(
            period=period1, timestamp=timedelta(seconds=15 * 60)
        )
        container.set(substitution_time, "LB")

        # Switches from LB to RB
        container.set(substitution_time + timedelta(seconds=40 * 60), "RB")

        # Player gets of the pitch
        container.set(
            Time(period=period2, timestamp=timedelta(seconds=20 * 60)), None
        )

        for start, end, position in container.ranges():
            print(f"{start} - {end} = {end - start} -> {position}")

        assert container.last() is None
