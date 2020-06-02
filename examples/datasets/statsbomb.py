import logging
import sys

from kloppy import datasets, transform, to_pandas
from kloppy.infra.utils import performance_logging


def main():
    """
        This example shows the use of Statsbomb datasets, and how we can pass argument
        to the dataset loader.
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(__name__)

    dataset = datasets.load("statsbomb", {
        "event_types": ["pass", "take_on", "carry", "shot"]
    }, match_id=3749052) #16079)

    with performance_logging("transform", logger=logger):
        dataset = transform(dataset, to_orientation="FIXED_HOME_AWAY")

    with performance_logging("to pandas", logger=logger):
        dataframe = to_pandas(dataset)

    print(dataframe.head())


if __name__ == "__main__":
    main()
