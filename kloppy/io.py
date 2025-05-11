"""I/O utilities for reading raw data."""

import bz2
import contextlib
import gzip
import logging
import lzma
import os
import re
from dataclasses import dataclass, replace
from io import BufferedWriter, BytesIO, TextIOWrapper
from typing import (
    IO,
    Any,
    BinaryIO,
    Callable,
    ContextManager,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from kloppy.exceptions import AdapterError, InputNotFoundError
from kloppy.infra.io.adapters import get_adapter

logger = logging.getLogger(__name__)

DEFAULT_GZIP_COMPRESSION = 1
DEFAULT_BZ2_COMPRESSION = 9
DEFAULT_XZ_COMPRESSION = 6


FilePath = Union[str, bytes, os.PathLike]
FileOrPath = Union[FilePath, IO]


@dataclass(frozen=True)
class Source:
    """A wrapper around a file-like object to enable optional inputs.

    Args:
        data (FileLike): The file-like object.
        optional (bool): Whether the file is optional. Defaults to False.
        skip_if_missing (bool): Whether to skip the file if it is missing. Defaults to False.

    Example:

        >>> open_as_file(Source.create("example.csv", optional=True))
    """

    data: Optional[FileOrPath]
    optional: bool = False
    skip_if_missing: bool = False

    @classmethod
    def create(cls, input_: Optional[FileOrPath], **kwargs):
        if isinstance(input_, Source):
            return replace(input_, **kwargs)
        return Source(data=input_, **kwargs)


FileLike = Union[FileOrPath, Source]


def _file_or_path_to_binary_stream(
    file_or_path: FileOrPath, binary_mode: str
) -> Tuple[BinaryIO, bool]:
    """
    Converts a file path or a file-like object to a binary stream.

    Args:
        file_or_path: The file path or file-like object to convert.
        binary_mode: The binary mode to open the file in. Must be one of 'rb', 'wb', or 'ab'.

    Returns:
        A tuple containing the binary stream and a boolean indicating whether
        a new file was opened (True) or an existing file-like object was used (False).
    """
    assert binary_mode in ("rb", "wb", "ab")

    if isinstance(file_or_path, (str, bytes)) or hasattr(
        file_or_path, "__fspath__"
    ):
        # If file_or_path is a path-like object, open it and return the binary stream
        return open(os.fspath(file_or_path), binary_mode), True  # type: ignore

    if isinstance(file_or_path, TextIOWrapper):
        # If file_or_path is a TextIOWrapper, return its underlying binary buffer
        return file_or_path.buffer, False

    if hasattr(file_or_path, "readinto") or hasattr(file_or_path, "write"):
        # If file_or_path is a file-like object, return it as is
        return file_or_path, False  # type: ignore

    raise TypeError(
        f"Unsupported type for {file_or_path}, {file_or_path.__class__.__name__}."
    )


def _detect_format_from_content(file_or_path: FileOrPath) -> Optional[str]:
    """
    Attempts to detect file format from the content by reading the first
    6 bytes. Returns None if no format could be detected.
    """
    fileobj, closefd = _file_or_path_to_binary_stream(file_or_path, "rb")
    try:
        if not fileobj.readable():
            return None
        if hasattr(fileobj, "peek"):
            bs = fileobj.peek(6)
        elif hasattr(fileobj, "seekable") and fileobj.seekable():
            current_pos = fileobj.tell()
            bs = fileobj.read(6)
            fileobj.seek(current_pos)
        else:
            return None

        if bs[:2] == b"\x1f\x8b":
            # https://tools.ietf.org/html/rfc1952#page-6
            return "gz"
        elif bs[:3] == b"\x42\x5a\x68":
            # https://en.wikipedia.org/wiki/List_of_file_signatures
            return "bz2"
        elif bs[:6] == b"\xfd\x37\x7a\x58\x5a\x00":
            # https://tukaani.org/xz/xz-file-format.txt
            return "xz"
        return None
    finally:
        if closefd:
            fileobj.close()


def _detect_format_from_extension(filename: FilePath) -> Optional[str]:
    """
    Attempt to detect file format from the filename extension.
    Return None if no format could be detected.
    """
    extensions = ("bz2", "xz", "gz")

    if isinstance(filename, bytes):
        for ext in extensions:
            if filename.endswith(b"." + ext.encode()):
                return ext

    if isinstance(filename, str):
        for ext in extensions:
            if filename.endswith("." + ext):
                return ext

    if hasattr(filename, "name"):
        return _detect_format_from_extension(filename.name)

    return None


def _filepath_from_path_or_filelike(file_or_path: FileOrPath) -> str:
    try:
        return os.fspath(file_or_path)  # type: ignore
    except TypeError:
        pass

    if hasattr(file_or_path, "name"):
        name = file_or_path.name
        if isinstance(name, str):
            return name
        elif isinstance(name, bytes):
            return name.decode()

    return ""


def _open(
    filename: FileOrPath,
    mode: str = "rb",
    compresslevel: Optional[int] = None,
    format: Optional[str] = None,
) -> BinaryIO:
    """
        A replacement for the "open" function that can also read and write
        compressed files transparently. The supported compression formats are gzip,
        bzip2 and xz. Filename can be a string, a Path or a file object.

        When writing, the file format is chosen based on the file name extension:
        - .gz uses gzip compression
        - .bz2 uses bzip2 compression
    - .xz uses xz/lzma compression
        - otherwise, no compression is used

        When reading, if a file name extension is available, the format is detected
        using it, but if not, the format is detected from the contents.

        mode can be: 'rb', 'ab', or 'wb'.

        compresslevel is the compression level for writing to gzip, and xz.
        This parameter is ignored for the other compression formats.
        If set to None, a default depending on the format is used:
        gzip: 6, xz: 6.

        format overrides the autodetection of input and output formats. This can be
        useful when compressed output needs to be written to a file without an
        extension. Possible values are "gz", "xz", "bz2" and "raw". In case of
        "raw", no compression is used.
    """
    if mode not in ("rb", "wb", "ab"):
        raise ValueError(f"Mode '{mode}' not supported")
    filepath = _filepath_from_path_or_filelike(filename)

    if format not in (None, "gz", "xz", "bz2", "raw"):
        raise ValueError(
            f"Format not supported: {format}. Choose one of: 'gz', 'xz', 'bz2'"
        )

    if format == "raw":
        detected_format = None
    else:
        detected_format = format or _detect_format_from_extension(filepath)
        if detected_format is None and "r" in mode:
            detected_format = _detect_format_from_content(filename)

    if detected_format == "gz":
        opened_file = _open_gz(filename, mode, compresslevel)
    elif detected_format == "xz":
        opened_file = _open_xz(filename, mode, compresslevel)
    elif detected_format == "bz2":
        opened_file = _open_bz2(filename, mode, compresslevel)
    else:
        opened_file, _ = _file_or_path_to_binary_stream(filename, mode)

    return opened_file


def _open_bz2(
    filename: FileOrPath,
    mode: str,
    compresslevel: Optional[int] = None,
) -> BinaryIO:
    assert mode in ("rb", "ab", "wb")
    if compresslevel is None:
        compresslevel = DEFAULT_BZ2_COMPRESSION

    if "r" in mode:
        return bz2.open(filename, mode)  # type: ignore
    return BufferedWriter(bz2.open(filename, mode, compresslevel))  # type: ignore


def _open_xz(
    filename: FileOrPath,
    mode: str,
    compresslevel: Optional[int] = None,
) -> BinaryIO:
    assert mode in ("rb", "ab", "wb")
    if compresslevel is None:
        compresslevel = DEFAULT_XZ_COMPRESSION

    if "r" in mode:
        return lzma.open(filename, mode)  # type: ignore
    return BufferedWriter(lzma.open(filename, mode, preset=compresslevel))  # type: ignore


def _open_gz(
    filename: FileOrPath,
    mode: str,
    compresslevel: Optional[int] = None,
) -> BinaryIO:
    assert mode in ("rb", "ab", "wb")
    if compresslevel is None:
        compresslevel = DEFAULT_GZIP_COMPRESSION

    if "r" in mode:
        return gzip.open(filename, mode)  # type: ignore
    return BufferedWriter(gzip.open(filename, mode, compresslevel=compresslevel))  # type: ignore


def get_file_extension(file_or_path: FileLike) -> str:
    """Determine the file extension of the given file-like object.

    If the file has compression extensions such as '.gz', '.xz', or '.bz2',
    they will be stripped before determining the extension.

    Args:
        file_or_path (FileLike): The file-like object whose extension needs to be determined.

    Returns:
        str: The file extension, including the dot ('.') if present.

    Raises:
        Exception: If the extension cannot be determined.

    Example:

        >>> get_file_extension("example.xml.gz")
        '.xml'
        >>> get_file_extension(Path("example.txt"))
        '.txt'
        >>> get_file_extension(Source(data="example.csv"))
        '.csv'
    """
    if isinstance(file_or_path, (str, bytes)) or hasattr(
        file_or_path, "__fspath__"
    ):
        path = os.fspath(file_or_path)  # type: ignore
        for ext in [".gz", ".xz", ".bz2"]:
            if path.endswith(ext):
                path = path[: -len(ext)]
        return os.path.splitext(path)[1]

    if isinstance(file_or_path, Source):
        return get_file_extension(file_or_path.data)

    raise TypeError(
        f"Could not determine extension for input type: {type(file_or_path)}"
    )


@contextlib.contextmanager
def dummy_context_mgr() -> Generator[None, None, None]:
    yield


def open_as_file(input_: FileLike) -> ContextManager[Optional[BinaryIO]]:
    """Open a byte stream to the given input object.

    The following input types are supported:
        - A string or `pathlib.Path` object representing a local file path.
        - A string representing a URL. It should start with 'http://' or
          'https://'.
        - A string representing a path to a file in a Amazon S3 cloud storage
          bucket. It should start with 's3://'.
        - A xml or json string containing the data. The string should contain
          a '{' or '<' character. Otherwise, it will be treated as a file path.
        - A bytes object containing the data.
        - A buffered binary stream that inherits from `io.BufferedIOBase`.
        - A [Source](`kloppy.io.Source`) object that wraps any of the above
          input types.

    Args:
        input_ (FileLike): The input object to be opened.

    Returns:
        BinaryIO: A binary stream to the input object.

    Raises:
        ValueError: If the input is required but not provided.
        InputNotFoundError: If the input file is not found and should not be skipped.
        TypeError: If the input type is not supported.

    Example:

        >>> with open_as_file("example.txt") as f:
        ...     contents = f.read()

    Note:
        To support reading data from other sources, see the
        [Adapter](`kloppy.io.adapters.Adapter`) class.

        If the given file path or URL ends with '.gz', '.xz', or '.bz2', the
        file will be decompressed before being read.
    """
    if isinstance(input_, Source):
        if input_.data is None and input_.optional:
            # This saves us some additional code in every vendor specific code
            return dummy_context_mgr()
        elif input_.data is None:
            raise ValueError("Input required but not provided.")
        else:
            try:
                return open_as_file(input_.data)
            except InputNotFoundError as exc:
                if input_.skip_if_missing:
                    logging.info(f"Input {input_.data} not found. Skipping")
                    return dummy_context_mgr()
                else:
                    raise exc

    if isinstance(input_, str) and ("{" in input_ or "<" in input_):
        # If input_ is a JSON or XML string, return it as a binary stream
        return BytesIO(input_.encode("utf8"))

    if isinstance(input_, bytes):
        # If input_ is a bytes object, return it as a binary stream
        return BytesIO(input_)

    if isinstance(input_, str) or hasattr(input_, "__fspath__"):
        # If input_ is a path-like object, open it and return the binary stream
        uri = _filepath_from_path_or_filelike(input_)

        adapter = get_adapter(uri)
        if adapter:
            stream = BytesIO()
            adapter.read_to_stream(uri, stream)
            stream.seek(0)
        else:
            raise AdapterError(f"No adapter found for {uri}")
        return stream

    if isinstance(input_, TextIOWrapper):
        # If file_or_path is a TextIOWrapper, return its underlying binary buffer
        return input_.buffer

    if hasattr(input_, "readinto"):
        # If file_or_path is a file-like object, return it as is
        return _open(input_)  # type: ignore

    raise TypeError(f"Unsupported input type: {type(input_)}")


def _natural_sort_key(path: str) -> List[Union[int, str]]:
    # Split string into list of chunks for natural sorting
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", path)
    ]


