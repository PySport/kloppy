import re
from dataclasses import dataclass
from typing import Callable, List

from kloppy import datasets, to_pandas
from kloppy.domain import Event, EventDataset
from kloppy.utils import performance_logging


@dataclass
class IndexEntry:
    start_pos: int
    end_pos: int
    event: Event


class Matcher:
    def __init__(self, encoder: Callable[[Event], str]):
        self.encoder = encoder

    def search(self, dataset: EventDataset, pattern: str) -> List[List[Event]]:
        # Step 1: encode events and build index
        index = []
        encoded_str = ""
        for event in dataset.events:
            encoded_event = self.encoder(event)
            if not encoded_event:
                continue

            current_pos = len(encoded_str)
            index_entry = IndexEntry(
                start_pos=current_pos,
                end_pos=current_pos + len(encoded_event),
                event=event,
            )
            index.append(index_entry)

            encoded_str += encoded_event

        # Step 2: Search using regular expression
        results = re.finditer(pattern, encoded_str)

        # Step 3: Decode back to match (List of Events)
        matches = []
        index_pos = 0
        index_length = len(index)
        for result in results:
            start_pos, end_pos = result.span()

            match = []
            for i in range(index_pos, index_length):
                index_entry = index[i]

                if index_entry.start_pos >= end_pos:
                    index_pos = i
                    break
                elif index_entry.start_pos >= start_pos:
                    match.append(index_entry.event)

            matches.append(match)

        return matches


def encoder(event: Event):
    if event.event_name == "pass":
        return "P"
    elif event.event_name == "shot":
        return "S"


def main():
    import pandas as pd

    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 2000)

    matcher = Matcher(encoder)

    dataset = datasets.load(
        "statsbomb", options={"event_types": ["shot", "pass"]}
    )

    with performance_logging("search"):
        matches = matcher.search(dataset, r"PPS")

    df = to_pandas(
        dataset,
        additional_columns={
            "player_name": lambda event: event.player.full_name,
            "team_name": lambda event: str(event.team),
        },
    )
    print(
        df[["timestamp", "team_name", "player_name", "event_type", "result"]][
            :100
        ]
    )
    return

    for i, match in enumerate(matches):
        df = to_pandas(
            dataset,
            additional_columns={
                "player_name": lambda event: event.player.full_name,
                "team_name": lambda event: str(event.team),
            },
        )
        print(
            df[
                [
                    "period_id",
                    "timestamp",
                    "team_name",
                    "player_name",
                    "event_type",
                ]
            ]
        )


if __name__ == "__main__":
    main()
