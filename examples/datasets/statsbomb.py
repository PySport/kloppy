from kloppy import datasets


def main():
    """
        This example shows the use of Statsbomb datasets, and how we can pass argument
        to the dataset loader.
    """

    data_set = datasets.load("statsbomb")


if __name__ == "__main__":
    main()
