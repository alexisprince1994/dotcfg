import os
import subprocess

import dotcfg


def test_version():
    """
    Tests that the version in the code matches the version
    provided in the package information
    """
    current_version = dotcfg.__version__

    cwd = os.path.join(os.path.dirname(__file__))
    cmd = ["poetry", "version"]
    # output will be b"dotcfg X.Y.Z\n"
    poetry_version = subprocess.check_output(cmd, cwd=cwd).strip().decode()
    package_version = poetry_version.replace("dotcfg ", "")

    assert package_version == current_version
