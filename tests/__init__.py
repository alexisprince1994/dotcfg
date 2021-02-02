from dotcfg import Config

# Need to define a near empty config here to avoid
# weird mypy issues or setting an attribute that doesn't exist
config = Config({"env": "testing"})
