import logging
import sys

from kloppy import metrica


def main():
    """
    This example shows the use of Metrica datasets, and how we can pass argument
    to the dataset loader.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # The metrica dataset loader loads by default the 'game1' dataset
    dataset = metrica.load_open_data(sample_rate=1.0 / 12, limit=10)
    print(len(dataset.frames))

    # We can pass additional keyword arguments to the loaders to specify a different dataset
    dataset = metrica.load_open_data(limit=1000, match_id="2")

    data_frame = dataset.to_pandas()
    print(data_frame)

    # Also load dataset in new metrica format
    dataset = metrica.load_open_data(limit=10_000, match_id="3")
    data_frame = dataset.to_pandas()
    df = data_frame[data_frame.ball_x.notnull()]
    print(df)


if __name__ == "__main__":
    main()
