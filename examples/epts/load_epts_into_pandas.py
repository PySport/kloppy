import logging
import sys

from pandas import DataFrame

from kloppy.infra.serializers.tracking.metrica_epts.metadata import (
    load_metadata as epts_load_metadata,
)
from kloppy.infra.serializers.tracking.epts.reader import (
    read_raw_data as epts_read_raw_data,
)


def main():
    """
    This example will show how to load data from EPTS files directly into a pandas frame using
    some internals, which allows us to read other sensors than the position sensor.

    We include 4 steps in this example:
    1. Loading the meta data from the XML fil
    2. Trying to load the raw data from a single sensor and discover what consequences the
       usage of generators are.
    3. Find out how we can iterate over the records and show what's in such a record
    4. Try to consume items from generator twice
    4. Convert the records into a pandas dataframe for easy data mangling
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # step 1: load metadata
    with open("epts_meta.xml", "rb") as meta_fp:
        metadata = epts_load_metadata(meta_fp)

    # step 2: try to load the raw data
    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(
            raw_fp, metadata, sensor_ids=["heartbeat"]
        )
    # raw_fp is closed here

    try:
        for record in records:
            print(record)
    except ValueError as e:
        print(f"Whoops, an error occured: {e}")
        # Why did this happen? Well.. `records` is a generator. A generator is a 'lazy list' which will produce
        # results when we ask for it (when we loop over the items). The `epts_read_raw_data` generator will
        # in its turn only consume data from `raw_fp` when we ask for new records.
        # So as long as we don't consume items from `records` no data is consumed from `raw_fp`. Performance wise
        # this is great! We don't load all data in memory.
        # But this also means `raw_fp` needs to be consumable (file may not be closed) before we consume
        # all items from `records`.

    # step 3: this works
    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(
            raw_fp, metadata, sensor_ids=["heartbeat"]
        )
        # consume all records before we close `raw_fp`
        for record in records:
            print(record)

    # step 4: re-use a generator
    data_frame = DataFrame.from_records(records)
    print(data_frame.head())
    # Empty dataframe? Wut? Well.. a generator can be consumed only once. The for loop above already consumed
    # all the items.

    # step 5: put the records in a pandas dataframe
    with open("epts_raw.txt", "rb") as raw_fp:
        # we are only interested in the data from the 'heartbeat' sensor
        records = epts_read_raw_data(
            raw_fp, metadata, sensor_ids=["heartbeat"]
        )
        data_frame = DataFrame.from_records(records)

    # Pfieh.. data. That's better :-)
    print(data_frame.head())


if __name__ == "__main__":
    main()
