from kloppy import datasets, to_pandas


def main():
    """
        This example shows the use of Metrica datasets, and how we can pass argument
        to the dataset loader.
    """

    # The metrica dataset loader loads by default the 'game1' dataset
    data_set = datasets.load("metrica_tracking", options={'sample_rate': 1./12, 'limit': 10})
    print(len(data_set.frames))

    # We can pass additional keyword arguments to the loaders to specify a different dataset
    data_set = datasets.load("metrica_tracking", options={'limit': 1000}, game='game2')

    data_frame = to_pandas(data_set)
    print(data_frame)


if __name__ == "__main__":
    main()
