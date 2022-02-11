from typing import Type

import pytest

from dotcfg.errors import (
    ConfigurationError,
    UnsupportedConfiguration,
    UnsupportedFileType,
)


@pytest.mark.parametrize("err", [UnsupportedFileType, UnsupportedConfiguration])
def test_subclass_of_project_error(err: Type[Exception]):

    with pytest.raises(ConfigurationError):
        raise err()
