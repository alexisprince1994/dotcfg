import os
import re
from ast import literal_eval
from typing import Any, Dict, List, Optional, Union, cast

import toml

from dotcfg import collections

INTERPOLATION_REGEX = re.compile(r"\${(.[^${}]*)}")


def load_toml(path: str) -> dict:
    """
    Loads a config dictionary from TOML
    """
    return {
        key: value
        for key, value in toml.load(cast(str, interpolate_env_vars(path))).items()
    }


def interpolate_config(
    config: dict, env_var_prefix: Optional[str] = None
) -> collections.Config:
    """
    Processes the initial input configuration and replaces
    system variables ($PROJECT_PATH, etc.) as well as our
    custom variables ("${}" syntax).

    Args:
        - config (dict): Loaded data from a configuration file
        - env_var_prefix (Optional[str]): Environment variable prefix to
            load from the current environment.

    Returns:
        - collections.Config: Configuration object with values populated
            and accessible via dot notation or dictionary notation.
    """

    # Toml & other file formats support nested
    # dictionaries, so we need to flatten them out
    # to avoid recursive checking when interpolating
    flat_config = collections.dict_to_flatdict(config)

    if env_var_prefix is not None:
        env_vars = load_environment_variables(env_var_prefix)

    # Interpolate any environment variables referenced
    for key, value in list(flat_config.items()):
        value = interpolate_env_vars(value)
        if isinstance(value, str):
            value = string_to_type(value)

        flat_config[key] = value

    flat_config = replace_variable_references(flat_config)
    return cast(
        collections.Config,
        collections.flatdict_to_dict(flat_config, dct_class=collections.Config),
    )


def replace_variable_references(flat_config: dict) -> dict:
    """
    Given a dictionary (with CompoundKeys as keys), we replace
    the references to other keys (with ${} syntax) with the
    actual values

    Args:
        - flat_config (dict): A dictionary containing
            collections.CompoundKey values as keys

    Returns:
        - dict: The updated (modified) dictionary that
            replaces variable references with the values
            existing elsewhere in the configuration
    """

    def check_and_replace(flat_config: dict, value: str) -> Optional[str]:
        match = INTERPOLATION_REGEX.search(value)
        if not match:
            return None

        # the matched_string includes "${}"; the matched_key is just the inner value
        matched_string = match.group(0)
        matched_key = match.group(1)

        # get the referenced key from the config value
        ref_key = collections.CompoundKey(matched_key.split("."))
        # get the value corresponding to the referenced key
        ref_value = flat_config.get(ref_key, "")

        # The configuration's value was just a reference and nothing else
        if value == matched_string:
            return ref_value

        # The reference wasn't a valid reference, so to maintain consistency
        # with the rest of the config API, a missing reference returns an
        # empty string

        # The value could either have multiple references, or
        # be used to interpolate a larger string, such
        # as a database URI or API request header
        # Ex1) "postgresql+psycopg2://${username}:${password}@{host}:${port}/${dbname}"
        # Ex2) "Bearer ${api_token}"
        return value.replace(matched_string, str(ref_value), 1)

    output = flat_config.copy()
    keys_to_check = set(output.keys())

    # Since each string variable reference could have more than one
    # reference, we iterate 10 times to avoid recursive hells and
    # to not end up in an infinite loop.
    for _ in range(10):

        # iterate over every key and value to check if the value uses variable references
        for k in list(keys_to_check):
            value = output[k]
            # Only removing from `keys_to_check` when the value
            # can't possibly be a reference (not a string) or when
            # there's no match, because we'll eventually run out of references
            # since we're iteratively replacing 10 times.

            # if the value isn't a string, it can't be a reference, so we exit
            if not isinstance(value, (str, list)):
                keys_to_check.remove(k)
                continue

            if isinstance(value, str):
                new_value = check_and_replace(flat_config=flat_config, value=value)
                # None specifically means there was no regex match, so a regular string
                # (not a reference to a missing key)
                if new_value is None:
                    keys_to_check.remove(k)
                    continue
                output[k] = new_value
            else:
                new_values: List[Any] = []
                for item in value:
                    if not isinstance(item, str):
                        new_values.append(item)
                        continue

                    interpolated = check_and_replace(flat_config=output, value=item)
                    # Explicit None check because we need to append empty strings
                    # that denote correct variable lookup syntax but missing
                    # reference
                    if interpolated is not None:
                        new_values.append(interpolated)
                    else:
                        new_values.append(item)

                # Only remove from the interation once the
                # values are the same before and after replacing
                if value == new_values:
                    keys_to_check.remove(k)

                output[k] = new_values

    return output


