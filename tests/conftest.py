import os
import tempfile
from typing import Any, Dict, Iterator

import pytest

template = b"""
debug = false

[general]
x = 1
y = "hi"

    [general.nested]
    x = "${general.x}"
    x_interpolated = "${general.x} + 1"
    y = "${general.y} or bye"

[interpolation]
key = "x"
value = "${general.nested.${interpolation.key}}"
bad_value = "${general.bad_key}"

array_values = ["${general.x}", "${general.bad_key}"]

[env_vars]
existing_key = true
missing_key = false
integer = "10"
negative_int = "-10"

"""


@pytest.fixture
def test_config_file_path() -> Iterator[str]:
    with tempfile.TemporaryDirectory() as td:
        test_config_location = os.path.join(td, "test_config.toml")
        with open(test_config_location, "wb") as test_config:
            test_config.write(template)

        yield test_config_location


@pytest.fixture
def env_var_prefix() -> str:
    return "DOTCFG_TESTS"


@pytest.fixture
def env_vars(env_var_prefix: str) -> Dict[str, Any]:

    environment = {
        f"{env_var_prefix}__ENV_VARS__OVERWRITE_KEY": True,
        f"{env_var_prefix}__ENV_VARS__float": "7.5",
    }
    return environment
