from typing import List
from lxml import etree

from cssselect import GenericTranslator

from kloppy.domain import Event, EventType


class CSSPatternMatcher:
    def __init__(self, pattern: str):
        self.expression = GenericTranslator().css_to_xpath([pattern])

    def match(self, events: List[Event]) -> List[List[Event]]:
        elm = etree.Element("start")
        root = elm
        for i, event in enumerate(events):
            if event.event_type != EventType.GENERIC:
                elm = etree.SubElement(
                    elm,
                    event.event_name.lower()
                    .replace(" ", "_")
                    .replace("*", ""),
                    index=i,
                    result=str(event.result).lower(),
                    team=str(event.team.ground).lower(),
                    attrib={
                        "class": str(event.result).lower()
                        + " "
                        + str(event.team.ground).lower()
                    },
                )

        matching_events = []
        for elm in root.xpath(self.expression):
            matching_events.append(events[elm.attrib["index"]])
        return matching_events
