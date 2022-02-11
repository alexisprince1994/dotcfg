class ConfigurationError(Exception):
    """Base exception for all `dotcfg` exceptions"""


class UnsupportedFileType(ConfigurationError):
    """
    Raised when trying to read configuration from a
    file type who is not supported.
    """


class UnsupportedConfiguration(ConfigurationError):
    """
    Raised if the contents of a configuration file
    are unsupported in some way
    """
