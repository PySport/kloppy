import argparse
import sys
import logging
from collections import Counter
from dataclasses import dataclass
from typing import List

from xml.etree import ElementTree as ET

from kloppy import (
    load_statsbomb_event_data,
    load_opta_event_data,
    event_pattern_matching as pm,
)
from kloppy.infra.utils import performance_logging

sys.path.append(".")


@dataclass
class VideoFragment:
    id_: str
    label: str
    start: float
    end: float


def write_to_xml(video_fragments: List[VideoFragment], filename):
    root = ET.Element("file")
    instances = ET.SubElement(root, "ALL_INSTANCES")
    for video_fragment in video_fragments:
        instance = ET.SubElement(instances, "instance")

        instance_id = ET.SubElement(instance, "ID")
        instance_id.text = video_fragment.id_

        instance_code = ET.SubElement(instance, "code")
        instance_code.text = video_fragment.label

        instance_start = ET.SubElement(instance, "start")
        instance_start.text = str(max(0.0, video_fragment.start))

        instance_end = ET.SubElement(instance, "end")
        instance_end.text = str(video_fragment.end)

    tree = ET.ElementTree(root)

    tree.write(filename, xml_declaration=True, encoding="utf-8", method="xml")


def _format_time(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02.0f}:{seconds:02.0f}"


def print_match(id_: int, match, success: bool, label):
    print(f"Match {id_}: {label} {'SUCCESS' if success else 'no-success'}")
    for event in match.events:
        time = _format_time(event.timestamp)
        print(
            f"{event.event_id} {event.event_type} {str(event.result).ljust(10)} / P{event.period.id} {time} / {event.team} {str(event.player_jersey_no).rjust(2)} / {event.position.x}x{event.position.y}"
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
        "--input-opta", help="Opta event input files (f24.xml,f7.xml)",
    )
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

    if not dataset:
        raise Exception("You have to specify a dataset.")

    with performance_logging("searching", logger=logger):
        matches = pm.search(dataset, query.pattern)

    video_fragments = []
    counter = Counter()
    for i, match in enumerate(matches):
        team = match.events[0].team
        success = "success" in match.captures

        counter.update(
            {f"{team}_total": 1, f"{team}_success": 1 if success else 0}
        )

        should_process = not opts.only_success or success
        if opts.show_events and should_process:
            print_match(i, match, success, str(team))

        if opts.output_xml and should_process:
            relative_period_start = 0
            for period in dataset.periods:
                if period == match.events[0].period:
                    break
                else:
                    relative_period_start += period.duration

            label = str(team)
            if opts.with_success and success:
                label += " success"

            start_timestamp = (
                relative_period_start
                + match.events[0].timestamp
                - opts.prepend_time
            )
            end_timestamp = (
                relative_period_start
                + match.events[-1].timestamp
                + opts.append_time
            )

            video_fragments.append(
                VideoFragment(
                    id_=str(i),
                    start=start_timestamp,
                    end=end_timestamp,
                    label=label,
                )
            )

    if opts.output_xml:
        write_to_xml(video_fragments, opts.output_xml)
        logger.info(f"Wrote {len(video_fragments)} video fragments to file")

    if opts.stats == "text":
        print("Home:")
        print(f"  total count: {counter['home_total']}")
        print(
            f"    success: {counter['home_success']} ({counter['home_success'] / counter['home_total'] * 100:.0f}%)"
        )
        print(
            f"    no success: {counter['home_total'] - counter['home_success']} ({(counter['home_total'] - counter['home_success']) / counter['home_total'] * 100:.0f}%)"
        )
        print("")
        print("Away:")
        print(f"  total count: {counter['away_total']}")
        print(
            f"    success: {counter['away_success']} ({counter['away_success'] / counter['away_total'] * 100:.0f}%)"
        )
        print(
            f"    no success: {counter['away_total'] - counter['away_success']} ({(counter['away_total'] - counter['away_success']) / counter['away_total'] * 100:.0f}%)"
        )
    elif opts.stats == "json":
        import json

        print(json.dumps(counter, indent=4))
