from dataclasses import dataclass, field, replace
from functools import reduce
from typing import Generic, Text, Union

from .matchers import Matcher, Out, Tok


@dataclass(frozen=True)
class Node(Generic[Tok, Out]):
    """
    Root class for a node. It has no real usage by itself but that's useful to
    define operators.

    Assembling the nodes together will build an AST which the RegExp class will
    then turn into a compiled regular expression.

    Example:

    >>> from nsre import *
    >>> root = Final(Eq('a')) + Final(Eq('b')) * slice(1, 5)
    >>> re = RegExp.from_ast(root)
    >>> assert re.match('abb')
    >>> assert not re.match('a')
    """

    def __add__(self, other: "Node"):
        """
        Generates a concatenation
        """

        return Concatenation(self, other)

    def __or__(self, other: "Node"):
        """
        Generates an alternation
        """

        return Alternation(self, other)

    def __getitem__(self, item: Text):
        """
        Generates a capture group
        """

        if not isinstance(item, Text):
            raise KeyError("Cannot capture with a key other than a string")

        return Capture(name=item, statement=self)

    def __mul__(self, other: Union[int, slice]):
        """
        Generates a repetition

        - If just an integer, repeat exactly this number of times
        - If a slice(), repeat between start to stop times (included). If the
          values of start or stop are None then it's respectively considered
          like 0 and +inf.
        """

        if isinstance(other, int):
            if other < 1:
                raise ValueError(
                    "Cannot repeat item a negative number of times"
                )

            return reduce(
                lambda a, b: a + b, [replace(self) for _ in range(0, other)]
            )
        elif isinstance(other, slice):
            parts = []

            if isinstance(other.start, int) and other.start > 0:
                parts.append(self * other.start)
            elif other.start is None or other.start == 0:
                pass
            else:
                raise ValueError("Start of slice does not look valid")

            if isinstance(other.stop, int):
                for _ in range(other.start or 0, other.stop):
                    parts.append(Maybe(replace(self)))
            elif other.stop is None:
                parts.append(AnyNumber(replace(self)))
            else:
                raise ValueError("End of slice does not look valid")

            return reduce(lambda a, b: a + b, parts)
        else:
            raise ValueError("Multiply either with an int or a slice")

    def copy(self):
        """
        Generates a copy of the node. This is done because of the way the graph
        generation works: it will put all the nodes in a graph so all of them
        will need a unique ID in case the same sub-tree was used several cases.
        """

        return replace(self)


# noinspection PyUnresolvedReferences
class CopyLeftRightMixin:
    """
    Mixin to help with the copy of nodes that have a left and a right attribute
    """

    def copy(self):
        return self.__class__(self.left.copy(), self.right.copy())


# noinspection PyUnresolvedReferences
class CopyStatementMixin:
    """
    Mixin to help with the copy of nodes that just have a statement attribute
    """

    def copy(self):
        return self.__class__(self.statement.copy())


class DumbHash:
    """
    Mixin to generate a very dumb __hash__ and __eq__ implementation based on
    the object's ID. This simplifies the construction of the graph.
    """

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return self is other


@dataclass(frozen=True, eq=False)
class Final(DumbHash, Node):
    """
    In the end, all nodes in the graph should be Final(). They allow the
    engine to call the matcher (stored in statement here).
    """

    statement: Matcher[Tok, Out]

    def __lt__(self, other):
        """
        Comparable for use in the de-duplication process
        """

        return id(self) < id(other)


@dataclass(frozen=True, eq=False)
class Concatenation(DumbHash, CopyLeftRightMixin, Node):
    """
    Represents a concatenation of the left and the right nodes.
    """

    left: Node
    right: Node


@dataclass(frozen=True, eq=False)
class Alternation(DumbHash, CopyLeftRightMixin, Node):
    """
    Represents an alternation of the left and the right nodes
    """

    left: Node
    right: Node


@dataclass(frozen=True, eq=False)
class Maybe(DumbHash, CopyStatementMixin, Node):
    """
    Represents 0 or 1 occurrence of the statement
    """

    statement: Node


@dataclass(frozen=True, eq=False)
class AnyNumber(DumbHash, CopyStatementMixin, Node):
    """
    Represents 0 to +inf occurrences of the statement
    """

    statement: Node


@dataclass(frozen=True, eq=False)
class Capture(DumbHash, Node):
    """
    Represents a capture group around the statement
    """

    name: Text
    statement: Node = field(repr=False)

    def copy(self):
        return Capture(name=self.name, statement=self.statement.copy())

    def __lt__(self, other):
        """
        Comparable for use in the de-duplication process
        """

        return id(self) < id(other)


@dataclass(frozen=True)
class _Initial(Node):
    """
    Special initial node. Don't use it directly.
    """


@dataclass(frozen=True)
class _Terminal(Node):
    """
    Special final node. Don't use it directly.
    """


__all__ = [
    "Node",
    "Final",
    "Concatenation",
    "Alternation",
    "Maybe",
    "AnyNumber",
    "Capture",
]