def load_environment_variables(
    env_var_prefix: str,
) -> Dict[collections.CompoundKey, Any]:

    flat_config = {}

    for env_var, env_var_value in os.environ.items():
        if not env_var.startswith(env_var_prefix + "__"):
            continue

        # Strips the prefix off the environment variable
        env_var_option = env_var[len(env_var_prefix + "__") :]

        # Make sure the result has at least one delimited section
        # with a key
        if "__" not in env_var:
            continue

        # Env vars with escaped characters are interpreted as a
        # literal "\", which Python helpfuly escaped with a second "\".
        # This step makes sure that the escaped characters are properly
        # interpreted.
        value = cast(str, env_var_value.encode().decode("unicode_escape"))

        # Place the environment variable into the flat config
        # as the compound key
        config_option = collections.CompoundKey(env_var_option.lower().split("__"))
        flat_config[config_option] = string_to_type(
            cast(str, interpolate_env_vars(value))
        )

    return flat_config


def interpolate_env_vars(
    env_var: Optional[str],
) -> Optional[Union[bool, int, float, str]]:
    """
    Expands (potentially nested) env vars by repeatedly applying
    `expandvars` and `expanduser` until interpolation stops having
    any effect.

    Args:
        - env_var (Optional[str]): Value that potentially has references
            to system variables

    Returns:
        - Optional[Union[bool, int, float, str]]: Value with references
            to system variables expanded; cast to appropriate python types.
    """
    if not env_var or not isinstance(env_var, str):
        return env_var

    counter = 0

    while counter < 10:
        interpolated = os.path.expanduser(os.path.expandvars(str(env_var)))
        if interpolated == env_var:
            # if a change was made, apply string-to-type casts; otherwise leave alone
            # this is because we don't want to override TOML type-casting if this function
            # is applied to a non-interpolated value
            if counter > 1:
                interpolated = string_to_type(interpolated)  # type: ignore
            return interpolated
        else:
            env_var = interpolated
        counter += 1

    return None


def string_to_type(value: str) -> Any:
    """
    Given a value read from the environment (which is always a string),
    loads the value into the correct python primative.

    Args:
        - value (str): Value read from the environment

    Returns:
        - Any: Python primative loaded. If not loadable into a more
            fitting primative, returned as a string.
    """
    if value.upper() == "TRUE":
        return True
    elif value.upper() == "FALSE":
        return False

    try:
        return literal_eval(value)
    except Exception:
        pass

    return value


def validate_config(config: collections.Config) -> None:
    """
    Validates that the configuration file is valid.
        - keys do not shadow Config methods
    Note that this is performed when the config is first loaded, but not after.
    """

    def check_valid_keys(config: collections.Config) -> None:
        """
        Recursively check that keys do not shadow methods of the Config object
        """
        invalid_keys = dir(collections.Config)
        for k, v in config.items():
            if k in invalid_keys:
                raise ValueError(
                    (
                        f'Invalid config key: "{k}".'
                        " Using this name will overlap with the configuration object's"
                        " attribute, resulting in undefined behavior."
                    )
                )
            if isinstance(v, collections.Config):
                check_valid_keys(v)

    check_valid_keys(config)


def load_configuration(
    default_path: str, *paths: str, env_var_prefix: Optional[str] = None
) -> collections.Config:
    """
    Main entrypoint to loading a configuration set.

    Args:
        - default_path (str): Path containing location to configuration
            with default values
        - *paths (str): Positional paths that contain configuration items
            that overwrite (in priority order) the previous configuration.
        - env_var_prefix (Optional[str]): An environment variable prefix
            to read values from. Environment variables with naming convention
            "<prefix>__[<optional section>]__[<optional subsection>]__key"

    Returns:
        - collections.Config: Dictionary supporting dot access
    """
    default_config = load_toml(default_path)

    # For each specified path, we assume that the later they are in the
    # provided argument list, the higher priority they are, with
    # environment variables having the highest priority.

    for path in paths:
        try:
            config_chunk = load_toml(path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Configuration file {path} was specified but does not exist."
            ) from exc

        default_config = cast(
            dict, collections.merge_dicts(default_config, config_chunk)
        )

    config = interpolate_config(default_config, env_var_prefix=env_var_prefix)

    validate_config(config)
    return config
