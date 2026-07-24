import re

_first_cap_re = re.compile("(.)([A-Z][a-z0-9]+)")
_all_cap_re = re.compile("([a-z0-9])([A-Z])")


def to_snake_case(string: str) -> str:
    """Convert a string to snake_case.

    Args:
        string (str): The string to convert.

    Returns:
        str: The converted snake_case string.

    Examples:
        >>> to_snake_case("CamelCase")
        'camel_case'
        >>> to_snake_case("camelCase")
        'camel_case'
        >>> to_snake_case("Space separated")
        'space_separated'
        >>> to_snake_case("Hyphen-separated")
        'hyphen_separated'
    """
    string = re.sub(r"[\s\-]+", "_", string.strip())
    s1 = _first_cap_re.sub(r"\1_\2", string)
    s2 = _all_cap_re.sub(r"\1_\2", s1).lower()
    return re.sub(r"_+", "_", s2)


def remove_suffix(string: str, suffix: str) -> str:
    """Remove a suffix from a string if it is present.

    Args:
        string (str): The original string.
        suffix (str): The suffix to remove.

    Returns:
        str: The string with the suffix removed if it was present, otherwise the original string.
    """
    if string[-len(suffix) :] == suffix:
        return string[: -len(suffix)]
    else:
        return string
