# Positions

In soccer, while players are not bound by strict rules about where they must be positioned on the field, there are traditionally recognized positions that players tend to stay closest to during a match. These positions are commonly tracked by various providers, though each provider may use different naming conventions and classifications. To offer consistency across different data sources, kloppy implements a standardized [PositionType][kloppy.domain.PositionType] with support for the following positions:

```python exec="true" html="true"
import subprocess

diagram = """
direction: right
UNK: Unknown
GK: Goalkeeper
DEF: Defender
FB: FullBack
LB: LeftBack
RB: RightBack
CB: CenterBack
LCB: LeftCenterBack
RCB: RightCenterBack
WB: WingBack
LWB: LeftWingBack
RWB: RightWingBack
MID: Midfielder
DM: DefensiveMidfield
LDM: LeftDefensiveMidfield
CDM: CenterDefensiveMidfield
RDM: RightDefensiveMidfield
CM: CentralMidfield
LCM: LeftCentralMidfield
CenterMid: CenterMidfield
RCM: RightCentralMidfield
AM: AttackingMidfield
LAM: LeftAttackingMidfield
CAM: CenterAttackingMidfield
RAM: RightAttackingMidfield
WM: WideMidfield
LW: LeftWing
RW: RightWing
LM: LeftMidfield
RM: RightMidfield
ATT: Attacker
LF: LeftForward
ST: Striker
RF: RightForward

UNK -> GK
UNK -> DEF
UNK -> MID
UNK -> ATT

DEF -> FB
DEF -> CB
DEF -> WB

FB -> LB
FB -> RB

CB -> LCB
CB -> RCB

WB -> LWB
WB -> RWB

MID -> DM
MID -> CM
MID -> AM
MID -> WM

DM -> LDM
DM -> CDM
DM -> RDM

CM -> LCM
CM -> CenterMid
CM -> RCM

AM -> LAM
AM -> CAM
AM -> RAM

WM -> LW
WM -> RW
WM -> LM
WM -> RM

ATT -> LF
ATT -> ST
ATT -> RF
"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "--layout=elk", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

Each [`PositionType`][kloppy.domain.PositionType] has a unique name and code.

```pycon exec="true" source="console" session="concepts-positions"
>>> from kloppy.domain import PositionType
>>> print(PositionType.LeftCenterBack) 
Left Center Back
```

```pycon exec="true" source="console" session="concepts-positions"
>>> print(PositionType.LeftCenterBack.code) 
LCB
```

As you might have noticed, positions are ordered hierarchically. This allows you to work on different levels of granularity, from broader categories like "Defender" or "Midfielder" to more specific positions like "Left Back" or "Center Midfield."

Each [`PositionType`][kloppy.domain.PositionType] has a `.parent` attribute to get the position's broader category.

```pycon exec="true" source="console" session="concepts-positions"
>>> pos_lb = PositionType.LeftBack
>>> print(f"{pos_lb} >> {pos_lb.parent} >> {pos_lb.parent.parent}") 
```

You can check if a position belongs to a broader category using the [`is_subtype_of`][kloppy.domain.PositionType.is_subtype_of] method.

```pycon exec="true" source="console" session="concepts-positions"
>>> print(PositionType.LeftCenterBack.is_subtype_of(PositionType.Defender))
True
```

A player's position can change throughout a game. A player's positions throughout the game are stored in the `.positions` attributes as a [`TimeContainer`][kloppy.domain.TimeContainer]. This container maps [`Time`][kloppy.domain.Time] instances to positions, allowing lookups and time range queries:

- `.ranges()`: list positions throughout the game.
- `.value_at(time)`: get position at a specific time.
- `.at_start()`: retrieve the starting position. 
- `.last()`: retrieve the last position. 

```pycon exec="true" source="console" session="concepts-positions"
>>> from kloppy import statsbomb
>>> event_dataset = statsbomb.load_open_data(match_id="15946")
>>> player = event_dataset.metadata.teams[0].get_player_by_jersey_number(5)
>>> for start_time, end_time, position in player.positions.ranges():
...    print(f"{start_time}:{end_time} - {position.code if position is not None else 'SUB'}")
```

You can conveniently retrieve a player's starting position or a player's position at a certain time in the match.

```pycon exec="true" source="console" session="concepts-positions"
>>> print(player.positions.at_start())
```

```pycon exec="true" source="console" session="concepts-positions"
>>> print(player.positions.value_at(event_dataset.find("shot.goal").time))
```


```pycon exec="true" source="console" session="concepts-positions"
>>> print(player.positions.last())
```

Note that a player's position will be `None` if not on the pitch.
