"""
    Test suite for apertium2ud.

    These tests assume the package resources have been built, i.e.

        python build_resources.py        # (or a `pip install .`)

    has produced:

        apertium2ud/resources/tags_map.json
        apertium2ud/resources/custom.udx

    The CI workflow runs the resource build before invoking pytest.
"""

import re

import pytest

# --------------------------------------------------------------------------- #
#  Import / smoke
# --------------------------------------------------------------------------- #

def test_package_imports():
    import apertium2ud  # noqa: F401
    from apertium2ud import feats2set  # noqa: F401
    from apertium2ud.convert import a2ud, ud2a  # noqa: F401


def test_resources_loaded():
    import apertium2ud
    assert apertium2ud.RAW_WIKI_MAP, "wiki tag map should be non-empty"
    assert apertium2ud.default_udx_mapping is not None, \
        "custom.udx rules should have been packaged and loaded"
    assert len(apertium2ud.POS_TAGS_LIST) > 0


# --------------------------------------------------------------------------- #
#  Apertium -> UD (a2ud), Kyrgyz analyses
# --------------------------------------------------------------------------- #

def test_a2ud_simple_noun():
    from apertium2ud.convert import a2ud
    upos, feats = a2ud(["n", "pl", "acc"])
    assert upos == ["NOUN"]
    assert "Number=Plur" in feats
    assert "Case=Acc" in feats


def test_a2ud_adjective():
    from apertium2ud.convert import a2ud
    upos, _ = a2ud(["adj"])
    assert upos == ["ADJ"]


def test_a2ud_punctuation():
    from apertium2ud.convert import a2ud
    upos, _ = a2ud(["sent"])
    assert upos == ["PUNCT"]


def test_a2ud_pronoun_demonstrative():
    # бул<prn><dem><nom>  -- from apertium-kir's own README example
    from apertium2ud.convert import a2ud
    upos, feats = a2ud(["prn", "dem", "nom"])
    assert upos == ["PRON"]
    assert "PronType=Dem" in feats
    assert "Case=Nom" in feats


def test_a2ud_verbal_noun():
    # талда<v><tv><ger><nom> ("талдоо")
    from apertium2ud.convert import a2ud
    upos, feats = a2ud(["v", "tv", "ger", "nom"])
    assert "VERB" in upos
    # ger -> VerbForm (Ger per the .udx rules)
    assert any(f.startswith("VerbForm=") for f in feats)


# --------------------------------------------------------------------------- #
#  Regression: no invalid (comma-joined) UD feature VALUES
# --------------------------------------------------------------------------- #

_FEATURE_VALUE = re.compile(r"^[A-Za-z0-9\[\]]+=[A-Za-z0-9]+$")


@pytest.mark.parametrize("tags", [
    ["n", "px3sp", "nom", "sg", "p3"],   # the historic Number[psor]=Plur,Sing bug
    ["n", "px3sg", "sg", "dat", "p3"],
    ["n", "px3pl", "sg", "gen", "p3"],
    ["num", "ord"],                       # the NumType=Card,Ord bug
])
def test_a2ud_no_comma_joined_feature_values(tags):
    """ UD feature values may never contain a comma. """
    from apertium2ud.convert import a2ud
    _, feats = a2ud(tags)
    for f in feats:
        assert "," not in f, f"comma-joined feature value produced: {f!r}"


def test_px3sp_underspecified_number_dropped():
    """ px3sp is number-underspecified -> it must NOT assert a possessor number,
        but must still carry Person[psor]=3. """
    from apertium2ud.convert import a2ud
    _, feats = a2ud(["n", "px3sp", "nom", "sg", "p3"])
    assert "Person[psor]=3" in feats
    assert not any(f.startswith("Number[psor]=") for f in feats), \
        "px3sp should not assert a possessor Number"


def test_px3sg_keeps_singular_possessor():
    """ The fix must not over-reach: px3sg keeps Number[psor]=Sing. """
    from apertium2ud.convert import a2ud
    _, feats = a2ud(["n", "px3sg", "sg", "dat", "p3"])
    assert "Number[psor]=Sing" in feats


# --------------------------------------------------------------------------- #
#  UD -> Apertium (ud2a)
# --------------------------------------------------------------------------- #

def test_ud2a_returns_candidates():
    from apertium2ud import feats2set
    from apertium2ud.convert import ud2a
    feats = feats2set({"Case": "Nom", "Number": "Sing", "Person": "3"})
    result = ud2a("NOUN", feats)
    assert isinstance(result, list)
    # 'n' should be among the suggested Apertium tag groups somewhere
    flat = {t for group in result for t in group}
    assert "n" in flat


