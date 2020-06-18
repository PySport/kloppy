from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from typing import (
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    Sequence,
    Text,
    Tuple,
)

import networkx as nx

# noinspection PyProtectedMember
from .ast import (
    Alternation,
    AnyNumber,
    Capture,
    Concatenation,
    Final,
    Maybe,
    Node,
    _Initial,
    _Terminal,
)
from .matchers import Out, Tok, _TrailItem


def ast_to_graph(root: Node) -> nx.DiGraph:
    """
    You will create your regular expression with a specific syntax which is
    transformed into an AST, however the regular expression engine expects
    to navigate in a graph. As it is too complicated to navigate inside the
    AST directly, this function transforms the AST into an actual graph.

    Notes
    -----
    Since each node, except the :py:class:`nsre.ast.Final` ones, have children
    nodes, the idea is to insert nodes into the graph one at a time and then to
    work on those new nodes to transform it into its content.

    Also, there is implicitly a :code:`_Initial` and a :code:`_Terminal` node.
    The graph exploration will start from the initial node and the regular
    expression will be considered to be a match if when the input sequence is
    entirely consumed you can transition to the terminal node.

    By example, you got a node A which is a concatenation of B and C. Suppose
    that the code looks like this:

    >>> from nsre import *
    >>> c = Final(Eq('c'))
    >>> b = Final(Eq('b'))
    >>> a = c + b
    >>> g = ast_to_graph(a)

    Then the first graph you're going to get is

        :code:`_Initial` -> :code:`A` -> :code:`_Terminal`

    But then the algorithm is going to transform A into its content and you'll
    end up with the new graph

        :code:`_Initial` -> :code:`B` -> :code:`C` -> :code:`_Terminal`

    And so on if B and C have content of their own (they don't in the current
    example).

    The way to transform a node into its content depends on the node type, of
    course. That's why you'll find in this file a bunch of :code:`_explore_*`
    methods which are actually the ways to transform a specific node into a
    graph.

    The overall algorithm here is to have a to-do list (the "explore" variable)
    which contains the set of currently unexplored nodes. When a node is
    transformed into its content, the newly inserted nodes are also added to
    the to-do list and will be explored at the next iteration. This goes on
    and on until the whole AST has been transformed into a graph.

    Another detail is that capture groups are indicated with a start and a
    stop marker on the edges. Each edge can potentially contain in its data
    a "start_captures" or a "stop_captures" list. They contain the name, in
    order, of capture groups to start or stop. The capture should start right
    after the start and before the stop marker.

    See Also
    --------
    _explore_concatenation, _explore_alternation, _explore_maybe,
    _explore_any_number, _explore_capture
    """

    g = nx.DiGraph()
    initial = _Initial()
    terminal = _Terminal()

    g.add_nodes_from([initial, root, terminal])
    g.add_edge(initial, root)
    g.add_edge(root, terminal)

    explore = {root}

    while explore:
        for node in [*explore]:
            explore.remove(node)

            if isinstance(node, Final):
                pass
            elif isinstance(node, Concatenation):
                _explore_concatenation(explore, g, node)
            elif isinstance(node, Alternation):
                _explore_alternation(explore, g, node)
            elif isinstance(node, Maybe):
                _explore_maybe(explore, g, node)
            elif isinstance(node, AnyNumber):
                _explore_any_number(explore, g, node)
            elif isinstance(node, Capture):
                _explore_capture(explore, g, node)

    return g


def _explore_capture(explore, g, node):
    """
    Adds the capture flags on the edges around the node. Of another capture
    is already flagged, append to the list.
    """

    explore.add(node.statement)
    g.add_node(node.statement)

    for p in g.predecessors(node):
        data = g.get_edge_data(p, node, default={"start_captures": []})
        data["start_captures"] = [*data.get("start_captures", []), node]
        g.add_edge(p, node.statement, **data)

    for s in g.successors(node):
        data = g.get_edge_data(node, s, default={"stop_captures": []})
        data["stop_captures"] = [node, *data.get("stop_captures", [])]
        g.add_edge(node.statement, s, **data)

    g.remove_node(node)