def expand_inputs(
    inputs: Union[FileLike, Iterable[FileLike]],
    regex_filter: Optional[str] = None,
    sort_key: Optional[Callable[[str], Any]] = None,
) -> Iterator[FileLike]:
    """
    Process input data to a list of file-like objects.

    This function resolves the input data to a list of file-like objects
    that can be opened with [`open_as_file`][kloppy.io.open_as_file].
    The input data can be any of the types supported by `open_as_file`,
    including a list of these input types or a directory.

    If the input is a directory, the directory is expanded to a list of files,
    which are then filtered using a regex pattern and sorted using a custom key.

    If the input is a list of file-like objects, these are assumed to be in the
    correct order and are returned as is.

    Args:
        inputs: The input object, a list of input objects, or a directory with input objects to be opened.
        regex_filter: A regex pattern to filter files (only applies to directories).
        sort_key: A callable to define sorting logic for files (only applies to directories).
          If not provided, files are sorted as ["file1.txt", "file2.txt", "file10.txt"].

    Returns:
        An iterator over the resolved file paths or stream content.
    """

    def is_file(uri):
        adapter = get_adapter(uri)
        if adapter:
            return adapter.is_file(uri)
        raise AdapterError(f"No adapter found for {uri}")

    def is_directory(uri):
        adapter = get_adapter(uri)
        if adapter:
            return adapter.is_directory(uri)
        raise AdapterError(f"No adapter found for {uri}")

    def process_expansion(files):
        """
        Process a list of files by filtering and sorting them.

        Args:
            files: List of file URIs to process.

        Returns:
            A sorted and filtered list of file URIs.
        """
        files = [f for f in files if not is_directory(f)]

        if regex_filter:
            pattern = re.compile(regex_filter)
            files = [f for f in files if pattern.search(f)]

        files.sort(key=sort_key or _natural_sort_key)
        return files

    if isinstance(inputs, (str, os.PathLike)):
        uri = _filepath_from_path_or_filelike(inputs)

        if is_directory(uri):
            adapter = get_adapter(uri)
            if adapter:
                yield from process_expansion(
                    adapter.list_directory(uri, recursive=True)
                )
            else:
                raise AdapterError(f"No adapter found for {uri}")
        elif is_file(uri):
            yield uri
        else:
            raise InputNotFoundError(f"Invalid path or file: {inputs}")

    elif isinstance(inputs, Iterable):
        for item in inputs:
            if isinstance(item, (str, os.PathLike)):
                uri = _filepath_from_path_or_filelike(item)
                if is_file(uri):
                    yield uri
                elif is_directory(uri):
                    adapter = get_adapter(uri)
                    if adapter:
                        yield from process_expansion(
                            adapter.list_directory(uri, recursive=True)
                        )
                    else:
                        raise AdapterError(f"No adapter found for {uri}")
                else:
                    raise InputNotFoundError(f"Invalid path or file: {item}")
            else:
                yield item

    else:
        yield inputs
