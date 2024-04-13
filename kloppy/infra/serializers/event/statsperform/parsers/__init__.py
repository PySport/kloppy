from typing import IO, Optional

from .base import OptaParser, OptaEvent
from .f7_xml import F7XMLParser
from .f24_xml import F24XMLParser
from .ma1_json import MA1JSONParser
from .ma1_xml import MA1XMLParser
from .ma3_json import MA3JSONParser
from .ma3_xml import MA3XMLParser


def get_parser(
    feed: IO[bytes],
    feed_code: str,
    feed_format: Optional[str] = None,
    **kwargs,
) -> OptaParser:
    # infer the data format if not provided
    if feed_format is None:
        if feed.peek().decode("utf-8")[0] == "<":
            feed_format = "XML"
        else:
            feed_format = "JSON"

    # select the appropriate parser
    feed_code = feed_code.upper()
    feed_format = feed_format.upper()
    if feed_code == "F24" and feed_format == "XML":
        return F24XMLParser(feed)
    elif feed_code == "F7" and feed_format == "XML":
        return F7XMLParser(feed)
    elif feed_code == "MA1" and feed_format == "JSON":
        return MA1JSONParser(feed)
    elif feed_code == "MA1" and feed_format == "XML":
        return MA1XMLParser(feed)
    elif feed_code == "MA3" and feed_format == "JSON":
        return MA3JSONParser(feed)
    elif feed_code == "MA3" and feed_format == "XML":
        return MA3XMLParser(feed)
    else:
        raise NotImplementedError(
            f"A parser for {feed_code} ({feed_format}) feeds is not yet implemented."
        )


__all__ = ["get_parser", "OptaParser", "OptaEvent"]
