from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import Callable, Tuple, Dict, List, Iterator

from kloppy.domain import (
    EventDataset,
    PassEvent,
    ShotEvent,
    CarryEvent,
    TakeOnEvent,
    Event,
)
from .regexp import *
from .regexp import _make_match, _TrailItem
from .regexp.regexp import _Match


class WithCaptureMatcher(Matcher):
    def __init__(self, matcher: Callable[[Tok, Dict[str, List[Tok]]], bool]):
        self.matcher = matcher

    def _add_captures(self, captures: Dict[str, List[Tok]], match: _Match):
        for name, capture in match.children.items():
            captures[name] = capture[0].trail
            self._add_captures(captures, capture[0])

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        match = _make_match(trail)
        captures = {}
        self._add_captures(captures, match)
        if self.matcher(token, captures):
            yield token


def match_generic(event_cls, capture=None, **kwargs):
    def _matcher_fn(event: Event, captures: Dict[str, List[Event]]) -> bool:
        if not isinstance(event, event_cls):
            return False

        # TODO: v[0] points to first record
        captures = {k: v[0] for k, v in captures.items()}
        for attr_name, attr_value in kwargs.items():
            if callable(attr_value):
                attr_real_value = getattr(event, attr_name)
                result = attr_value(attr_name, attr_real_value, captures)
            else:
                if attr_name == "success":
                    result = event.result and event.result.is_success
                else:
                    result = getattr(event, attr_name) == attr_value
            if not result:
                return False
        return True

    _matcher = Final(WithCaptureMatcher(matcher=_matcher_fn))

    if capture:
        return _matcher[capture]
    else:
        return _matcher


match_pass = partial(match_generic, PassEvent)
match_shot = partial(match_generic, ShotEvent)
match_carry = partial(match_generic, CarryEvent)
match_take_on = partial(match_generic, TakeOnEvent)
match_any = partial(match_generic, Event)


def same_as(capture: str):
    capture_name, attribute_name = capture.split(".")

    def fn(attr_name, value, captures):
        return value == getattr(captures[capture_name], attribute_name)

    return fn


def not_same_as(capture: str):
    capture_name, capture_attribute_name = capture.split(".")

    def fn(attr_name, value, captures):
        return value != getattr(captures[capture_name], capture_attribute_name)

    return fn


def group(node, capture=None):
    if capture:
        return node[capture]
    return node


def function(fn):
    def wrapper(attr_name, value, captures):
        capture_values = {
            f"{capture_name}_{attr_name}": getattr(capture_value, attr_name)
            for capture_name, capture_value in captures.items()
            if capture_value
        }
        return fn(value, **capture_values)

    return wrapper


@dataclass
class Match:
    events: List[Event]
    captures: Dict[str, List[Event]]


def search(dataset: EventDataset, pattern: Node[Tok, Out]):
    events = dataset.events
    re = RegExp.from_ast(pattern)

    results = []
    events_per_period = defaultdict(list)
    for event in events:
        events_per_period[event.period.id].append(event)

    for period, events_ in sorted(events_per_period.items()):
        # Search per period. Patterns should never match over periods
        results.extend(_search(events_, re))
    return results


def _search(events: List[Event], re: RegExp[Tok, Out]):
    i = 0
    results = []
    for i in range(len(events)):
        matches = re.match(events[i:], consume_all=False)
        if matches:
            results.append(
                Match(
                    events=matches[0].trail,
                    # TODO: check trail[0] because this points to the first event in the capture and not
                    #       all of them
                    captures={
                        capture_name: capture_value[0].trail[0]
                        for capture_name, capture_value in matches[
                            0
                        ].children.items()
                    },
                )
            )

    return results


@dataclass
class Query:
    event_types: List[str]
    pattern: Node[Tok, Out]


__all__ = [
    "search",
    "match_pass",
    "match_carry",
    "match_take_on",
    "match_shot",
    "match_any",
    "same_as",
    "not_same_as",
    "function",
    "Query",
]