# noinspection DuplicatedCode
def _explore_any_number(explore, g, node):
    """
    Allows to see any number of the child node. This means:

    - Either 0 match, meaning that all incoming edges are connected directly
      to all outgoing edges
    - Either 1 or more matches, granting a loop of the node on itself
    - And of course an exit edge which goes into the next node(s)
    """

    explore.add(node.statement)
    g.add_node(node.statement)

    g.add_edge(node.statement, node.statement)

    _cross_connect(g, node)

    for p in g.predecessors(node):
        data = g.get_edge_data(p, node, default={})
        g.add_edge(p, node.statement, **data)

    for s in g.successors(node):
        data = g.get_edge_data(node, s, default={})
        g.add_edge(node.statement, s, **data)

    g.remove_node(node)


# noinspection DuplicatedCode
def _explore_maybe(explore, g, node):
    """
    Like `_explore_any_number` but without the self-loop to allow at most one
    match.
    """

    explore.add(node.statement)
    g.add_node(node.statement)

    _cross_connect(g, node)

    for p in g.predecessors(node):
        data = g.get_edge_data(p, node, default={})
        g.add_edge(p, node.statement, **data)

    for s in g.successors(node):
        data = g.get_edge_data(node, s, default={})
        g.add_edge(node.statement, s, **data)

    g.remove_node(node)


def _cross_connect(g, node):
    """
    Used by `_explore_any_number` and `_explore_maybe` which both need to
    connect all incoming edges to all outgoing edges.

    Notes
    -----
    There is a complicated logic with the capture flags in order to make sure
    that capture groups that are opened and closed at the same time don't
    actually stay (because they confuse the matching algorithm and they are
    useless).
    """

    for p, s in product(g.predecessors(node), g.successors(node)):
        data1 = g.get_edge_data(p, node, default={})
        data2 = g.get_edge_data(node, s, default={})
        merged = dict(**data1)
        merged.update(**data2)

        if "start_captures" in data1 and "start_captures" in data2:
            merged["start_captures"] = (
                data1["start_captures"] + data2["start_captures"]
            )

        if "stop_captures" in data1 and "stop_captures" in data2:
            merged["stop_captures"] = (
                data1["stop_captures"] + data2["stop_captures"]
            )

        cancel = 0
        start_captures = merged.get("start_captures", [])
        stop_captures = merged.get("stop_captures", [])

        for start, stop in zip(start_captures, stop_captures):
            if start == stop:
                cancel += 1
            else:
                break

        if cancel:
            merged["start_captures"] = start_captures[cancel:]
            merged["stop_captures"] = stop_captures[:-cancel]

        g.add_edge(p, s, **merged)


def _explore_alternation(explore, g, node):
    """
    This node accepts either the left or the right child node. Meaning that
    all edges connected to this node are connected to both the left and the
    right node.
    """

    explore.add(node.left)
    explore.add(node.right)

    g.add_node(node.left)
    g.add_node(node.right)

    for p in g.predecessors(node):
        data = g.get_edge_data(p, node, default={})
        g.add_edge(p, node.left, **data)
        g.add_edge(p, node.right, **data)

    for s in g.successors(node):
        data = g.get_edge_data(node, s, default={})
        g.add_edge(node.left, s, **data)
        g.add_edge(node.right, s, **data)

    g.remove_node(node)


# noinspection DuplicatedCode
def _explore_concatenation(explore, g, node):
    """
    Concatenation is just taking all the incoming edges and plugging them into
    the left node, making a connection between the left and the right node and
    then taking all the outgoing edges and plugging them into the right node.
    """

    explore.add(node.left)
    explore.add(node.right)

    g.add_node(node.left)
    g.add_node(node.right)

    for p in g.predecessors(node):
        data = g.get_edge_data(p, node, default={})
        g.add_edge(p, node.left, **data)

    g.add_edge(node.left, node.right)

    for s in g.successors(node):
        data = g.get_edge_data(node, s, default={})
        g.add_edge(node.right, s, **data)

    g.remove_node(node)


