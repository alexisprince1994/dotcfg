import json
import os
import pathlib
import tempfile
from typing import Type, cast

import pytest
import toml

from dotcfg import collections
from dotcfg.configuration import (
    interpolate_config,
    interpolate_env_vars,
    load_configuration,
    replace_variable_references,
    string_to_type,
    validate_config,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture(autouse=True)
def env(monkeypatch, temp_dir: str):

    project_name = "DOTCFG"
    monkeypatch.setenv("HOME", temp_dir)
    monkeypatch.setenv("PROJECT_NAME", project_name)
    monkeypatch.setenv(f"{project_name}__ENVIRONMENT", "TESTING")
    monkeypatch.setenv(
        f"{project_name}__TESTING_CONFIG_PATH", "$HOME/testing_config.toml"
    )
    monkeypatch.setenv(
        f"{project_name}__DEVELOPMENT_CONFIG_PATH", "$HOME/dev_config.toml"
    )
    monkeypatch.setenv(
        f"{project_name}__PRODUCTION_CONFIG_PATH", "$HOME/prod_config.toml"
    )
    monkeypatch.setenv(
        f"{project_name}__DEFAULT_CONFIG_PATH", "$HOME/default_config.toml"
    )

    yield temp_dir


@pytest.fixture
def testing_config_contents():
    return {
        "env": "TESTING",
        "database": {
            "user": "testing user",
            "password": "testing password",
            "host": "testing host",
            "port": "testing port",
            "db": "testing db",
        },
    }


@pytest.fixture
def testing_config(env, testing_config_contents: dict):
    project_name = os.environ.get("PROJECT_NAME")
    file_path = os.path.expanduser(
        os.path.expandvars(os.environ[f"{project_name}__TESTING_CONFIG_PATH"])
    )

    with open(file_path, "w") as f:
        toml.dump(testing_config_contents, f)

    yield file_path


class TestReplaceVariableReferences:
    def test_returns_unmodified_if_no_variable_references(self):
        config = {
            collections.CompoundKey(["a", "b"]): "foo",
            collections.CompoundKey(["a"]): "bar",
        }
        replaced = replace_variable_references(config)
        assert config == replaced

    def test_doesnt_modify_input(self):
        config = {
            collections.CompoundKey(["a", "b"]): "foo",
            collections.CompoundKey(["a"]): "${a.b}",
        }
        before_config = {
            collections.CompoundKey(["a", "b"]): "foo",
            collections.CompoundKey(["a"]): "${a.b}",
        }
        replaced = replace_variable_references(config)

        assert config == before_config
        assert config != replaced

    def test_replaces_root_variable(self):
        config = {
            collections.CompoundKey(["a"]): "${b}",
            collections.CompoundKey(["b"]): "foo",
        }
        replaced = replace_variable_references(config)

        assert (
            replaced[collections.CompoundKey(["a"])]
            == replaced[collections.CompoundKey(["b"])]
        )

    def test_replaces_multiple_existing_variables(self):
        config = {
            collections.CompoundKey(["a"]): "${b}",
            collections.CompoundKey(["b"]): "foo",
            collections.CompoundKey(["c"]): "bar",
            collections.CompoundKey(["d"]): "${c}",
        }
        replaced = replace_variable_references(config)
        assert (
            replaced[collections.CompoundKey(["a"])]
            == replaced[collections.CompoundKey(["b"])]
        )
        assert (
            replaced[collections.CompoundKey(["c"])]
            == replaced[collections.CompoundKey(["d"])]
        )

    def test_replaces_from_nested_to_root_keys(self):
        config = {
            collections.CompoundKey(["a", "b"]): "${b}",
            collections.CompoundKey(["b"]): "foo",
        }
        replaced = replace_variable_references(config)

        assert (
            replaced[collections.CompoundKey(["a", "b"])]
            == replaced[collections.CompoundKey(["b"])]
        )

    def test_replaces_from_root_to_nested_keys(self):
        config = {
            collections.CompoundKey(["a"]): "${a.b}",
            collections.CompoundKey(["a", "b"]): "foo",
        }
        replaced = replace_variable_references(config)

        assert (
            replaced[collections.CompoundKey(["a"])]
            == replaced[collections.CompoundKey(["a", "b"])]
        )

    def test_single_key_multiple_variables(self):
        same_values = "${b}-${b}"
        different_values = "${b}-${c}"
        config = {
            collections.CompoundKey(["a"]): same_values,
            collections.CompoundKey(["d"]): different_values,
            collections.CompoundKey(["b"]): "foo",
            collections.CompoundKey(["c"]): "bar",
        }
        replaced = replace_variable_references(config)
        assert replaced[collections.CompoundKey(["a"])] == "{val}-{val}".format(
            val=replaced[collections.CompoundKey(["b"])]
        )
        assert replaced[collections.CompoundKey(["d"])] == "{b}-{c}".format(
            b=replaced[collections.CompoundKey(["b"])],
            c=replaced[collections.CompoundKey(["c"])],
        )

    def test_chained_variables(self):
        config = {
            collections.CompoundKey(["a"]): "${b}",
            collections.CompoundKey(["b"]): "${c}",
            collections.CompoundKey(["c"]): "bar",
        }
        replaced = replace_variable_references(config)
        for value in replaced.values():
            assert value == "bar"

    def test_bad_reference_returns_empty_string(self):
        config = {
            collections.CompoundKey(["a"]): "${b}",
            collections.CompoundKey(["c"]): "bar",
            collections.CompoundKey(["d"]): "${c}",
        }
        replaced = replace_variable_references(config)
        assert replaced[collections.CompoundKey(["a"])] == ""
        # not modifying the other, valid entries
        assert replaced[collections.CompoundKey(["c"])] == "bar"
        assert (
            replaced[collections.CompoundKey(["d"])]
            == replaced[collections.CompoundKey(["c"])]
        )

    def test_self_reference_doesnt_cause_recursion_error(self):
        config = {
            collections.CompoundKey(["a"]): "${a}",
        }
        replaced = replace_variable_references(config)
        assert config == replaced

    def test_variable_reference_from_array(self):
        config = {
            collections.CompoundKey(["a"]): "foo",
            collections.CompoundKey(["b"]): ["${a}", "${a}", "${a}"],
        }

        replaced = replace_variable_references(config)
        assert replaced[collections.CompoundKey(["b"])] == [
            replaced[collections.CompoundKey(["a"])],
            replaced[collections.CompoundKey(["a"])],
            replaced[collections.CompoundKey(["a"])],
        ]

    def test_array_replacement_missing_variable(self):
        config = {
            collections.CompoundKey(["a"]): "foo",
            collections.CompoundKey(["b"]): ["${a}", "${a}", "${c}"],
        }

        replaced = replace_variable_references(config)

        assert replaced[collections.CompoundKey(["b"])] == [
            replaced[collections.CompoundKey(["a"])],
            replaced[collections.CompoundKey(["a"])],
            "",
        ]

    def test_array_replacement_nested_variable(self):
        config = {
            collections.CompoundKey(["a", "c"]): "foo",
            collections.CompoundKey(["b"]): ["${a.c}", "${a.c}", "${a.c}"],
        }

        replaced = replace_variable_references(config)
        assert replaced[collections.CompoundKey(["b"])] == [
            replaced[collections.CompoundKey(["a", "c"])],
            replaced[collections.CompoundKey(["a", "c"])],
            replaced[collections.CompoundKey(["a", "c"])],
        ]


class TestStringToType:
    @pytest.mark.parametrize(
        "string,expected",
        [
            ("True", True),
            ("False", False),
            ("true", True),
            ("false", False),
            ("TRUE", True),
            ("FALSE", False),
        ],
    )
    def test_bools(self, string: str, expected: bool):

        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected", [("1", 1), ("2", 2), ("0", 0), ("-1", -1)]
    )
    def test_integers(self, string: str, expected: int):

        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected",
        [
            ("1.0", 1.0),
            ("1.5", 1.5),
            ("2.0", 2.0),
            ("0.0", 0.0),
            ("-1.0", -1.0),
            ("-1.5", -1.5),
        ],
    )
    def test_floats(self, string: str, expected: float):
        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected",
        [("foo", "foo"), ("bar", "bar"), ("baz", "baz"), ("secret", "secret")],
    )
    def test_strings(self, string: str, expected: str):
        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected", [("1.0.1", "1.0.1"), ("1a", "1a"), ("[1, []", "[1, []")]
    )
    def test_malformed_primatives_are_strings(self, string: str, expected: str):
        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected",
        [
            ("[1, 2, 3]", [1, 2, 3]),
            ("[1, '2', 3]", [1, "2", 3]),
            ("['a', 'b', 'c']", ["a", "b", "c"]),
            ('[{"foo": "bar"}, {"bar": "baz"}]', [{"foo": "bar"}, {"bar": "baz"}]),
        ],
    )
    def test_lists(self, string: str, expected: list):
        result = string_to_type(string)
        assert result == expected

    @pytest.mark.parametrize(
        "string,expected",
        [
            ('{"key": "value", "other": 1}', {"key": "value", "other": 1}),
            (
                '{"key": ["value"], "other": {"nested": True}}',
                {"key": ["value"], "other": {"nested": True}},
            ),
        ],
    )
    def test_dicts(self, string: str, expected: dict):
        result = string_to_type(string)
        assert result == expected


