import os

from kloppy import statsbomb


class TestIssue171:
    def test_determine_statsbomb_home_away_teams(self):
        base_dir = os.path.dirname(__file__)

        dataset = statsbomb.load(
            event_data=f"{base_dir}/../files/statsbomb_3788741_event.json",
            lineup_data=f"{base_dir}/../files/statsbomb_3788741_lineup.json",
            coordinates="statsbomb",
        )

        assert dataset.metadata.teams[0].name == "Turkey"