@dataclass(frozen=True)
class Explorer(Generic[Tok, Out]):
    """
    An explorer is a pointer to a specific position in the graph, with a past
    trail of previously visited nodes.
    """

    re: "RegExp[Tok, Out]"
    node: Node[Tok, Out]
    trail: Tuple[_TrailItem[Out], ...]

    @property
    def signature(self) -> Tuple[Node, Tuple[_TrailItem, ...]]:
        """
        Sortable signature for this explorer, used for de-duplication
        """

        return self.node, self.trail

    def advance(self, token: Tok) -> Iterator["Explorer[Tok, Out]"]:
        """
        Given the provided token, emits all the explorers that managed to
        advance to another node.

        Parameters
        ----------
        token
            Consumed token
        """

        for s in self.re.graph.successors(self.node):
            if not isinstance(s, Final):
                continue

            data = self.re.graph.get_edge_data(self.node, s, default={})
            possible_trail = self.trail + (_TrailItem(item=None, data=data),)

            for m in s.statement.match(token, trail=possible_trail):
                yield Explorer(
                    re=self.re,
                    node=s,
                    trail=self.trail + (_TrailItem(item=m, data=data),),
                )

    def can_terminate(self) -> bool:
        """
        Indicates if this explorer is connected to a _Terminal node, meaning
        that if you were to stop the matching here it would mean that the
        expression matched.
        """
        return self.re.graph.has_successor(self.node, _Terminal())


class _Match(Generic[Out]):
    """
    Internal sub-type that helps building the Match and MatchList objects
    expected outside of `RegExp#match()`.
    """

    def __init__(self, start_pos: int):
        self.start_pos = start_pos
        self.children: Dict[Text, List[_Match]] = {}
        self.trail: List[Out] = []
        self._stack: List[Capture] = []

    def _deep_get(self, keys: Sequence[Capture]) -> "_Match":
        """
        Gets a child following a path of keys. At each level, gets the last
        child in the list as it is the one that we're going to want to deal
        with.

        Parameters
        ----------
        keys
            Successive name of keys to follow
        """

        ptr = self

        for key in keys:
            ptr = ptr.children[key.name][-1]

        return ptr

    def start(self, capture: Capture, pos: int) -> None:
        """
        Call this to indicate that you're starting a capture group

        Notes
        -----
        This will append the name of the capture group to the capture stack
        and will also make sure that there is a corresponding child Match for
        this sequence of keys.

        Parameters
        ----------
        capture
            Name of the capturing group
        pos
            Starting index in the input sequence
        """

        stick = self._deep_get(self._stack)

        if capture not in stick.children:
            stick.children[capture.name] = [_Match(pos)]
        else:
            stick.children[capture.name].append(_Match(pos))

        self._stack.append(capture)

    def stop(self, capture: Capture) -> None:
        """
        Indicates that matching should stop (as opposed to start).

        Parameters
        ----------
        capture
            Name of the matching group to stop
        """

        if capture != self._stack[-1]:
            raise ValueError("Trying to stop a match which is not started")

        self._stack = self._stack[0:-1]

    def append(self, item: Out) -> None:
        """
        Appends the item at all level of trails for the current stack.

        Parameters
        ----------
        item
            Matched item to be added to trails
        """

        self.trail.append(item)
        ptr = self

        for key in self._stack:
            ptr = ptr.children[key.name][-1]
            ptr.trail.append(item)

    def as_match(self, join_trails: bool = False) -> "Match":
        """
        Converts this into a real read-only match object.

        Parameters
        ----------
        join_trails
            If set to true then the items matched in the trail are expected to
            be individual characters and they will be joined in a string
            instead of being returned in an array
        """

        return Match(
            start_pos=self.start_pos,
            trail="".join(self.trail) if join_trails else tuple(self.trail),
            children=MappingProxyType(
                {
                    k: MatchList(i.as_match(join_trails) for i in v)
                    for k, v in self.children.items()
                }
            ),
        )


@dataclass(frozen=True)
class Match(Generic[Out]):
    """
    Represents a match for a capture group in the regular expression.
    """

    # Index of the first matching token
    start_pos: int

    # Sub-groups that matched. As several groups could be matching, a list
    # is returned so you can access each one of them.
    children: Mapping[Text, List["Match"]]

    # Trail of matched items. It's the output of the matcher, not the input
    # tokens.
    trail: Sequence[Out]

    def __getitem__(self, item):
        return self.children[item][0]


class MatchList(tuple, Generic[Out]):
    """
    List of matches. It's just a convenience around a tuple in order to
    facilitate getting a specific group in the first item of the list.
    """

    def __getitem__(self, item) -> Match[Out]:
        if isinstance(item, str):
            return self[0][item]
        else:
            return super().__getitem__(item)


