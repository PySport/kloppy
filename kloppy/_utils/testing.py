from typing import Optional

import pytest

from kloppy._utils.optional import import_optional_dependency


def skip_if_no(
    package: str, min_version: Optional[str] = None
) -> pytest.MarkDecorator:
    """
    Generic function to help skip tests when required packages are not
    present on the testing system.

    This function returns a pytest mark with a skip condition that will be
    evaluated during test collection. An attempt will be made to import the
    specified ``package`` and optionally ensure it meets the ``min_version``.

    The mark can be used as either a decorator for a test class or to be
    applied to parameters in pytest.mark.parametrize calls or parametrized
    fixtures. Use pytest.importorskip if an imported module is later needed
    or for test functions.

    If the import and version check are unsuccessful, then the test function
    (or test case when used in conjunction with parametrization) will be
    skipped.

    Args:
        package (str): The name of the required package.
        min_version (Optional[str]): Optional minimum version of the package. Defaults to None.

    Returns:
        pytest.MarkDecorator: A pytest.mark.skipif to use as either a test
            decorator or a parametrization mark.
    """
    msg = f"Could not import '{package}'"
    if min_version:
        msg += f" satisfying a min_version of {min_version}"

    return pytest.mark.skipif(
        not bool(
            import_optional_dependency(
                package, raise_on_missing=False, min_version=min_version
            )
        ),
        reason=msg,
    )
