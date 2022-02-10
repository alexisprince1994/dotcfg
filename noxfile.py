import pathlib

from nox_poetry import Session, session

BLACK_PATHS = [
    "dotcfg",
    "tests",
    "noxfile.py",
]

DEFAULT_PYTHON_VERSION = "3.9"
PYTHON_VERSIONS = ["3.7", "3.8", "3.9", "3.10"]


CURRENT_DIRECTORY = pathlib.Path(__file__).parent.absolute()


@session(python=DEFAULT_PYTHON_VERSION)
def blacken(session: Session) -> None:
    """Runs the code formatter black"""
    session.install("black")
    session.run("black", *BLACK_PATHS)


@session(python=DEFAULT_PYTHON_VERSION)
def lint(session: Session) -> None:
    """Runs static code checks / linters."""
    session.install("mypy")
    # TODO: Cleanup codebase and enforce pylint rules

    session.run("mypy", "dotcfg")


@session
def tests(session: Session) -> None:
    """Runs the tests against the codebase."""

    # Package dependencies
    session.install(".")
    # Test running dependencies
    session.install("pytest")
    session.run("pytest", "tests")
