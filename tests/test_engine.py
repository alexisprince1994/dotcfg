import json
import pathlib
import tempfile

import pytest
import toml

from dotcfg import errors
from dotcfg.engine import SupportedFileTypes, read_configuration_file


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield pathlib.Path(td)


@pytest.fixture
def cfg():
    """
    Underlying serialization libraries are depended on for serializing
    and deserializing data. If a data type is available in one config
    format, the data types are passed through and not coerced by
    the library.
    """

    return {"root": True, "nested": {"foo": 1}}


class BaseMixin:

    file_format: SupportedFileTypes

    def test_reads_with_explicit_auto(self, config: pathlib.Path):

        read_configuration_file(config, file_format=SupportedFileTypes.AUTO)

    def test_reads_with_auto_default(self, config: pathlib.Path):
        read_configuration_file(config)

    def test_reads_with_explicit_format(self, config: pathlib.Path):
        read_configuration_file(config, file_format=self.file_format)


class TestTomlReader(BaseMixin):

    file_format = SupportedFileTypes.TOML

    @pytest.fixture
    def config(self, cfg: dict, temp_dir: pathlib.Path):
        location = temp_dir / "toml_config.toml"
        with open(location, "w") as f:
            toml.dump(cfg, f)

        yield location


class TestJsonReader(BaseMixin):

    file_format = SupportedFileTypes.JSON

    @pytest.fixture
    def config(self, cfg: dict, temp_dir: pathlib.Path):
        location = temp_dir / "json_config.json"
        with open(location, "w") as f:
            json.dump(cfg, f)

        yield location


@pytest.mark.parametrize(
    "bad_file_name", ["test", "test.invalid_extension", "test.yaml"]
)
def test_raises_error_on_unexpected_file_type(
    cfg: dict, temp_dir: pathlib.Path, bad_file_name: str
):

    location = temp_dir / bad_file_name
    with open(location, "w") as f:
        json.dump(cfg, f)

    with pytest.raises(errors.UnsupportedFileType):
        read_configuration_file(location)
