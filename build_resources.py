"""
    Builds the resources that the `apertium2ud` package needs at import time:

      1. `apertium2ud/resources/tags_map.json`
            -- the machine-readable Apertium<->UD tag map, scraped from the
               Apertium wiki "List of symbols" page.

      2. `apertium2ud/resources/<lang>.udx` (one per configured language)
            -- copied verbatim from the corresponding Apertium language
               repository, which is vendored as a git submodule under
               `external/apertium-<lang>/`.

      3. `apertium2ud/resources/custom.udx`
            -- a copy of the DEFAULT language's `.udx`, kept under the historic
               name so that existing code / released behaviour keeps working.

    This module is intentionally dependency-light (only `requests`) and is
    invoked from two places:

      * the PEP 517 build backend (see `pyproject.toml` -> `_build_hook.py`),
        so that a plain `pip install .` / `python -m build` produces a wheel
        that already contains the resources; and

      * the CI workflow, so the same artefacts can be validated and tested.

    Run directly:

        python build_resources.py                # build all configured langs
        python build_resources.py --langs kir tat # subset
        python build_resources.py --skip-wiki     # only copy .udx files
"""

import argparse
import json
import os
import sys
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(HERE, "apertium2ud", "resources")
SUBMODULES_DIR = os.path.join(HERE, "external")

# The language whose .udx is packaged under the historic name `custom.udx`
# and treated as the default. Kyrgyz, since that is what the tool targets.
DEFAULT_LANG = "kir"

# Languages whose Apertium repos are vendored as submodules under external/.
# Add more here as submodules are added; the build will pick them up.
SUPPORTED_LANGS = ["kir", "kaz", "uig"]

# Languages whose Apertium repository does NOT ship a .udx file. We still allow
# selecting them at runtime, but they fall back to the generic wiki-scraped tag
# map (no language-specific overrides). They are listed here so the build does
# not attempt to copy a non-existent .udx, and so tooling can enumerate them.
#
# NB: these Apertium repos have no .udx upstream; language-specific rule sets
# would have to be authored separately and reviewed, so we do not invent them.
GENERIC_MAP_LANGS = ["tat", "tur", "uzb", "aze", "sah"]


def _udx_source_path(lang: str) -> str:
    """ Path to a language's .udx inside its vendored Apertium submodule. """
    repo = os.path.join(SUBMODULES_DIR, f"apertium-{lang}")
    candidate = os.path.join(repo, f"apertium-{lang}.{lang}.udx")
    return candidate


def build_tags_map(skip_wiki: bool = False) -> None:
    """ Scrape the Apertium wiki and write resources/tags_map.json. """
    target = os.path.join(RESOURCES_DIR, "tags_map.json")

    if skip_wiki:
        if os.path.exists(target):
            print(f"[build_resources] --skip-wiki: keeping existing {target}")
            return
        raise SystemExit(
            "[build_resources] --skip-wiki was given but no existing "
            f"tags_map.json found at {target}"
        )

    # Imported lazily so that --skip-wiki works without `requests` installed
    # and so importing this module never triggers a network call.
    from apertium_wiki_parser import scrape_tags

    print("[build_resources] scraping Apertium wiki 'List of symbols' ...")
    tags = scrape_tags()

    os.makedirs(RESOURCES_DIR, exist_ok=True)
    with open(target, "w", encoding="utf-8") as wf:
        json.dump(tags, wf, ensure_ascii=False)

    n_pos = len(tags.get("POS", {}))
    print(f"[build_resources] wrote {target} (top-level POS entries: {n_pos})")