def test_feats2set_handles_none():
    from apertium2ud import feats2set
    assert feats2set(None) == set()
    assert feats2set({"Case": "Nom"}) == {"Case=Nom"}


# --------------------------------------------------------------------------- #
#  Determinism
# --------------------------------------------------------------------------- #

def test_tv_iv_convert_and_are_symmetric():
    """ Issue #1: tv/iv were dropped by a2ud while ud2a still mapped them.
        a2ud must now emit Subcat (matching the wiki + ud2a), in both directions. """
    from apertium2ud import feats2set
    from apertium2ud.convert import a2ud, ud2a

    # forward
    _, tv_feats = a2ud(["tv"], disable_undocumented_tags_warnings=True)
    _, iv_feats = a2ud(["iv"], disable_undocumented_tags_warnings=True)
    assert "Subcat=Tran" in tv_feats
    assert "Subcat=Intr" in iv_feats

    # backward (was already working; assert it stays consistent)
    tran = {t for g in ud2a("VERB", feats2set({"Subcat": "Tran"})) for t in g}
    intr = {t for g in ud2a("VERB", feats2set({"Subcat": "Intr"})) for t in g}
    assert "tv" in tran
    assert "iv" in intr


def test_mf_stays_suppressed():
    """ The empty-override removal must NOT resurrect tags whose wiki mapping is
        itself invalid: mf -> Gender=Masc,Fem (a comma value) must stay dropped,
        so no invalid UD feature value is produced. """
    from apertium2ud.convert import a2ud
    _, feats = a2ud(["n", "mf"], disable_undocumented_tags_warnings=True)
    assert not any("," in f for f in feats)
    assert "Gender=Masc,Fem" not in feats


def test_report_unmapped_surfaces_undocumented_tags():
    """ Issue #1: undocumented apertium-kir subtags should be surfaceable. """
    from apertium2ud.convert import a2ud
    _, _, unmapped = a2ud(
        ["v", "ger_ppot", "prc_plan", "p3"],
        report_unmapped=True, disable_undocumented_tags_warnings=True,
    )
    assert "ger_ppot" in unmapped
    assert "prc_plan" in unmapped
    assert "p3" not in unmapped


def test_report_unmapped_is_opt_in():
    from apertium2ud.convert import a2ud
    assert len(a2ud(["n", "pl"])) == 2


def test_supplementary_equ_prc_irre():
    """ Issue #1: equ -> Case=Equ and prc_irre -> Mood=Irr (spec-grounded). """
    from apertium2ud.convert import a2ud
    assert "Case=Equ" in a2ud(["n", "equ"])[1]
    assert "Mood=Irr" in a2ud(["v", "prc_irre"])[1]


def test_a2ud_is_deterministic():
    from apertium2ud.convert import a2ud
    tags = ["n", "px3sg", "sg", "dat", "p3"]
    first = a2ud(tags)
    for _ in range(5):
        assert a2ud(tags) == first


def test_bounded_powerset_matches_unbounded():
    """ The bounded powerset (subsets capped at the largest rule-key size) must
        produce exactly the same output as an unbounded powerset would. Guards
        the performance optimisation in a2ud against changing behaviour. """
    from itertools import chain, combinations

    import apertium2ud
    from apertium2ud.convert import a2ud

    rules = apertium2ud.APERTIUM2UD_RULES
    pos = apertium2ud.POS_TAGS_SET

    def a2ud_unbounded(tags):
        ft, seen = [], False
        for t in tags:
            if t in pos:
                if not seen:
                    ft.append(t)
                    seen = True
            else:
                ft.append(t)
        s = ft
        all_subsets = chain.from_iterable(
            combinations(s, r) for r in range(len(s), 0, -1)
        )
        rt, rf = [], []
        for sub in all_subsets:
            sub = frozenset(sub)
            if sub not in rules:
                continue
            for rule in rules[sub]:
                rt.extend(rule.get("tag", []))
                rf.extend(rule.get("feats", []))
        return list(dict.fromkeys(rt)), list(dict.fromkeys(rf))

    # Long readings are where the two could diverge; check several.
    samples = [
        ["n", "px3sp", "nom", "sg", "p3"],
        ["vblex", "past3p", "past", "p3", "perf", "pl"],
        ["n", "sg", "nom", "p3", "px3sp", "subst", "loc", "gen", "acc"],
        ["prn", "pers", "p1", "sg", "gen", "dat", "acc", "nom"],
    ]
    for tags in samples:
        assert a2ud(tags, disable_undocumented_tags_warnings=True) == \
            a2ud_unbounded(tags), f"bounded != unbounded for {tags}"
