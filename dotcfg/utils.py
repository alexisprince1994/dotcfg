from contextlib import contextmanager
from typing import Any, Dict, Iterator

from dotcfg.collections import Config


@contextmanager
def set_temporary_config(
    temp_config: Dict[str, Any], set_location: object, set_name: str = "config"
) -> Iterator:
    """
    Temporarily sets the configuration values for the duration of the
    context manager.

    Args:
        - temp_config (Dict[str, Any]): Dictionary containing (possibly nested)
            config keys and values. Nested keys should be supplied as `.`
            delimited strings.
        - set_location (object): Object to set the new configuration on
        - set_name (str): Attribute to set the new configuration on on the
            `set_location`.

    Example:

        ```python
        # Instead of `obj`, you'd typically provide your project's
        # top level package to attach to so your config can be
        # found at `my_package.config`.

        obj = object()
        with set_temporary_config({"first": 1, "nested.two": 2}, set_location=obj):
            obj.config.first  # 1
            obj.config.nested.two  # 2
        ```
    """

    # If a `Config` object isn't found at this location, create
    # an empty one to use as the default

    old_config = getattr(set_location, set_name).copy()

    try:

        for key, value in temp_config.items():
            # Handle dot-delimited strings for keys
            cfg = getattr(set_location, set_name)
            subkeys = key.split(".")
            for subkey in subkeys[:-1]:
                cfg = cfg.setdefault(subkey, Config())
            cfg[subkeys[-1]] = value
            # setattr(set_location, set_name, cfg)

        cfg = getattr(set_location, set_name)
        setattr(set_location, set_name, cfg)
        yield cfg

    finally:
        cfg = getattr(set_location, set_name)
        cfg.clear()
        cfg.update(old_config)
        setattr(set_location, set_name, cfg)
