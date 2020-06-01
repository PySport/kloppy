import logging
import sys

from kloppy import datasets, transform
from kloppy.infra.utils import performance_logging


def main():
    """
        This example shows the use of Statsbomb datasets, and how we can pass argument
        to the dataset loader.
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    data_set = datasets.load("statsbomb")
    with performance_logging("transform"):
        data_set = transform(data_set, to_orientation="FIXED_HOME_AWAY")
    a = 1


if __name__ == "__main__":
    main()
