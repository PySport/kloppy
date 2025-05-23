import logging
import sys
from collections import Counter

from kloppy import metrica
import matplotlib.pyplot as plt

from kloppy.domain import Ground


def main():
    """
    This example shows how to determine playing time
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    dataset = metrica.load_open_data(sample_rate=1.0 / 25)

    playing_seconds_per_player = Counter()
    for frame in dataset.frames:
        playing_seconds_per_player.update(
            [player.jersey_no for player in frame.players_coordinates.keys() if player.team.ground == Ground.HOME]
        )

    x = range(len(playing_seconds_per_player))
    jersey_numbers, playing_seconds = zip(*sorted(playing_seconds_per_player.items()))
    playing_minutes = [seconds / 60 for seconds in playing_seconds]

    plt.bar(x, playing_minutes, align="center", alpha=0.5)
    plt.xticks(x, jersey_numbers)
    plt.ylabel("Minutes")
    plt.title("Playing time per player")

    plt.show()


if __name__ == "__main__":
    main()
