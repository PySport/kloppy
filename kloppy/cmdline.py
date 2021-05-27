import argparse
import logging
import sys
import textwrap
from collections import Counter

from kloppy import (
    load_opta_event_data,
    load_statsbomb_event_data,
    load_wyscout_event_data,
    write_xml_code_data,
    event_pattern_matching as pm,
)
from kloppy.domain import CodeDataset, Code
from kloppy.utils import performance_logging

sys.path.append(".")


def _format_time(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02.0f}:{seconds:02.0f}"


def print_match(id_: int, match, success: bool, label):
    print(f"Match {id_}: {label} {'SUCCESS' if success else 'no-success'}")
    for event in match.events:
        time = _format_time(event.timestamp)
        print(
            f"{event.event_id} {event.event_type} {str(event.result).ljust(10)} / P{event.period.id} {time} / {event.team} {str(event.player.jersey_no).rjust(2)} / {event.coordinates.x}x{event.coordinates.y}"
        )
    print("")


def load_query(query_file: str) -> pm.Query:
    locals_dict = {}
    with open(query_file, "rb") as fp:
        exec(fp.read(), {}, locals_dict)

    if "query" not in locals_dict:
        raise Exception("File does not contain query")
    return locals_dict["query"]


def run_query(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Run query on event data")
    parser.add_argument(
        "--input-statsbomb",
        help="StatsBomb event input files (events.json,lineup.json)",
    )
    parser.add_argument(
        "--input-opta", help="Opta event input files (f24.xml,f7.xml)"
    )
    parser.add_argument("--input-wyscout", help="Wyscout event input file")
    parser.add_argument("--output-xml", help="Output file")
    parser.add_argument(
        "--with-success",
        default=True,
        help="Input existence of success capture in output",
    )
    parser.add_argument(
        "--prepend-time", default=7, help="Seconds to prepend to match"
    )
    parser.add_argument(
        "--append-time", default=5, help="Seconds to append to match"
    )
    parser.add_argument(
        "--query-file", help="File containing the query", required=True
    )
    parser.add_argument(
        "--stats",
        default="none",
        help="Show matches stats",
        choices=["text", "json", "none"],
    )
    parser.add_argument(
        "--show-events",
        default=False,
        help="Show events for each match",
        action="store_true",
    )
    parser.add_argument(
        "--only-success",
        default=False,
        help="Only show/output success cases",
        action="store_true",
    )

    logger = logging.getLogger("run_query")
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    opts = parser.parse_args(argv)

    query = load_query(opts.query_file)

    dataset = None
    if opts.input_statsbomb:
        with performance_logging("load dataset", logger=logger):
            events_filename, lineup_filename = opts.input_statsbomb.split(",")
            dataset = load_statsbomb_event_data(
                events_filename.strip(),
                lineup_filename.strip(),
                options={"event_types": query.event_types},
            )
    if opts.input_opta:
        with performance_logging("load dataset", logger=logger):
            f24_filename, f7_filename = opts.input_opta.split(",")
            dataset = load_opta_event_data(
                f24_filename.strip(),
                f7_filename.strip(),
                options={"event_types": query.event_types},
            )
    if opts.input_wyscout:
        with performance_logging("load dataset", logger=logger):
            events_filename = opts.input_wyscout
            dataset = load_wyscout_event_data(
                events_filename,
                options={"event_types": query.event_types},
            )

    if not dataset:
        raise Exception("You have to specify a dataset.")

    with performance_logging("searching", logger=logger):
        matches = pm.search(dataset, query.pattern)

    # Construct new code dataset with same properties (eg periods)
    # as original event dataset.
    # Records will be added later below
    code_dataset = CodeDataset(metadata=dataset.metadata, records=[])

    counter = Counter()
    for i, match in enumerate(matches):
        team = match.events[0].team
        success = "success" in match.captures

        counter.update(
            {
                f"{team.ground}_total": 1,
                f"{team.ground}_success": 1 if success else 0,
            }
        )

        should_process = not opts.only_success or success
        if opts.show_events and should_process:
            print_match(i, match, success, str(team))

        if opts.output_xml and should_process:
            code_ = str(team)
            if opts.with_success and success:
                code_ += " success"

            code = Code(
                period=match.events[0].period,
                code_id=str(i),
                code=code_,
                timestamp=match.events[0].timestamp - opts.prepend_time,
                end_timestamp=match.events[-1].timestamp + opts.append_time,
                # TODO: refactor those two out
                ball_state=None,
                ball_owning_team=None,
            )
            code_dataset.records.append(code)

    if opts.output_xml:
        write_xml_code_data(code_dataset, opts.output_xml)
        logger.info(f"Wrote {len(code_dataset.codes)} video fragments to file")

    if opts.stats == "text":
        text_stats = """\
        Home:
          total count: {home_total}
            success: {home_success} ({home_success_rate:.0f}%)
            no success: {home_failure} ({home_failure_rate:.0f}%)

        Away:
          total count: {away_total}
            success: {away_success} ({away_success_rate:.0f}%)
            no success: {away_failure} ({away_failure_rate:.0f}%)
        """.format(
            home_total=counter["home_total"],
            home_success=counter["home_success"],
            home_success_rate=(
                counter["home_success"] / counter["home_total"] * 100
            ),
            home_failure=counter["home_total"] - counter["home_success"],
            home_failure_rate=(
                (counter["home_total"] - counter["home_success"])
                / counter["home_total"]
                * 100
            ),
            away_total=counter["away_total"],
            away_success=counter["away_success"],
            away_success_rate=(
                counter["away_success"] / counter["away_total"] * 100
            ),
            away_failure=counter["away_total"] - counter["away_success"],
            away_failure_rate=(
                (counter["away_total"] - counter["away_success"])
                / counter["away_total"]
                * 100
            ),
        )
        print(textwrap.dedent(text_stats))
    elif opts.stats == "json":
        import json

        print(json.dumps(counter, indent=4))
