from enum import Enum


class PositionType(Enum):
    Unknown = ("Unknown", "UNK", None)

    Goalkeeper = ("Goalkeeper", "GK", None)

    Defender = ("Defender", "DEF", None)
    FullBack = ("Full Back", "FB", "Defender")
    LeftBack = ("Left Back", "LB", "FullBack")
    RightBack = ("Right Back", "RB", "FullBack")
    CenterBack = ("Center Back", "CB", "Defender")
    LeftCenterBack = ("Left Center Back", "LCB", "CenterBack")
    RightCenterBack = ("Right Center Back", "RCB", "CenterBack")
    LeftWingBack = ("Left Wing Back", "LWB", "WingBack")
    RightWingBack = ("Right Wing Back", "RWB", "WingBack")

    Midfielder = ("Midfielder", "MID", None)
    DefensiveMidfield = ("Defensive Midfield", "DM", "Midfielder")
    LeftDefensiveMidfield = (
        "Left Defensive Midfield",
        "LDM",
        "DefensiveMidfield",
    )
    CenterDefensiveMidfield = (
        "Center Defensive Midfield",
        "CDM",
        "DefensiveMidfield",
    )
    RightDefensiveMidfield = (
        "Right Defensive Midfield",
        "RDM",
        "DefensiveMidfield",
    )

    CentralMidfield = ("Central Midfield", "CM", "Midfielder")
    LeftCentralMidfield = ("Left Central Midfield", "LCM", "CentralMidfield")
    CenterMidfield = ("Center Midfield", "CM", "CentralMidfield")
    RightCentralMidfield = ("Right Central Midfield", "RCM", "CentralMidfield")

    AttackingMidfield = ("Attacking Midfield", "AM", "Midfielder")
    LeftAttackingMidfield = (
        "Left Attacking Midfield",
        "LAM",
        "AttackingMidfield",
    )
    CenterAttackingMidfield = (
        "Center Attacking Midfield",
        "CAM",
        "AttackingMidfield",
    )
    RightAttackingMidfield = (
        "Right Attacking Midfield",
        "RAM",
        "AttackingMidfield",
    )

    WideMidfield = ("Wide Midfield", "WM", "Midfielder")
    LeftWing = ("Left Wing", "LW", "WideMidfield")
    RightWing = ("Right Wing", "RW", "WideMidfield")
    LeftMidfield = ("Left Midfield", "LM", "WideMidfield")
    RightMidfield = ("Right Midfield", "RM", "WideMidfield")

    Attacker = ("Attacker", "ATT", None)
    LeftForward = ("Left Forward", "LF", "Attacker")
    Striker = ("Striker", "ST", "Attacker")
    RightForward = ("Right Forward", "RF", "Attacker")

    def __init__(self, long_name, code, parent):
        self.long_name = long_name
        self.code = code
        self._parent = parent

    @property
    def parent(self):
        if self._parent:
            return PositionType[self._parent]
        return None

    def is_subtype_of(self, other):
        current = self
        while current is not None:
            if current == other:
                return True
            current = current.parent
        return False

    def __str__(self):
        return self.long_name

    @classmethod
    def unknown(cls) -> "PositionType":
        return cls.Unknown
