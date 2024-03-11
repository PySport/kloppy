import logging
import sys

from kloppy import statsbomb
from kloppy.utils import performance_logging


def main():
    """
    This example shows the use of Statsbomb datasets, and how we can pass argument
    to the dataset loader.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    dataset = statsbomb.load_open_data(
        event_types=["pass", "take_on", "carry", "shot"]
    )

    with performance_logging("transform", logger=logger):
        # convert to TRACAB coordinates
        dataset = dataset.transform(
            to_orientation="STATIC_HOME_AWAY",
            to_pitch_dimensions=[(-5500, 5500), (-3300, 3300)],
        )

    with performance_logging("to pandas", logger=logger):
        dataframe = dataset.to_df()

    print(dataframe[:50].to_string())


if __name__ == "__main__":
    main()
