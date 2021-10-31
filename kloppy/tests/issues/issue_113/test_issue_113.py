import os

from kloppy.domain import Transformer, Orientation, AttackingDirection
from kloppy import OptaSerializer, to_pandas


def kloppy_load_data(f7, f24):
    """

    Args:
        f7: filepath to the match details
        f24: filepath to the event details


    Returns:
        events: DataFrame consisting of all events
        home_team_id: id of the home team
        away_team_id: id of the away team

    """
    serializer = OptaSerializer()
    with open(f24, "rb") as f24_data, open(f7, "rb") as f7_data:
        dataset = serializer.deserialize(
            inputs={"f24_data": f24_data, "f7_data": f7_data}
        )
    dataset = Transformer.transform_dataset(
        dataset, to_orientation=Orientation.FIXED_HOME_AWAY
    )

    events = to_pandas(
        dataset,
        additional_columns={
            "event_name": lambda event: str(getattr(event, "event_name", "")),
            "player_name": lambda event: str(getattr(event, "player", "")),
            "ball_state": lambda event: str(getattr(event, "ball_state", "")),
            "team_name": lambda event: str(getattr(event, "team", "")),
        },
    )

    metadata = dataset.metadata
    home_team, away_team = metadata.teams
    return events, home_team.team_id, away_team.team_id


class TestIssue113:
    def test_parse_opta(self):
        dir_path = os.path.dirname(__file__)
        kloppy_load_data(
            f7=f"{dir_path}/opta_f7.xml",
            f24=f"{dir_path}/opta_f24.xml",
        )
