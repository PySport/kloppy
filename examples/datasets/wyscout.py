import logging
import sys

from kloppy import wyscout
from kloppy.utils import performance_logging


def main():
    """
    This example shows the use of Wyscout datasets, and how we can pass argument
    to the dataset loader.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # The wyscout dataset loader loads by default the '2499841' dataset
    dataset = wyscout.load_open_data()
    print(len(dataset.events))


if __name__ == "__main__":
    main()
