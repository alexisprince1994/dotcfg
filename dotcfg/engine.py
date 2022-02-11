"""
Code related to reading multiple types
of supported configuration file formats.
"""
import enum
import json
import pathlib
from typing import Any, Callable, Dict, cast

import toml

from dotcfg import errors


class SupportedFileTypes(enum.Enum):

    JSON = "JSON"
    TOML = "TOML"

    # Will be assigned based on the provided file's extension
    AUTO = "AUTO"


def read_configuration_file(
    location: pathlib.Path, *, file_format: SupportedFileTypes = SupportedFileTypes.AUTO
) -> dict:
    """Reads a configuration file from disk

    Args:
        - location (pathlib.Path): Location of a file on disk
        - file_format (SupportedFileTypes): Enum member of the supported file types.
            Defaults to `AUTO`, which attempts to discover the file type based
            on the file's extension.

    Raises:
        - UnsupportedFileType: If a provided file has an unsupported extension
        - UnsupportedConfiguration: If the data structure in your configuration
            file doesn't deserialize into a dictionary

    Returns:
        dict: Dictionary of contents of the configuration file
    """
    if file_format == file_format.AUTO:
        file_format = _infer_file_format(location)

    loaders: Dict[SupportedFileTypes, Callable[[pathlib.Path], Dict[str, Any]]] = {
        SupportedFileTypes.JSON: _load_json,
        SupportedFileTypes.TOML: _load_toml,
    }
    try:
        return loaders[file_format](location)
    except KeyError as exc:
        raise errors.UnsupportedFileType(
            f"Unsupported file format {file_format}."
        ) from exc


def _infer_file_format(location: pathlib.Path) -> SupportedFileTypes:

    file_name = location.name
    file_extension = file_name.split(".")[-1]
    try:
        return SupportedFileTypes(file_extension.upper())
    except ValueError as exc:
        raise errors.UnsupportedFileType(
            f"Can't read configuration from {location}. {file_extension} is currently unsupported."
        ) from exc


def _load_toml(location: pathlib.Path) -> dict:

    return cast(dict, toml.load(location))


def _load_json(location: pathlib.Path) -> dict:
    with open(location) as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError(
            f"Configuration read from {location} is {type(location)} but must be a dict."
        )

    return data
