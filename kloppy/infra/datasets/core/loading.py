import os

import requests

from typing import Dict, Union

from kloppy.domain import DataSet, TrackingDataSet

from .registered import _DATASET_REGISTRY


def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_local_files(data_set_name: str, files: Dict[str, str]) -> Dict[str, str]:
    datasets_base_dir = os.environ.get('KLOPPY_BASE_DIR', None)
    if not datasets_base_dir:
        datasets_base_dir = os.path.expanduser('~/kloppy_datasets')

    dataset_base_dir = f'{datasets_base_dir}/{data_set_name}'
    if not os.path.exists(dataset_base_dir):
        os.makedirs(dataset_base_dir)

    local_files = {}
    for file_key, file_url in files.items():
        filename = file_url.split('/')[-1]
        local_filename = f'{dataset_base_dir}/{filename}'
        if not os.path.exists(local_filename):
            print(f'Downloading {filename}...')
            download_file(file_url, local_filename)
            print('Done')
        local_files[file_key] = local_filename
    return local_files


def load(data_set_name: str, options=None, **dataset_kwargs) -> Union[TrackingDataSet]:
    if data_set_name not in _DATASET_REGISTRY:
        raise ValueError(f"Dataset {data_set_name} not found")

    builder_cls = _DATASET_REGISTRY[data_set_name]
    builder = builder_cls()

    dataset_remote_files = builder.get_data_set_files(**dataset_kwargs)
    dataset_local_files = get_local_files(data_set_name, dataset_remote_files)

    file_handlers = {
        local_file_key: open(local_file_name, 'rb')
        for local_file_key, local_file_name
        in dataset_local_files.items()
    }

    try:
        serializer_cls = builder.get_serializer_cls()
        serializer = serializer_cls()
        data_set = serializer.deserialize(
            inputs=file_handlers,
            options=options
        )
    finally:
        for fp in file_handlers.values():
            fp.close()
    return data_set
