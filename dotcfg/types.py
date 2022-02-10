from os import PathLike
from typing import Union

# Found the definition in stubs for the standard library. Goal is to
# support the same things that can be passed to `open`
StrPath = Union[str, PathLike[str]]
