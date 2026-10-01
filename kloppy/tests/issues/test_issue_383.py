import inspect
import warnings

import pytest

from kloppy.utils import deprecated


@pytest.fixture(params=[False, True], ids=["bare", "reason"])
def deprecated_function(request):
    calls = []

    def old_function(value, *, factor=2):
        """Return a scaled value."""
        calls.append(value)
        return value * factor

    if request.param:
        wrapped = deprecated("use replacement")(old_function)
        message = "Call to deprecated function old_function (use replacement)."
    else:
        wrapped = deprecated(old_function)
        message = "Call to deprecated function old_function."
    return wrapped, old_function, calls, message


@pytest.mark.parametrize(
    "action, expected_count", [("ignore", 0), ("default", 1), ("always", 2)]
)
def test_deprecated_respects_warning_filter(
    deprecated_function, action, expected_count
):
    wrapped, _, calls, _ = deprecated_function

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter(action, DeprecationWarning)
        filters_before = warnings.filters[:]
        for _ in range(2):
            assert wrapped(3, factor=4) == 12

        assert len(caught) == expected_count
        assert warnings.filters == filters_before

    assert calls == [3, 3]


def test_deprecated_respects_error_filter(deprecated_function):
    wrapped, _, calls, message = deprecated_function

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        filters_before = warnings.filters[:]
        with pytest.raises(DeprecationWarning) as exc_info:
            wrapped(3)

        assert str(exc_info.value) == message
        assert warnings.filters == filters_before

    assert calls == []


def test_deprecated_preserves_warning_and_function_details(deprecated_function):
    wrapped, original, _, message = deprecated_function

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        call_line = inspect.currentframe().f_lineno + 1
        assert wrapped(3) == 6

    assert len(caught) == 1
    assert caught[0].category is DeprecationWarning
    assert str(caught[0].message) == message
    assert caught[0].filename == __file__
    assert caught[0].lineno == call_line
    assert wrapped.__name__ == original.__name__
    assert wrapped.__doc__ == original.__doc__
    assert wrapped.__wrapped__ is original
