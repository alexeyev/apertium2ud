"""
    In-tree PEP 517 build backend for apertium2ud.

    It guarantees that the package's data files

        apertium2ud/resources/tags_map.json
        apertium2ud/resources/<lang>.udx  (+ custom.udx)

    exist *before* setuptools collects `package_data`, so that a plain

        pip install .
        python -m build

    produces a wheel/sdist that already contains them -- even though those
    files are git-ignored and never committed.

    All the heavy lifting lives in `build_resources.py`; this module only hooks
    it into the standard setuptools backend.

    Behaviour notes / fallbacks:

    * If a `.udx` source is unavailable (submodule not checked out) but a
      previously-built `resources/custom.udx` already exists, the build does NOT
      fail -- it reuses what's there. This keeps `pip install` from a released
      sdist working, since the sdist ships the resources.
    * If the wiki cannot be scraped but a `tags_map.json` already exists, it is
      reused (same rationale).
"""

import os
import sys

from setuptools import build_meta as _orig

# Re-export the hooks setuptools' backend provides, so anything we don't
# override keeps working unchanged.
get_requires_for_build_wheel = _orig.get_requires_for_build_wheel
get_requires_for_build_sdist = _orig.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel

# Optional editable-install hooks (present on modern setuptools).
get_requires_for_build_editable = getattr(
    _orig, "get_requires_for_build_editable", None
)
prepare_metadata_for_build_editable = getattr(
    _orig, "prepare_metadata_for_build_editable", None
)

HERE = os.path.dirname(os.path.abspath(__file__))
RESOURCES = os.path.join(HERE, "apertium2ud", "resources")


def _resources_present() -> bool:
    have_map = os.path.isfile(os.path.join(RESOURCES, "tags_map.json"))
    have_udx = os.path.isfile(os.path.join(RESOURCES, "custom.udx"))
    return have_map and have_udx


def _ensure_resources() -> None:
    """ Build resources, tolerating offline / no-submodule situations when a
        previous build's artefacts are already present. """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)

    try:
        import build_resources
    except Exception as e:  # pragma: no cover - defensive
        if _resources_present():
            print(f"[_build_backend] could not import build_resources ({e}); "
                  f"reusing existing resources.", file=sys.stderr)
            return
        raise

    # Decide whether we can skip the wiki scrape (offline-friendly).
    have_map = os.path.isfile(os.path.join(RESOURCES, "tags_map.json"))

    try:
        build_resources.build(skip_wiki=have_map)
    except SystemExit as e:
        # build_resources raises SystemExit on missing .udx / wiki failures.
        if _resources_present():
            print(f"[_build_backend] resource (re)build skipped ({e}); "
                  f"reusing existing resources.", file=sys.stderr)
            return
        raise
    except Exception as e:
        if _resources_present():
            print(f"[_build_backend] resource (re)build failed ({e}); "
                  f"reusing existing resources.", file=sys.stderr)
            return
        raise


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _ensure_resources()
    return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    _ensure_resources()
    return _orig.build_sdist(sdist_directory, config_settings)


if get_requires_for_build_editable is not None:
    def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
        _ensure_resources()
        return _orig.build_editable(
            wheel_directory, config_settings, metadata_directory
        )
