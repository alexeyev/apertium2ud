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


def _wiki_mapped_tags():
    """ Set of Apertium tags that the wiki 'List of symbols' map assigns a
        non-empty UD mapping (a POS and/or at least one feature). Read from the
        already-generated resources/tags_map.json (build_tags_map runs first).
        Used to decide which empty-override .udx rows actually suppress a real
        wiki mapping (e.g. tv/iv) versus which are deliberately featureless. """
    path = os.path.join(RESOURCES_DIR, "tags_map.json")
    mapped = set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return mapped

    def _valid_mapping(v):
        """ True if this leaf maps to a POS and/or features, and none of its
            feature values is a comma-joined (invalid UD) value. A comma value
            means the wiki entry itself is defective (e.g. mf -> Gender=Masc,Fem);
            such overrides are left in place rather than resurrected. """
        if not (v.get("tags") or v.get("feats")):
            return False
        for feat in v.get("feats") or []:
            if "=" in feat and "," in feat.split("=", 1)[1]:
                return False
        return True

    def walk(d):
        if not isinstance(d, dict):
            return
        for k, v in d.items():
            if isinstance(v, dict):
                if v.get("t") and _valid_mapping(v):
                    mapped.add(k)
                walk(v)

    walk(data)
    return mapped


_WIKI_MAPPED_TAGS = set()  # populated at build time by copy_udx_files


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
    n_empty_override = 0
    # matches a feature token like `Name=Val1,Val2` (one or more commas)
    bad_feat = re.compile(r"(?<![|=])\b([A-Za-z]+(?:\[[a-z]+\])?)=([^|\t,]+(?:,[^|\t,]+)+)")

    for raw in text.splitlines():
        if not raw.strip():
            out_lines.append(raw)
            continue
        cols = raw.split("\t")

        # Drop "empty-override" rows ONLY where they suppress a mapping the wiki
        # "List of symbols" actually defines. A single-tag row mapping the tag to
        # NO UD POS and NO features (cols 5.. all "_") erases the wiki entry for
        # that tag in the forward direction, even though ud2a still maps it in
        # reverse. The clear case is <tv>/<iv>: the wiki documents
        # tv -> Subcat=Tran and iv -> Subcat=Intr, so a2ud (empty) and ud2a
        # (Subcat) disagree. Removing only these wiki-backed overrides makes the
        # directions symmetric WITHOUT resurrecting tags the maintainer
        # deliberately suppressed (e.g. proper-noun subtypes <al>/<ant>/<org>...
        # which the wiki itself leaves featureless).
        if len(cols) >= 8:
            tag_cols = [c for c in cols[:5] if c != "_"]
            result_cols = [c for c in cols[5:] if c != "_"]
            if (len(tag_cols) == 1 and not result_cols
                    and tag_cols[0] in _WIKI_MAPPED_TAGS):
                print(f"[build_resources] {lang}.udx: dropping empty-override "
                      f"row for <{tag_cols[0]}> (wiki maps it; lets it through)")
                n_empty_override += 1
                continue

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

    if n_dropped or n_renamed or n_empty_override:
        print(f"[build_resources] {lang}.udx: sanitized "
              f"{n_dropped} dropped, {n_renamed} renamed, "
              f"{n_empty_override} empty-override row(s) removed")

    # preserve trailing newline behaviour of the source
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(out_lines) + suffix


def _supplementary_rules(lang: str) -> str:
    """ Extra .udx rows for tags that are missing from BOTH the wiki map and the
        upstream .udx, but have an unambiguous, spec-grounded UD mapping. Only
        clearly-standard UD mappings are added; tags whose correct UD feature is
        a genuine judgement call (apertium-kir's advl, mod_ind, ger_ppot,
        prc_pcond, prc_plan) are intentionally NOT added (see issue #1).

        Columns: 5 Apertium tag-group cols, 1 UD POS col, 2 UD feature cols. """
    if lang != "kir":
        return ""
    rows = [
        ("equ", "Case=Equ"),       # equative case; Case=Equ is standard UD,
                                   # attested in UD_Kyrgyz-KTMU
        ("prc_irre", "Mood=Irr"),  # irrealis; Mood=Irr is standard UD
    ]
    print(f"[build_resources] {lang}.udx: appended {len(rows)} supplementary "
          f"rule(s) for tags missing upstream (equ, prc_irre)")
    return "".join(f"_\t_\t{tag}\t_\t_\t_\t{feat}\t_\n" for tag, feat in rows)


def copy_udx_files(langs: List[str]) -> Dict[str, str]:
    """ Copy each configured language's .udx out of its submodule into
        resources/<lang>.udx. The DEFAULT_LANG is additionally copied to
        resources/custom.udx for backward compatibility.

        Returns a {lang: written_path} dict. """
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    written: Dict[str, str] = {}

    # Compute once: which tags the wiki map actually maps (used by the sanitiser
    # to decide which empty-override rows suppress a real mapping, e.g. tv/iv).
    global _WIKI_MAPPED_TAGS
    _WIKI_MAPPED_TAGS = _wiki_mapped_tags()

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
        supplement = _supplementary_rules(lang)
        if supplement:
            if not udx_text.endswith("\n"):
                udx_text += "\n"
            udx_text += supplement

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
