import importlib.util

import pytest

from kloppy.domain.models.common import Dataset

has_pandas = importlib.util.find_spec("pandas") is not None
has_pyarrow = importlib.util.find_spec("pyarrow") is not None
has_polars = importlib.util.find_spec("polars") is not None
has_networkx = importlib.util.find_spec("networkx") is not None
has_s3fs = importlib.util.find_spec("s3fs") is not None


class TestOptionalDependencies:
    @pytest.mark.skipif(has_pandas, reason="pandas is installed")
    def test_to_pandas_missing(self):
        dataset = Dataset(records=[], metadata=None)
        with pytest.raises(
            ImportError, match="Missing optional dependency 'pandas'"
        ):
            dataset.to_df(engine="pandas")

    @pytest.mark.skipif(
        has_pandas and has_pyarrow, reason="pandas and pyarrow are installed"
    )
    def test_to_pandas_pyarrow_missing(self):
        dataset = Dataset(records=[], metadata=None)
        with pytest.raises(ImportError, match="Missing optional dependency"):
            dataset.to_df(engine="pandas[pyarrow]")

    @pytest.mark.skipif(has_polars, reason="polars is installed")
    def test_to_polars_missing(self):
        dataset = Dataset(records=[], metadata=None)
        with pytest.raises(
            ImportError, match="Missing optional dependency 'polars'"
        ):
            dataset.to_df(engine="polars")

    @pytest.mark.skipif(has_s3fs, reason="s3fs is installed")
    def test_s3fs_missing(self):
        from kloppy.infra.io.adapters.s3 import S3Adapter

        adapter = S3Adapter(s3_kwargs={})
        with pytest.raises(
            ImportError, match="Missing optional dependency 's3fs'"
        ):
            adapter.read("s3://dummy/path")

    @pytest.mark.skipif(has_networkx, reason="networkx is installed")
    def test_networkx_missing(self):
        with pytest.raises(
            ImportError, match="Missing optional dependency 'networkx'"
        ):
            pass
