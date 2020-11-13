# DotCfg
Dotcfg, or dot configuration, is a library to load configuration values into a dictionary which is `.` accessable. This is preferable to having something like a `constants.py` file, since you'd lose out on the ability to separate true constants from any runtime logic or have any namespacing.

## Quickstart
The `dotcfg` library uses `toml` files for configuration. To load a configuration object, see the example below assuming a minimal `toml` file with the following contents:

```toml

env = "DEVELOPMENT"

[constants]
assets_dir = "/some/file/system/path"
```

```python
from dotcfg import load_configuration

config = load_configuration(default_path="/path/to/config/file.toml")

# You can access these with nested dot notation
config.env # "DEVELOPMENT"
config.constants.assets_dir # "/some/file/system/path"

# You can also access like a dictionary with key notation
config["env"] # "DEVELOPMENT"
config["constants"]["assets_dir"] # "/some/file/system/path"
```

### Knobs and Levers

#### Multiple Configurations
It's not uncommon to have multiple sets of configurations, possibly one for each of a dev, test, and production environment. We can handle these by providing positional arguments to the `load_configuration` method, which will load each configuration, then overwrite any matching keys from previous configurations. Given the two `toml` files

```toml
# dev_config.toml

env = "DEVELOPMENT"

dev_only = true

[database]
user = "dev user"
password = "dev password"
host = "dev host"
port = "dev port"
db = "dev db"
```

```toml
# prod_config.toml

env = "PRODUCTION"

prod_only = true

[database]
user = "prod user"
password = "prod password"
host = "prod host"
port = "prod port"
db = "prod db"
```

Will load a python object like so:

```python
from dotcfg import load_configuration

# If there are overlapping keys, prefer the later positional argument
config = load_configuration("dev_config.toml", "prod_config.toml")

config.env # "PRODUCTION"

# However, keys that are defined in the first are still preserved
# if not overriden
config.dev_only # True
config.prod_only # True
```

##### Best Practices
A best practice for loading configurations across multiple environments are to have one "base" configuration, which contains all of the keys so it's easier for yourself and other developers to know which fields should be populated on the configuration object.

An example based on the above is:

```toml
# dev_config.toml

# Use as the default unless overriden
env = "DEVELOPMENT"

[database]
# You don't want your credentials, even for development, in version control
# but you do want to denote they will be populated either by another
# config file or environment variables
user = ""
password = ""
host = ""
port = ""
db = ""
```

Secondly, it's suggested you write light validation code for your configuration. It is easy to accidentally miss an underscore, have a typo, etc. that will contribute to very frustrating debugging. A good starting point is to have a function that just accesses all of the expected keys and sections, ensuring none of them error out.

#### Environment Variables
Environment variables are a core component of configuration. In order to support this, `dotcfg` requires specifying a `env_var_prefix` to read in environment variables. Typically, this `env_var_prefix` is the same name as your project. This prefix allows reading in some of the environment variables without polluting the configuration with unnecessary variables. The syntax is `PREFIX__[section]__[subsection]...[key]`. Variables / sections do not need to exist in a "base" config to be inserted as environment variables.

Examples of environment variables, assuming your `env_var_prefix` is `PROJ`.

The environment variables require your `env_var_prefix` as well as 2 underscores to be recognized:

* `PROJ_KEY` # Not loaded since we require 2 underscores
* `PROJ__KEY` # Okay, available at `config.key`

The `env_var_prefix` is case sensitive, but will always load your configuration as lowercase:

* `proj__key` # Not loaded since `PROJ` isn't found
* `PROJ__key` # Found and available at `config.key`

Sections are denoted with 2 underscores separating them

* `PROJ__DATABASE__USER` # Found, loaded at `config.database.user`
* `PROJ__DATABASE_USER` # Found, but loaded at `config.database_user`
* `PROJ__DATABASE__CREDENTIALS__USER` # Found, loaded at `config.database.credentials.user`


#### References
When writing configuration, it's very easy to end up with something that isn't DRY. To avoid this, we support references with the `${}` syntax. Nested references are done by `${section.subsection.key}`. If you reference something that doesn't exist, it will be populated with an empty string.

Example:

```toml
# dev_config.toml

env = "DEVELOPMENT"
# References the `env` key at the base level
env_copy = "${env}"

[constants]
dev = "DEVELOPMENT"
prod = "PRODUCTION"
test = "TESTING"

# Arrays can be made up of references
allowed_environments = ["${constants.dev}", "${constants.prod}", "${constants.test}"]

[services]
host = "0.0.0.0"

    [services.database]
    # References the `host` key nested within `services`
    host = "${services.host}"
    # Oops! No key, so this will be an empty string
    port = "${services.port}"
    
    [services.other_database]
    # References can reference references
    host = "${services.database.host}"
```
