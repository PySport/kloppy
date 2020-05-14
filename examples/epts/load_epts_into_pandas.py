from pandas import DataFrame

from kloppy import epts_load_meta_data, epts_read_raw_data


def main():
    """
    This example will show how to load data from EPTS files directly into a pandas frame,
    while bypassing the (internal) structure kloppy uses to represent a dataset.
    """
    with open("epts_meta.xml", "rb") as meta_fp:
        meta_data = epts_load_meta_data(meta_fp)

    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(raw_fp, meta_data, sensor_ids=["heartbeat"])
    # raw_fp is closed here

    try:
        for record in records:
            print(record)
    except ValueError as e:
        print(f"Whoops, an error occured: {e}")

        # Why did this happen? Well.. records is a generator and it will start consuming data from
        # raw_fp in the for loop. In this example the file is already closed before we start
        # consuming.

    # this works:
    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(raw_fp, meta_data, sensor_ids=["heartbeat"])
        for record in records:
            print(record)


    # put records in a dataframe
    data_frame = DataFrame.from_records(records)
    print(data_frame.head())
    # Empty dataframe? Wut? Well.. a generator can be consumed only once. The for loop above already consumed its
    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(raw_fp, meta_data, sensor_ids=["heartbeat"])
        data_frame = DataFrame.from_records(records)

    # Pfieh.. data. That's better :-)
    print(data_frame.head())


if __name__ == "__main__":
    main()
