import argparse
import sys
import logging
from dataclasses import dataclass
from typing import List

from xml.etree import ElementTree as ET

from kloppy import load_statsbomb_event_data, event_pattern_matching as pm
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

    tree.write(filename,
               xml_declaration=True,
               encoding='utf-8',
               method="xml")


def load_query(query_file: str) -> pm.Query:
    locals_dict = {}
    with open(query_file, "rb") as fp:
        exec(fp.read(), {}, locals_dict)

    if 'query' not in locals_dict:
        raise Exception("File does not contain query")
    return locals_dict['query']


def run_query(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Run query on event data")
    parser.add_argument('--input-statsbomb', help="StatsBomb event input files (events.json,lineup.json)")
    parser.add_argument('--output-xml', help="Output file", required=True)
    parser.add_argument('--with-success', default=True, help="Input existence of success capture in output")
    parser.add_argument('--prepend-time', default=7, help="Seconds to prepend to match")
    parser.add_argument('--append-time', default=5, help="Seconds to append to match")
    parser.add_argument('--query-file', help="File containing the query", required=True)

    logger = logging.getLogger("run_query")
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    opts = parser.parse_args(argv)

    query = load_query(opts.query_file)

    dataset = None
    if opts.input_statsbomb:
        with performance_logging("load dataset", logger=logger):
            events_filename, lineup_filename = opts.input_statsbomb.split(",")
            dataset = load_statsbomb_event_data(
                events_filename.strip(),
                lineup_filename.strip(),
                options={
                    "event_types": query.event_types
                }
            )

    if not dataset:
        raise Exception("You have to specify a dataset.")

    with performance_logging("searching", logger=logger):
        matches = pm.search(dataset, query.pattern)

    video_fragments = []
    for i, match in enumerate(matches):
        success = 'success' in match.captures
        label = str(match.events[0].team)
        if opts.with_success and success:
            label += " success"

        start_timestamp = (
            match.events[0].timestamp +
            match.events[0].period.start_timestamp -
            opts.prepend_time
        )
        end_timestamp = (
            match.events[-1].timestamp +
            match.events[-1].period.start_timestamp +
            opts.append_time
        )

        video_fragments.append(
            VideoFragment(
                id_=str(i),
                start=start_timestamp,
                end=end_timestamp,
                label=label
            )
        )

    if opts.output_xml:
        write_to_xml(video_fragments, opts.output_xml)
        logger.info(f"Wrote {len(video_fragments)} video fragments to file")
