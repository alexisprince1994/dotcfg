import os
import shlex
import subprocess


def test_black_formatting():
    # make sure we're in the right place
    assert __file__.endswith("/tests/test_formatting.py")
    project_dir = os.path.dirname(os.path.dirname(__file__))
    result = subprocess.call(shlex.split("black --check {}".format(project_dir)))
    assert result == 0, "Repo did not pass Black formatting!"


def test_mypy():
    # make sure we're in the right place
    assert __file__.endswith("/tests/test_formatting.py")
    project_dir = os.path.dirname(os.path.dirname(__file__))
    config_file = os.path.join(project_dir, "setup.cfg")
    result = subprocess.call(
        shlex.split("mypy --config-file {} {}".format(config_file, project_dir))
    )
    assert result == 0, "Repo did not pass mypy type checks!"
