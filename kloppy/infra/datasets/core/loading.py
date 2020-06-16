import os, logging

import requests

from typing import Dict, Union

from kloppy.domain import TrackingDataset, EventDataset

from .registered import _DATASET_REGISTRY


logger = logging.getLogger(__name__)


def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_local_files(
    dataset_name: str, files: Dict[str, str]
) -> Dict[str, str]:
    datasets_base_dir = os.environ.get("KLOPPY_BASE_DIR", None)
    if not datasets_base_dir:
        datasets_base_dir = os.path.expanduser("~/kloppy_datasets")

    dataset_base_dir = f"{datasets_base_dir}/{dataset_name}"
    if not os.path.exists(dataset_base_dir):
        os.makedirs(dataset_base_dir)

    local_files = {}
    for file_key, file_url in files.items():
        filename = f"{file_key}={file_url.split('/')[-1]}"
        local_filename = f"{dataset_base_dir}/{filename}"
        if not os.path.exists(local_filename):
            logger.info(f"Downloading {filename}")
            download_file(file_url, local_filename)
            logger.info("Download complete")
        else:
            logger.info(f"Using local cached file {local_filename}")
        local_files[file_key] = local_filename
    return local_files


def load(
    dataset_name: str, options=None, **dataset_kwargs
) -> Union[TrackingDataset, EventDataset]:
    if dataset_name not in _DATASET_REGISTRY:
        raise ValueError(
            f"Dataset {dataset_name} not found. Known datasets: {', '.join(_DATASET_REGISTRY.keys())}"
        )

    builder_cls = _DATASET_REGISTRY[dataset_name]
    builder = builder_cls()

    dataset_urls = builder.get_dataset_urls(**dataset_kwargs)
    dataset_local_files = get_local_files(dataset_name, dataset_urls)

    file_handlers = {
        local_file_key: open(local_file_name, "rb")
        for local_file_key, local_file_name in dataset_local_files.items()
    }

    try:
        serializer_cls = builder.get_serializer_cls()
        serializer = serializer_cls()
        dataset = serializer.deserialize(inputs=file_handlers, options=options)
    finally:
        for fp in file_handlers.values():
            fp.close()
    return dataset
