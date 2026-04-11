"""
Heavy packaging tests — require build tools and network access.
Run with:  pytest test/heavy/ -v
These are intentionally excluded from the fast unittest suite.
Each test builds a real wheel and installs it into a throw-away venv,
so they catch distribution bugs (missing sub-packages, missing data files, etc.)
that editable installs hide.
"""
import subprocess
import sys
import os
import tempfile
import shutil
import glob
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_wheel(tmp_dir: str) -> str:
    """Build a wheel from the current source tree; return the .whl path."""
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", tmp_dir, REPO_ROOT],
        check=True,
        capture_output=True,
    )
    wheels = glob.glob(os.path.join(tmp_dir, "*.whl"))
    assert wheels, "build produced no wheel"
    return wheels[0]


def _fresh_venv(tmp_dir: str) -> str:
    """Create a fresh venv and return the path to its Python interpreter."""
    venv_dir = os.path.join(tmp_dir, "venv")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, capture_output=True)
    python = os.path.join(venv_dir, "bin", "python")
    return python


@pytest.fixture(scope="module")
def installed_python():
    """
    Module-scoped fixture: build one wheel, create one venv, install fargv,
    yield the venv Python path.  Shared across all tests in this module so the
    build + install runs only once.
    """
    tmp = tempfile.mkdtemp(prefix="fargv_pkg_test_")
    try:
        wheel = _build_wheel(tmp)
        python = _fresh_venv(tmp)
        subprocess.run([python, "-m", "pip", "install", wheel],
                       check=True, capture_output=True)
        yield python
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_wheel_importable(installed_python):
    """
    The installed wheel must be importable from a clean venv with no access
    to the source tree (catches missing sub-packages like fargv.parameters).
    Added: 2026-04-11, initiated by: Anguelos.
    Regression: fargv.parameters sub-package was absent from setup.py packages
    list, so pip-installed users got ModuleNotFoundError on import.
    Reported by: rafaeldominiquini.
    """
    result = subprocess.run(
        [installed_python, "-c", "import fargv; print(fargv.__version__)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"import fargv failed in clean venv:\n{result.stderr}"
    )


def test_wheel_parse_runs(installed_python):
    """
    A minimal fargv.parse() call must work from a clean venv.
    Exercises that all internal imports (parameters, type_detection, parser, ...)
    resolve correctly after a wheel install.
    Added: 2026-04-11, initiated by: Anguelos.
    """
    script = (
        "import fargv; "
        "ns, _ = fargv.parse({'x': 1}, given_parameters=['prog', '--x=2'], "
        "auto_define_verbosity=False, auto_define_bash_autocomplete=False, "
        "auto_define_help=False, auto_define_user_interface=False, "
        "auto_define_config=False); "
        "assert ns.x == 2, ns.x"
    )
    result = subprocess.run(
        [installed_python, "-c", script],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"fargv.parse() failed in clean venv:\n{result.stderr}"
    )


def test_wheel_version_matches_source(installed_python):
    """
    The version reported by the installed wheel must match the version in
    fargv/version.py in the source tree.  Catches forgotten version bumps.
    Added: 2026-04-11, initiated by: Anguelos.
    """
    version_file = os.path.join(REPO_ROOT, "fargv", "version.py")
    _v = {}
    with open(version_file) as f:
        exec(f.read(), _v)
    source_version = _v["__version__"]

    result = subprocess.run(
        [installed_python, "-c", "import fargv; print(fargv.__version__)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    installed_version = result.stdout.strip()
    assert installed_version == source_version, (
        f"Wheel version {installed_version!r} != source version {source_version!r}"
    )


def test_all_subpackages_present(installed_python):
    """
    Every sub-package that exists in the source tree must be importable
    from the installed wheel.  Catches future sub-packages that get added
    to the source tree but are not declared in setup.py.
    Added: 2026-04-11, initiated by: Anguelos.
    """
    fargv_src = os.path.join(REPO_ROOT, "fargv")
    subpkgs = []
    for dirpath, dirnames, filenames in os.walk(fargv_src):
        if "__init__.py" in filenames:
            rel = os.path.relpath(dirpath, os.path.dirname(fargv_src))
            pkg = rel.replace(os.sep, ".")
            subpkgs.append(pkg)

    imports = "; ".join(f"import {p}" for p in subpkgs)
    result = subprocess.run(
        [installed_python, "-c", imports],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"Sub-package import failed:\n{result.stderr}\n"
        f"Packages checked: {subpkgs}"
    )
