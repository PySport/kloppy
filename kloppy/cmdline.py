import argparse
import sys
import os
import importlib

from kloppy import load_statsbomb_event_data, event_pattern_matching as pm

sys.path.append(".")


def load_query(query_file: str) -> pm.Query:
    file_name, _ = os.path.splitext(query_file)
    module = importlib.import_module(file_name, ".")
    return module.query


def run_query(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Run query on event data")
    parser.add_argument('--statsbomb', help="StatsBomb event input files (events.json,lineup.json)")
    parser.add_argument('--output', default="stdout", help="Output file")
    parser.add_argument('--with-success', default=True, help="Input existence of success capture in output")
    parser.add_argument('--prepend-time', default=7, help="Seconds to prepend to match")
    parser.add_argument('--append-time', default=5, help="Seconds to append to match")
    parser.add_argument('--query-file', help="File containing the query", required=True)

    opts = parser.parse_args(argv)

    query = load_query(opts.query_file)

    dataset = None
    if opts.statsbomb:
        events_filename, lineup_filename = opts.statsbomb.split(",")
        dataset = load_statsbomb_event_data(
            events_filename.strip(),
            lineup_filename.strip(),
            options={
                "event_types": query.event_types
            }
        )

    if not dataset:
        raise Exception("You have to specify a dataset.")

    matches = pm.search(dataset, query.pattern)
    for match in matches:
        success = 'success' in match.captures
        label = str(match.events[0].team)
        if opts.with_success and success:
            label += " success"

        start_timestamp = (
            match.events[0].timestamp +
            match.events[0].period.start_timestamp +
            opts.prepend_time
        )
        end_timestamp = (
            match.events[-1].timestamp +
            match.events[-1].period.start_timestamp +
            opts.append_time
        )

        print(start_timestamp, end_timestamp, label)




if __name__ == "__main__":
    run_query()
