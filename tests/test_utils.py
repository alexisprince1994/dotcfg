import functools

import pytest

import tests
from dotcfg.utils import set_temporary_config


class TestSetTemporaryConfig:
    def test_invent_new_settings(self):

        with pytest.raises(AttributeError):
            tests.config.setting

        with set_temporary_config({"setting": 1}, set_location=tests):
            assert tests.config.setting == 1

        with pytest.raises(AttributeError):
            tests.config.setting

    def test_overwrite_existing_settings(self):

        assert tests.config.env == "testing"

        with set_temporary_config({"env": "OVERRIDE"}, set_location=tests):
            assert tests.config.env == "OVERRIDE"

        assert tests.config.env == "testing"

    def test_nest_temp_configs(self):
        assert tests.config.env == "testing"

        with set_temporary_config({"env": "OVERRIDE"}, set_location=tests):
            assert tests.config.env == "OVERRIDE"

            with set_temporary_config({"env": "NESTED OVERRIDE"}, set_location=tests):
                assert tests.config.env == "NESTED OVERRIDE"

            assert tests.config.env == "OVERRIDE"

        assert tests.config.env == "testing"

    def test_set_multiple_keys(self):
        with set_temporary_config(
            {"env": "OVERRIDE", "other": True}, set_location=tests
        ):
            assert tests.config.env == "OVERRIDE"
            assert tests.config.other is True

    def test_set_nested_keys(self):
        with set_temporary_config(
            {"env": "OVERRIDE", "section.subsection.key": True}, set_location=tests
        ):
            assert tests.config.env == "OVERRIDE"
            assert tests.config.section.subsection.key is True


class TestPartialedTempConfig:
    def test_partials(self):
        stc = functools.partial(
            set_temporary_config, set_location=tests, set_name="config"
        )
        with stc({"env": "OVERRIDE"}):
            assert tests.config.env == "OVERRIDE"
