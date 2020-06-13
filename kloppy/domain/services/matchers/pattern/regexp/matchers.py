from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    Mapping,
    Sequence,
    Text,
    Tuple,
    TypeVar,
    Union,
    Dict,
)

if TYPE_CHECKING:
    from .ast import Final

# Tokens type
Tok = TypeVar("Tok")

# Output type
Out = TypeVar("Out")


@dataclass
class _TrailItem(Generic[Out]):
    """
    Internal intermediate object that will represent a step in the matching
    process along with the edge metadata.

    Let's just mention that the matched item is not the input token but the
    output of the matcher for this token.
    """

    item: Out
    data: Dict[Text, Sequence[Text]]

    @property
    def _comparable(self):
        """
        Returns a signature tuple that can be used for comparison
        """

        return self.item, tuple(sorted(self.data.items()))

    def __lt__(self, other):
        """
        Sortability for de-duplication purposes
        """

        if not isinstance(other, _TrailItem):
            raise TypeError

        return self._comparable < other._comparable


class Matcher(Generic[Tok, Out], metaclass=ABCMeta):
    @abstractmethod
    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        raise NotImplementedError


class Eq(Matcher):
    def __init__(self, ref: Tok):
        self.ref = ref

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if self.ref == token:
            yield token

    def __repr__(self):
        return f"Eq({self.ref!r})"


class In(Matcher):
    def __init__(self, ref: Sequence[Tok]):
        self.ref = ref

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if token in self.ref:
            yield token

    def __repr__(self):
        return f"In({self.ref!r})"


class OutOf(Matcher):
    def __init__(self, ref: Tok):
        self.ref = ref

    def __repr__(self):
        return f"OutOf({self.ref!r})"

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if self.ref in token:
            yield self.ref


class AttributeHasValue(Matcher):
    def __init__(self, attribute: Text, value: Any):
        self.attribute = attribute
        self.value = value

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if (
            hasattr(token, self.attribute)
            and getattr(token, self.attribute) == self.value
        ):
            yield token

    def __repr__(self):
        return f"AttributeHasValue({self.attribute}={self.value!r}"


class KeyHasValue(Matcher):
    def __init__(self, key: Any, value: Any):
        self.key = key
        self.value = value

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if (
            isinstance(token, Mapping)
            and self.key in token
            and token[self.key] == self.value
        ):
            yield token

    def __repr__(self):
        return f"KeyHasValue({self.key!r}={self.value!r})"


class Anything(Matcher):
    def __repr__(self):
        return f"Anything()"

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        yield token


class ChrRanges(Matcher[str, str]):
    def __init__(self, *ranges: Tuple[str, str]):
        self.ranges = ranges

    def __repr__(self):
        return f"ChrRanges{self.ranges!r}"

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        for start, stop in self.ranges:
            if ord(start) <= ord(token) <= ord(stop):
                yield token


class Test(Matcher[Tok, Out]):
    """
    Runs an arbitrary test and matches the token as-is if successful
    """

    def __init__(self, test: Callable[[Tok], bool]):
        self.test = test

    def __repr__(self):
        return f"Test({self.test!r}"

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        if self.test(token):
            yield token


class Not(Matcher[Tok, Out]):
    """
    Negates another matcher. If no match is found then the token is returned
    as-is.
    """

    def __init__(self, matcher: Union[Matcher, "Final"]):
        from .ast import Final

        if isinstance(matcher, Final):
            self.matcher: Matcher[Tok, Out] = matcher.statement
        elif isinstance(matcher, Matcher):
            self.matcher: Matcher[Tok, Out] = matcher
        else:
            raise ValueError("Cannot negate this")

    def __repr__(self):
        return f"Not({self.matcher!r})"

    def match(
        self, token: Tok, trail: Tuple[_TrailItem[Out], ...]
    ) -> Iterator[Out]:
        found = list(self.matcher.match(token, trail))

        if not found:
            yield token


__all__ = [
    "Tok",
    "Out",
    "Matcher",
    "Eq",
    "In",
    "OutOf",
    "AttributeHasValue",
    "KeyHasValue",
    "Anything",
    "ChrRanges",
    "Test",
    "Not",
    "_TrailItem",
]
