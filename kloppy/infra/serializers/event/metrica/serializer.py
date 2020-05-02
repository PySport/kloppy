from kloppy.domain.models.event import EventType


event_type_map = {
    "SET PIECE": EventType.SET_PIECE,
    "RECOVERY": EventType.RECOVERY,
    "PASS": EventType.PASS,
    "BALL LOST": EventType.BALL_LOST,
    "BALL OUT": EventType.BALL_OUT,
    "SHOT": EventType.SHOT,
    "FAULT RECEIVED": EventType.FAULT_RECEIVED,
    "CHALLENGE": EventType.CHALLENGE,
    "CARD": EventType.CARD
}

# https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python/blob/master/processing/tracking.py
# https://github.com/HarvardSoccer/TrackingData/blob/fa7701893c928e9fcec358ec6e281743c00e6bc1/Metrica.py#L251