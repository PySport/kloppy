from typing import IO, List, Optional, Tuple

from lxml import objectify

from kloppy.domain import Period, Team

from .metadata.base import TracabMetadataParser
from .metadata.flat_xml import TracabFlatXMLMetadataParser
from .metadata.hierarchical_xml import TracabHierarchicalXMLMetadataParser
from .metadata.json import TracabJSONMetadataParser
from .raw_data.base import TracabDataParser
from .raw_data.dat import TracabDatParser
from .raw_data.json import TracabJSONParser


def get_metadata_parser(
    feed: IO[bytes], feed_format: Optional[str] = None
) -> TracabMetadataParser:
    # infer the data format if not provided
    if feed_format is None:
        if feed.read(1).decode("utf-8")[0] == "<":
            feed.seek(0)
            meta_data = objectify.fromstring(feed.read())
            if hasattr(meta_data, "match"):
                feed_format = "HIERARCHICAL_XML"
            else:
                feed_format = "FLAT_XML"
        else:
            feed_format = "JSON"
        feed.seek(0)

    if feed_format.upper() == "JSON":
        return TracabJSONMetadataParser(feed)
    elif feed_format.upper() == "FLAT_XML":
        return TracabFlatXMLMetadataParser(feed)
    elif feed_format.upper() == "HIERARCHICAL_XML":
        return TracabHierarchicalXMLMetadataParser(feed)
    else:
        raise ValueError(f"Unknown metadata feed format {feed_format}")


def get_raw_data_parser(
    feed: IO[bytes],
    periods: List[Period],
    teams: Tuple[Team, Team],
    frame_rate: int,
    feed_format: Optional[str] = None,
) -> TracabDataParser:
    # infer the data format if not provided
    if feed_format is None:
        if feed.read(1).decode("utf-8")[0] == "{":
            feed_format = "JSON"
        else:
            feed_format = "DAT"
        feed.seek(0)

    if feed_format.upper() == "DAT":
        return TracabDatParser(feed, periods, teams, frame_rate)
    elif feed_format.upper() == "JSON":
        return TracabJSONParser(feed, periods, teams, frame_rate)
    else:
        raise ValueError(f"Unknown raw data feed format {feed_format}")
