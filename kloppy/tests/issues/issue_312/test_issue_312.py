from kloppy import statsbomb


class TestIssue312:
    def test_create_periods(self, base_dir):
        dataset = statsbomb.load(
            event_data=base_dir / "issues/issue_312/statsbomb_event.json",
            lineup_data=base_dir / "issues/issue_312/statsbomb_lineup.json",
            coordinates="statsbomb",
        )

        assert len(dataset.metadata.periods) == 2
