from kloppy import datasets


def main():
    """
        This example shows the use of Metrica datasets, and how we can pass argument
        to the dataset loader.
    """

    # The metrica dataset loader loads by default the 'game1' dataset
    data_set = datasets.load("metrica_tracking", options={'sample_rate': 1./12, 'limit': 10})
    print(len(data_set.frames))

    # We can pass additional keyword arguments to the loaders to specify a different dataset
    data_set = datasets.load("metrica_tracking", options={'sample_rate': 1, 'limit': 10}, game='game2')
    print(len(data_set.frames))


if __name__ == "__main__":
    main()