class TestValidateConfig:
    def test_valid_config_does_nothing(self):

        config = collections.Config(key="value", foo=1)
        validate_config(config)

    def test_shadowed_attribute_raises_error(self):
        config = collections.Config(key="value", items="error!")
        with pytest.raises(ValueError):
            validate_config(config)


class TestInterpolateEnvVars:
    @pytest.mark.parametrize(
        "regular_value", ["TESTING", "$NOT_A_VARIABLE", "ENVIRONMENT", "FOO", "bar"]
    )
    def test_does_nothing_if_doesnt_need_interpolation(self, regular_value: str):

        result = cast(str, interpolate_env_vars(regular_value))
        assert result == regular_value

    def test_expands_variables(self, testing_config):

        testing_config_path = os.environ.get(
            f"{os.environ.get('PROJECT_NAME')}__TESTING_CONFIG_PATH"
        )
        home = os.environ.get("HOME")
        result = cast(str, interpolate_env_vars(testing_config_path))
        assert "$HOME" not in result
        assert os.path.isfile(result)

    def test_expands_home(self, monkeypatch):
        home = os.environ.get("HOME")
        result = interpolate_env_vars("$HOME")
        assert home == result

    def test_expands_multiple_variables(self):

        result = cast(str, interpolate_env_vars("$HOME/$PROJECT_NAME"))
        assert "$HOME" not in result
        assert "$PROJECT_NAME" not in result