def _sanitize_udx_text(text: str, lang: str) -> str:
    """ Repair known upstream .udx defects that would otherwise emit invalid
        UD output. Each repair is logged so it stays auditable, and this runs on
        a COPY (never on the vendored submodule file).

        Known issues handled:

        * A single UD feature given two comma-joined values, e.g.
          `Number[psor]=Plur,Sing`. UD feature values may not contain a comma;
          a comma-joined value means the analyser left the feature
          underspecified. The UD-correct resolution is to DROP that feature for
          the affected tag, so we strip such `Feat=A,B` tokens out.
          (Upstream ref: apertium-kir `px3sp` -> `Number[psor]=Plur,Sing`.)

        * A misspelled UD feature NAME with a single unambiguous correction.
          Only outright-invalid names are touched (values are left alone, since
          UD permits language-specific feature *values* such as `Tense=Aor` or
          `NumType=Coll`). Currently: `Reflexive=Yes` -> `Reflex=Yes`
          (the UD universal feature is `Reflex`; per the UD spec `Reflexive` is
          not a feature name). (Upstream ref: apertium-uig `ref`.) """
    import re

    # Unambiguous feature-NAME corrections (invalid name -> valid UD name).
    # Deliberately conservative: only misspelled names, never values.
    NAME_FIX = {"Reflexive": "Reflex"}

    out_lines = []
    n_dropped = 0
    n_renamed = 0
    # matches a feature token like `Name=Val1,Val2` (one or more commas)
    bad_feat = re.compile(r"(?<![|=])\b([A-Za-z]+(?:\[[a-z]+\])?)=([^|\t,]+(?:,[^|\t,]+)+)")

    for raw in text.splitlines():
        if not raw.strip():
            out_lines.append(raw)
            continue
        cols = raw.split("\t")
        # feature columns are 6.. (0-indexed); POS is col 5, tags are 0..4
        for ci in range(6, len(cols)):
            cell = cols[ci]
            if cell == "_":
                continue
            new_tokens = []
            for tok in cell.split("|"):
                # 1) drop comma-joined (underspecified) feature values
                if "," in tok and bad_feat.fullmatch(tok):
                    name = tok.split("=", 1)[0]
                    print(f"[build_resources] {lang}.udx: dropping invalid "
                          f"multi-valued feature '{tok}' (underspecified {name})")
                    n_dropped += 1
                    continue
                # 2) correct misspelled feature NAMES (values untouched)
                if "=" in tok:
                    name, val = tok.split("=", 1)
                    if name in NAME_FIX:
                        fixed = f"{NAME_FIX[name]}={val}"
                        print(f"[build_resources] {lang}.udx: renaming invalid "
                              f"feature '{tok}' -> '{fixed}'")
                        n_renamed += 1
                        tok = fixed
                new_tokens.append(tok)
            cols[ci] = "|".join(new_tokens) if new_tokens else "_"
        out_lines.append("\t".join(cols))

    if n_dropped or n_renamed:
        print(f"[build_resources] {lang}.udx: sanitized "
              f"{n_dropped} dropped, {n_renamed} renamed feature(s)")

    # preserve trailing newline behaviour of the source
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(out_lines) + suffix


def copy_udx_files(langs: List[str]) -> Dict[str, str]:
    """ Copy each configured language's .udx out of its submodule into
        resources/<lang>.udx. The DEFAULT_LANG is additionally copied to
        resources/custom.udx for backward compatibility.

        Returns a {lang: written_path} dict. """
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    written: Dict[str, str] = {}

    for lang in langs:
        src = _udx_source_path(lang)
        if not os.path.isfile(src):
            raise SystemExit(
                f"[build_resources] expected .udx for '{lang}' at:\n    {src}\n"
                f"  Is the submodule checked out? Try:\n"
                f"    git submodule update --init --recursive\n"
                f"  or add it:\n"
                f"    git submodule add https://github.com/apertium/apertium-{lang} "
                f"external/apertium-{lang}"
            )

        with open(src, "r", encoding="utf-8") as rf:
            udx_text = rf.read()
        udx_text = _sanitize_udx_text(udx_text, lang)

        dst = os.path.join(RESOURCES_DIR, f"{lang}.udx")
        with open(dst, "w", encoding="utf-8") as wf:
            wf.write(udx_text)
        written[lang] = dst
        print(f"[build_resources] copied {lang}.udx  <-  {os.path.relpath(src, HERE)}")

        if lang == DEFAULT_LANG:
            legacy = os.path.join(RESOURCES_DIR, "custom.udx")
            with open(legacy, "w", encoding="utf-8") as wf:
                wf.write(udx_text)
            print(f"[build_resources] copied custom.udx (default={DEFAULT_LANG})")

    if DEFAULT_LANG not in written:
        print(
            f"[build_resources] WARNING: default language '{DEFAULT_LANG}' was "
            f"not among the built languages {langs}; custom.udx not refreshed.",
            file=sys.stderr,
        )

    return written


def build(langs: List[str] = None, skip_wiki: bool = False) -> None:
    langs = langs or SUPPORTED_LANGS
    build_tags_map(skip_wiki=skip_wiki)
    copy_udx_files(langs)
    print("[build_resources] done.")


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build apertium2ud package resources.")
    p.add_argument(
        "--langs",
        nargs="+",
        default=SUPPORTED_LANGS,
        help=f"Languages to build .udx resources for (default: {SUPPORTED_LANGS}).",
    )
    p.add_argument(
        "--skip-wiki",
        action="store_true",
        help="Do not scrape the wiki; keep an existing tags_map.json.",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    build(langs=args.langs, skip_wiki=args.skip_wiki)
