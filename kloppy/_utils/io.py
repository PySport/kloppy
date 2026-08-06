from io import BytesIO
from typing import BinaryIO, Union
from urllib.parse import quote
from urllib.request import Request, urlopen

Readable = Union[bytes, BinaryIO]


def to_file_object(s: Readable) -> BinaryIO:
    if isinstance(s, bytes):
        return BytesIO(s)
    return s


def github_resolve_raw_data_url(repository: str, branch: str, file: str) -> str:
    """
    Resolve a GitHub repository file to its actual raw data URL.

    GitHub serves files differently depending on their size:
    - Small files are redirected to raw.githubusercontent.com
    - Large files (Git LFS) are redirected to media.githubusercontent.com

    This function follows the redirect and returns the final URL.

    Args:
        repository: The repository in the format "owner/repo" (e.g., "metrica-sports/sample-data")
        branch: The branch name (e.g., "master", "main")
        file: The file path within the repository (e.g., "data/file.csv")

    Returns:
        The resolved raw data URL

    Examples:
        >>> github_resolve_raw_data_url(
        ...     repository="metrica-sports/sample-data",
        ...     branch="master",
        ...     file="data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv"
        ... )
        'https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv'
    """
    # Encode the file path properly to handle spaces and special characters
    encoded_file = "/".join(quote(part, safe="") for part in file.split("/"))

    # Construct the GitHub raw URL
    # This URL will redirect to either raw.githubusercontent.com or media.githubusercontent.com
    github_url = f"https://github.com/{repository}/raw/refs/heads/{branch}/{encoded_file}"

    # Make a HEAD request to follow redirects and get the final URL
    req = Request(github_url, method="HEAD")
    try:
        with urlopen(req) as response:
            # The final URL after following redirects
            return response.url
    except Exception:
        # If there's an error, fall back to the standard raw.githubusercontent.com URL
        # This ensures backwards compatibility
        return f"https://raw.githubusercontent.com/{repository}/{branch}/{encoded_file}"