def _make_match(trail: Tuple[_TrailItem, ...]) -> _Match[Out]:
    """
    Transforms an explorer into a Match object using its trail

    Parameters
    ----------
    explorer
        Explorer that you want to transform
    """

    match = _Match(0)

    for i, token in enumerate(trail):
        for stop in token.data.get("stop_captures", []):
            match.stop(stop)

        for start in token.data.get("start_captures", []):
            match.start(start, i)

        match.append(token.item)

    return match


class RegExp(Generic[Tok, Out]):
    """
    Core of the RegExp system. Don't instantiate this directly. There is so
    far only one way to create an instance easily but in the future there will
    be more ways, like a parser for good old-school regular expressions or a
    new specific DSL.

    Here's an usage example.

    >>> from nsre import *
    >>> re = RegExp.from_ast(anything()['user'] + seq("@") + anything()['domain'])
    >>> m = re.match('remy.sanchez@with-madrid.com', join_trails=True)
    >>> assert m['user'].trail == 'remy.sanchez'
    >>> assert m['domain'].trail == 'with-madrid.com'
    """

    def __init__(self, graph: nx.DiGraph):
        """
        Don't call me directly.

        See Also
        -------
        RegExp#from_ast() : compiles an AST into a regular expression

        Parameters
        ----------
        graph
            The regular expression's graph
        """

        self.graph = graph

    @classmethod
    def from_ast(cls, root: Node[Tok, Out]) -> "RegExp[Tok, Out]":
        """
        Use this to generate your regular expression. To generate the AST,
        have a look at :py:mod:`nsre.ast` and :py:mod:`nsre.shortcuts` modules.

        Parameters
        ----------
        root
            Root node of your expression.
        """

        return cls(graph=ast_to_graph(root.copy()))

    def match(
        self,
        seq: Sequence[Tok],
        join_trails: bool = False,
        consume_all: bool = True,
    ) -> MatchList[Match[Out]]:
        """
        For a given sequence of tokens, generates all the matches that were
        detected.

        Notes
        -----
        If you think your regular expression like you would think of using the
        `re` module then you're going to have 0 or 1 match. However, if your
        Matchers can match several options then you might end up with two
        or more matches at the same time.

        For this reason, the MatchList object provides shortcuts so you don't
        have to skim through the list of matches if you don't want to.

        Please note that inside a match, the capture groups do not match in
        "parallel", only root MatchList provides several matching options. The
        inside of them is just their content.

        Parameters
        ----------
        seq
            Sequence that you would like to test
        join_trails
            If all your output items are going to be characters, you can set
            this to true in order to receive trails that are strings instead of
            them being character lists.
        """

        stack: List[Explorer[Tok, Out]] = [Explorer(self, _Initial(), tuple())]

        stacks = []
        for token in seq:
            stack = list(
                self._de_duplicate(
                    ne for oe in stack for ne in oe.advance(token)
                )
            )

            # if not consume_all:
            #     if any(s.can_terminate() for s in stack):
            #         break

            if not stack:
                break

            stacks.append(stack)

        if not consume_all and stacks:
            stacks.reverse()
            for stack in stacks:
                stack = [s for s in stack if s.can_terminate()]
                if stack:
                    break

        terminal = list(
            self._de_duplicate(
                (s for s in stack if s.can_terminate()), key="trail"
            )
        )

        return MatchList(
            _make_match(s.trail).as_match(join_trails=join_trails)
            for s in terminal
        )

    def _de_duplicate(
        self, stack: Iterator[Explorer[Tok, Out]], key: Text = "signature"
    ) -> Iterator[Explorer[Tok, Out]]:
        """
        As there is potentially several paths that lead to the same result, we
        merge for each node all identical trails. Without this the number of
        results becomes completely crazy (on top of being useless and
        confusing)
        """

        stack = list(sorted(stack, key=lambda e: getattr(e, key)))

        if not stack:
            return

        yield stack[0]

        for i in range(1, len(stack)):
            if getattr(stack[i], key) != getattr(stack[i - 1], key):
                yield stack[i]


__all__ = ["RegExp", "Match", "MatchList", "ast_to_graph", "_make_match"]