class TestInterpolateConfig:
    def test_ignores_environment_if_not_provided(self, monkeypatch):
        monkeypatch.setenv("DOTCFG__SETTING", "FOO")
        config = {"setting": "BAR"}
        cfg = interpolate_config(config)
        assert cfg.setting == "BAR"

    def test_reads_env_if_provided(self, monkeypatch):
        monkeypatch.setenv("DOTCFG__SETTING", "FOO")
        cfg = interpolate_config({}, env_var_prefix="DOTCFG")
        assert cfg.setting == "FOO"

    def test_overwrites_from_env(self, monkeypatch):
        monkeypatch.setenv("DOTCFG__SETTING", "FOO")
        config = {"setting": "BAR"}
        cfg = interpolate_config(config, env_var_prefix="DOTCFG")
        assert cfg.setting == "FOO"

    def test_replaces_references(self):
        config = {"x": 1, "y": "${x}"}

        cfg = interpolate_config(config)
        assert cfg.x == 1
        assert cfg.y == 1

    def test_doesnt_replace_references(self):

        config = {"x": 1, "y": "${x}"}
        cfg = interpolate_config(config, replace_references=False)
        assert cfg.x == 1
        assert cfg.y == "${x}"

        second = interpolate_config(cfg, replace_references=True)
        assert second.x == 1
        assert second.y == second.x


class TestLoadConfiguration:
    def test_prefers_env_vars(self, monkeypatch, testing_config: str):

        monkeypatch.setenv("DOTCFG__ENV", "OVERRIDE")

        config = load_configuration(testing_config, env_var_prefix="DOTCFG")
        assert config.env == "OVERRIDE"

    @pytest.mark.parametrize("input_type", [str, pathlib.Path])
    def test_reads_from_str_or_path(self, testing_config: str, input_type: Type):

        config_location = input_type(testing_config)
        config = load_configuration(config_location)
        assert config.env == "TESTING"

    def test_reads_json_file(self, testing_config_contents: dict, temp_dir: str):

        location = os.path.join(temp_dir, "testing_config.json")
        with open(location, "w") as f:
            json.dump(testing_config_contents, f)

        config = load_configuration(location)
