"""
    Integrity tests for the generated resource files:

        apertium2ud/resources/tags_map.json
        apertium2ud/resources/custom.udx  (+ <lang>.udx)

    These guard the build output itself, independently of the conversion code.
"""

import json
import os

import pytest

RESOURCES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "apertium2ud", "resources",
)


# --------------------------------------------------------------------------- #
#  tags_map.json
# --------------------------------------------------------------------------- #

def test_tags_map_exists_and_parses():
    path = os.path.join(RESOURCES, "tags_map.json")
    assert os.path.isfile(path), "tags_map.json must be built before tests"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "POS" in data, "tag map must contain a POS section"
    assert isinstance(data["POS"], dict) and data["POS"]


# --------------------------------------------------------------------------- #
#  .udx files
# --------------------------------------------------------------------------- #

def _udx_files():
    return [
        os.path.join(RESOURCES, n)
        for n in os.listdir(RESOURCES)
        if n.endswith(".udx")
    ]


def test_at_least_default_udx_present():
    assert os.path.isfile(os.path.join(RESOURCES, "custom.udx")), \
        "the default (kir) custom.udx must be present"


@pytest.mark.parametrize("path", _udx_files() or [os.path.join(RESOURCES, "custom.udx")])
def test_udx_has_eight_columns(path):
    """ Every non-empty .udx row must have exactly 8 tab-separated columns:
        5 Apertium tag-group columns, 1 UD POS column, 2 UD feature columns. """
    assert os.path.isfile(path), f"missing {path}"
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            assert len(cols) == 8, \
                f"{os.path.basename(path)} line {i}: expected 8 columns, got {len(cols)}"


@pytest.mark.parametrize("path", _udx_files() or [os.path.join(RESOURCES, "custom.udx")])
def test_udx_feature_values_have_no_commas(path):
    """ No UD feature token may carry a comma-joined value (Feat=A,B). """
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            for ci in range(6, len(cols)):
                cell = cols[ci]
                if cell == "_":
                    continue
                for tok in cell.split("|"):
                    if "=" in tok:
                        value = tok.split("=", 1)[1]
                        assert "," not in value, (
                            f"{os.path.basename(path)} line {i}: "
                            f"comma in feature value {tok!r}"
                        )


@pytest.mark.parametrize("path", _udx_files() or [os.path.join(RESOURCES, "custom.udx")])
def test_udx_feature_names_are_valid_ud(path):
    """ No UD feature token may use an unknown feature NAME. UD permits
        language-specific feature *values* (e.g. Tense=Aor, NumType=Coll), so
        only names are checked here. Guards the `Reflexive` -> `Reflex`
        sanitisation (apertium-uig) from regressing. """
    ud_feature_names = {
        "PronType", "NumType", "Poss", "Reflex", "Foreign", "Abbr", "Typo",
        "Gender", "Animacy", "NounClass", "Number", "Case", "Definite",
        "Degree", "VerbForm", "Mood", "Tense", "Aspect", "Voice", "Evident",
        "Polarity", "Person", "Polite", "Clusivity", "Deixis", "DeixisRef",
        "PartType", "Style", "NumForm", "ExtPos", "Echo", "Advlz", "Nomzr",
        "Int", "Subcat",
    }
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            for ci in range(6, len(cols)):
                if cols[ci] == "_":
                    continue
                for tok in cols[ci].split("|"):
                    if "=" in tok:
                        name = tok.split("=", 1)[0].split("[")[0]
                        assert name in ud_feature_names, (
                            f"{os.path.basename(path)} line {i}: "
                            f"unknown UD feature name {name!r} in {tok!r}"
                        )
    """ The UD POS column (index 5) must be '_' or an UPPERCASE UD POS tag. """
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            pos = cols[5]
            if pos == "_":
                continue
            assert pos.isupper(), \
                f"{os.path.basename(path)} line {i}: POS {pos!r} is not uppercase"
