from kloppy.exceptions import DeserializationError


def parse_period_id(raw_period: str) -> int:
    if "H" in raw_period:
        period_id = int(raw_period.replace("H", ""))
    elif "E" in raw_period:
        period_id = 2 + int(raw_period.replace("E", ""))
    elif raw_period == "P":
        period_id = 5
    else:
        raise DeserializationError(f"Unknown period {raw_period}")
    return period_id
