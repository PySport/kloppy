# Attempt to import optional dependencies
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Awaitable, Callable, Generator, Iterator, TypeVar, Union
from unittest.mock import patch

import aiobotocore
import aiobotocore.endpoint
import botocore
import botocore.retries.standard
from moto import mock_aws

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class _PatchedAWSReponseContent:
    """Patched version of `botocore.awsrequest.AWSResponse.content`"""

    content: Union[bytes, Awaitable[bytes]]

    def __await__(self) -> Iterator[bytes]:
        async def _generate_async() -> bytes:
            if isinstance(self.content, Awaitable):
                return await self.content
            return self.content

        return _generate_async().__await__()

    def decode(self, encoding: str) -> str:
        assert isinstance(self.content, bytes)
        return self.content.decode(encoding)


class PatchedAWSResponse:
    """Patched version of `botocore.awsrequest.AWSResponse`"""

    def __init__(self, response: botocore.awsrequest.AWSResponse) -> None:
        self._response = response
        self.status_code = response.status_code

        #  '317822581'{'server': 'amazon.com', 'date': 'Thu, 29 Aug 2024 17:10:05 GMT', 'x-amzn-requestid': 'Rlz2JkR24Tzbh5GEFyIBCKempp5HjXw6uh17z5J5EtoGhW4Udr97', 'x-amz-crc32': '317822581'}
        self.headers = response.headers
        self.headers["x-amz-crc32"] = None
        self.url = response.url
        self.content = _PatchedAWSReponseContent(response.content)
        self._content = self.content
        self.raw = response.raw
        self.text = response.text
        if not hasattr(self.raw, "raw_headers"):
            self.raw.raw_headers = {}


class PatchedRetryContext(botocore.retries.standard.RetryContext):
    """Patched version of `botocore.retries.standard.RetryContext`"""

    def __init__(self, *args, **kwargs):
        if kwargs.get("http_response"):
            kwargs["http_response"] = PatchedAWSResponse(
                kwargs["http_response"]
            )
        super().__init__(*args, **kwargs)


def _factory(
    original: Callable[[botocore.awsrequest.AWSResponse, T], Awaitable[R]],
) -> Callable[[botocore.awsrequest.AWSResponse, T], Awaitable[R]]:
    async def patched_convert_to_response_dict(
        http_response: botocore.awsrequest.AWSResponse, operation_model: T
    ) -> R:
        return await original(PatchedAWSResponse(http_response), operation_model)  # type: ignore[arg-type]

    return patched_convert_to_response_dict


@contextmanager
def mock_aio_aws() -> Generator[None, None, None]:
    with (
        patch(
            "aiobotocore.endpoint.convert_to_response_dict",
            new=_factory(aiobotocore.endpoint.convert_to_response_dict),
        ),
        patch(
            "botocore.retries.standard.RetryContext", new=PatchedRetryContext
        ),
        mock_aws(),
    ):
        yield
