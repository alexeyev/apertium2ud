"""
    Integration evaluation of the apertium2ud converter against real
    Universal Dependencies data: the UD_Kyrgyz-KTMU treebank (vendored as a
    git submodule under external/UD_Kyrgyz-KTMU).

    IMPORTANT — what this does and does NOT test
    --------------------------------------------
    A UD CoNLL-U file provides gold UPOS + FEATS, but NOT the Apertium analysis
    of each token. A faithful *forward* test (Apertium analysis -> UD) would
    require running the apertium-kir FST pipeline (lttoolbox/hfst), which is out
    of scope here. Instead we evaluate what can be measured from the treebank
    alone:

      (A) Output-validity stress test (forward, ud2a -> a2ud):
          For every gold token we map  UD FEATS -> Apertium candidates (ud2a)
          -> back to UD (a2ud), and assert the converter NEVER emits invalid
          UD feature values (e.g. comma-joined `Number[psor]=Plur,Sing`).
          This exercises the px3sp / NumType sanitisation on ~23K real tokens,
          including many Number[psor]/Person[psor] forms.

      (B) UPOS round-trip recovery (ud2a -> a2ud):
          gold (UPOS, FEATS) -> ud2a -> a2ud -> predicted UPOS set.
          We report how often the gold UPOS is recovered. Round-trips are
          lossy by design (ud2a yields disjunctive candidates), so this is a
          quality signal, not a pass/fail correctness oracle. A floor is
          asserted so regressions are caught.

    Run standalone for a full report:

        python tests/integration_ud_eval.py

    Under pytest, the heavy per-token assertions run only if the treebank
    submodule is present (otherwise the tests are skipped).
"""

import logging
import os
import sys

logging.disable(logging.WARNING)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Registry of (language -> treebank dir + conllu basenames), each vendored as a
# git submodule under external/. The language key selects the .udx rule set.
TREEBANKS = {
    "kir": {
        "dir": os.path.join(ROOT, "external", "UD_Kyrgyz-KTMU"),
        "files": ["ky_ktmu-ud-test.conllu", "ky_ktmu-ud-train.conllu"],
    },
    "kaz": {
        "dir": os.path.join(ROOT, "external", "UD_Kazakh-KTB"),
        "files": ["kk_ktb-ud-test.conllu", "kk_ktb-ud-train.conllu"],
    },
    "tat": {
        "dir": os.path.join(ROOT, "external", "UD_Tatar-NMCTT"),
        "files": ["tt_nmctt-ud-test.conllu", "tt_nmctt-ud-train.conllu"],
    },
    "uig": {
        "dir": os.path.join(ROOT, "external", "UD_Uyghur-UDT"),
        "files": ["ug_udt-ud-test.conllu", "ug_udt-ud-train.conllu"],
    },
    "tur": {
        "dir": os.path.join(ROOT, "external", "UD_Turkish-IMST"),
        "files": ["tr_imst-ud-test.conllu", "tr_imst-ud-train.conllu"],
    },
    "uzb": {
        "dir": os.path.join(ROOT, "external", "UD_Uzbek-UT"),
        "files": ["uz_ut-ud-test.conllu", "uz_ut-ud-train.conllu"],
    },
    "aze": {
        "dir": os.path.join(ROOT, "external", "UD_Azerbaijani-TueCL"),
        "files": ["az_tuecl-ud-test.conllu", "az_tuecl-ud-train.conllu"],
    },
    "sah": {
        "dir": os.path.join(ROOT, "external", "UD_Yakut-YKTDT"),
        "files": ["sah_yktdt-ud-test.conllu", "sah_yktdt-ud-train.conllu"],
    },
}


def treebank_file(lang="kir"):
    spec = TREEBANKS.get(lang)
    if spec is None:
        return None
    for name in spec["files"]:
        p = os.path.join(spec["dir"], name)
        if os.path.isfile(p):
            return p
    return None


def _iter_tokens(conllu_path):
    """ Yield (upos, feats_dict) for every real token (skips multiword ranges
        and empty nodes). Uses the `conllu` library (a package dependency). """
    from conllu import parse_incr
    with open(conllu_path, "r", encoding="utf-8") as f:
        for sentence in parse_incr(f):
            for tok in sentence:
                tid = tok.get("id")
                # skip multiword token ranges (tuple ids) and empty nodes
                if not isinstance(tid, int):
                    continue
                upos = tok.get("upos")
                feats = tok.get("feats") or {}
                xpos = tok.get("xpos")  # Apertium POS tag in these treebanks
                if upos is None or upos == "_":
                    continue
                yield upos, dict(feats), xpos


def _feats_to_set(feats_dict):
    """ Convert a conllu FEATS dict {Name: Val} into the {"Name=Val"} set that
        the converter's feats2set / ud2a expect. Handle multi-valued cells
        (UD allows `Name=A,B`) by emitting each value separately. """
    out = set()
    for name, val in feats_dict.items():
        if val is None:
            continue
        for v in str(val).split(","):
            v = v.strip()
            if v:
                out.add(f"{name}={v}")
    return out


_EVAL_CACHE = {}


def evaluate(conllu_path, limit=None, verbose=False, lang="kir"):
    """ Run evaluations and return a stats dict, memoised per (path, lang,
        limit). The three pytest checks each ask for the same evaluation of the
        same treebanks, so without caching every treebank would be parsed and
        converted three times. `verbose` only affects printing, so a verbose
        call bypasses the cache to still emit its report. """
    key = (conllu_path, lang, limit)
    if not verbose and key in _EVAL_CACHE:
        return _EVAL_CACHE[key]
    stats = _evaluate_uncached(conllu_path, limit=limit, verbose=verbose, lang=lang)
    _EVAL_CACHE[key] = stats
    return stats


def _evaluate_uncached(conllu_path, limit=None, verbose=False, lang="kir"):
    """ Run evaluations. Returns a stats dict.

        Uses the .udx rules for `lang`. If the treebank carries Apertium tags
        in its XPOS column, also runs a real FORWARD evaluation (XPOS -> a2ud,
        compared to gold UPOS). """
    import apertium2ud
    from apertium2ud.convert import a2ud, ud2a

    try:
        rules = apertium2ud.load_language_rules(lang)
    except FileNotFoundError:
        rules = None  # fall back to packaged default inside a2ud

    # The set of Apertium POS tags the converter knows about. Used to decide
    # whether a treebank's XPOS column actually contains Apertium tags (Kazakh)
    # or some other tagset (Kyrgyz-KTMU uses Penn-style XPOS).
    _APERTIUM_TAG_INVENTORY = set(apertium2ud.POS_TAGS_SET)

    n = 0
    invalid_outputs = []          # (A) any comma-joined UD feature value
    upos_recovered = 0            # (B) round-trip
    upos_total = 0
    per_pos_total = {}
    per_pos_ok = {}
    empty_candidate = 0           # ud2a returned nothing usable

    # forward (XPOS -> a2ud) accounting
    fwd_total = 0
    fwd_pos_ok = 0
    fwd_invalid = []

    for upos, feats, xpos in _iter_tokens(conllu_path):
        if limit is not None and n >= limit:
            break
        n += 1

        feat_set = _feats_to_set(feats)

        # ----- ud2a : UD -> Apertium candidate tag groups -----
        candidates = ud2a(upos, feat_set)
        flat_tags = []
        for group in candidates:
            for t in group:
                if t and t != "_":
                    flat_tags.append(t)
        flat_tags = list(dict.fromkeys(flat_tags))  # de-dupe, keep order

        if not flat_tags:
            empty_candidate += 1

        # ----- a2ud : Apertium -> UD (round trip) -----
        pred_upos, pred_feats = a2ud(flat_tags, rules=rules)

        # (A) output-validity: no comma inside any feature value
        for pf in pred_feats:
            if "=" in pf and "," in pf.split("=", 1)[1]:
                invalid_outputs.append((upos, sorted(feat_set), pf))

        # (B) UPOS round-trip recovery
        upos_total += 1
        per_pos_total[upos] = per_pos_total.get(upos, 0) + 1
        if upos in set(pred_upos):
            upos_recovered += 1
            per_pos_ok[upos] = per_pos_ok.get(upos, 0) + 1

        # ----- (E) FORWARD eval using the gold Apertium XPOS tag, if present -
        # Only meaningful when XPOS actually holds Apertium tags (e.g. the
        # Kazakh treebank). Some treebanks (e.g. Kyrgyz-KTMU) use a Penn-style
        # XPOS instead, which is NOT Apertium; we detect that and skip, so the
        # forward metric is not polluted with un-mappable tags.
        if xpos and xpos != "_" and xpos in _APERTIUM_TAG_INVENTORY:
            fwd_total += 1
            f_upos, f_feats = a2ud([xpos], rules=rules)
            if upos in set(f_upos):
                fwd_pos_ok += 1
            for pf in f_feats:
                if "=" in pf and "," in pf.split("=", 1)[1]:
                    fwd_invalid.append((xpos, pf))

        if verbose and n <= 8:
            print(f"  {upos:6s} xpos={xpos} feats={sorted(feat_set)}")
            print(f"         ud2a -> {flat_tags}")
            print(f"         a2ud -> {pred_upos}, {pred_feats}")

    return {
        "tokens": n,
        "lang": lang,
        "invalid_outputs": invalid_outputs,
        "upos_recovered": upos_recovered,
        "upos_total": upos_total,
        "upos_acc": (upos_recovered / upos_total) if upos_total else 0.0,
        "per_pos_total": per_pos_total,
        "per_pos_ok": per_pos_ok,
        "empty_candidate": empty_candidate,
        "fwd_total": fwd_total,
        "fwd_pos_ok": fwd_pos_ok,
        "fwd_pos_acc": (fwd_pos_ok / fwd_total) if fwd_total else None,
        "fwd_invalid": fwd_invalid,
    }


def _print_report(stats, source):
    print(f"\n=== UD evaluation [{stats['lang']}] on {os.path.basename(source)} ===")
    print(f"tokens evaluated         : {stats['tokens']}")
    print(f"UPOS round-trip recovery : {stats['upos_recovered']}/{stats['upos_total']} "
          f"= {stats['upos_acc']:.1%}")
    print(f"empty ud2a candidates    : {stats['empty_candidate']}")
    print(f"invalid UD feat values   : {len(stats['invalid_outputs'])}")
    if stats["fwd_total"]:
        print("\nFORWARD (gold Apertium XPOS -> a2ud), real-direction test:")
        print(f"  tokens with XPOS       : {stats['fwd_total']}")
        print(f"  POS match vs gold UPOS : {stats['fwd_pos_ok']}/{stats['fwd_total']} "
              f"= {stats['fwd_pos_acc']:.1%}")
        print(f"  invalid feat values    : {len(stats['fwd_invalid'])}")
    print("\nper-UPOS round-trip recovery:")
    for pos in sorted(stats["per_pos_total"], key=lambda p: -stats["per_pos_total"][p]):
        tot = stats["per_pos_total"][pos]
        ok = stats["per_pos_ok"].get(pos, 0)
        print(f"  {pos:6s} {ok:5d}/{tot:<5d} ({ok/tot:5.1%})")
    if stats["invalid_outputs"]:
        print("\n!!! invalid outputs (first 10):")
        for row in stats["invalid_outputs"][:10]:
            print("   ", row)


# --------------------------------------------------------------------------- #
#  pytest entry points
# --------------------------------------------------------------------------- #

def _pytest_params():
    import pytest
    return [pytest.param(lang, id=lang) for lang in TREEBANKS]


def test_treebank_no_invalid_feature_values():
    """ (A) On real UD data (both languages), the converter must never emit a
        comma-joined UD feature value. Skipped if no treebank is present. """
    import pytest
    ran = False
    for lang in TREEBANKS:
        path = treebank_file(lang)
        if path is None:
            continue
        ran = True
        stats = evaluate(path, lang=lang)
        assert stats["tokens"] > 0
        assert not stats["invalid_outputs"], (
            f"[{lang}] {len(stats['invalid_outputs'])} invalid feature values, "
            f"e.g. {stats['invalid_outputs'][:3]}"
        )
    if not ran:
        pytest.skip("no UD treebank submodule checked out")


def test_treebank_upos_roundtrip_floor():
    """ (B) UPOS round-trip recovery should clear a conservative floor for each
        available language. Regression guard, not a correctness oracle. """
    import pytest
    ran = False
    for lang in TREEBANKS:
        path = treebank_file(lang)
        if path is None:
            continue
        ran = True
        stats = evaluate(path, lang=lang)
        assert stats["upos_acc"] >= 0.50, (
            f"[{lang}] UPOS round-trip recovery {stats['upos_acc']:.1%} below floor"
        )
    if not ran:
        pytest.skip("no UD treebank submodule checked out")


def test_forward_xpos_pos_accuracy():
    """ (E) Real-direction test: where the treebank stores Apertium tags in
        XPOS, mapping that tag with a2ud should recover the gold UPOS for the
        large majority of tokens, and never produce invalid features. """
    import pytest
    ran = False
    for lang in TREEBANKS:
        path = treebank_file(lang)
        if path is None:
            continue
        stats = evaluate(path, lang=lang)
        if not stats["fwd_total"]:
            continue  # this treebank has no Apertium XPOS tags
        ran = True
        assert not stats["fwd_invalid"], (
            f"[{lang}] forward produced invalid feats: {stats['fwd_invalid'][:3]}"
        )
        assert stats["fwd_pos_acc"] >= 0.80, (
            f"[{lang}] forward POS accuracy {stats['fwd_pos_acc']:.1%} below floor"
        )
    if not ran:
        pytest.skip("no treebank with Apertium XPOS tags checked out")


def test_a2ud_output_has_no_duplicate_features():
    """ (C) a2ud must not emit the same feature string twice. The powerset
        matching can match overlapping tag subsets (e.g. a portmanteau tag and
        its components), so without de-duplication the same UD value would be
        appended multiple times. This guards that de-duplication. """
    from apertium2ud.convert import a2ud
    # <past3p> overlaps <past>/<p3>; <perf> adds Aspect; all must appear once.
    readings = [
        ["vblex", "past3p", "past", "p3", "perf", "pl"],
        ["n", "px1sg", "sg", "gen", "p1"],
        ["v", "tv", "ger", "nom", "cop", "aor", "p3", "pl"],
    ]
    for r in readings:
        upos, feats = a2ud(r)
        assert len(feats) == len(set(feats)), \
            f"duplicate feature(s) for {r}: {feats}"
        assert len(upos) == len(set(upos)), \
            f"duplicate POS for {r}: {upos}"


def test_real_single_readings_are_valid_ud():
    """ (D) Genuine single Apertium readings (as the FST would emit, NOT the
        disjunctive fan-out of ud2a) must yield valid UD: no feature name may
        receive two different values. """
    from apertium2ud.convert import a2ud
    real_readings = [
        ["n", "px1sg", "sg", "gen"],
        ["vblex", "past", "p3", "pl"],
        ["prn", "pers", "p1", "sg", "gen"],
        ["v", "tv", "ger", "nom"],
        ["adj"],
        ["num"],
        ["sent"],
    ]
    for r in real_readings:
        _, feats = a2ud(r)
        names = {}
        for f in feats:
            if "=" in f:
                name, val = f.split("=", 1)
                names.setdefault(name, set()).add(val)
        conflicts = {n: v for n, v in names.items() if len(v) > 1}
        assert not conflicts, f"conflicting feature values for {r}: {conflicts}"


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    requested = [a for a in sys.argv[1:] if not a.startswith("-")]
    langs = requested or list(TREEBANKS)
    any_found = False
    for lang in langs:
        path = treebank_file(lang)
        if path is None:
            print(f"[{lang}] treebank not found under external/; add via:")
            spec_dir = os.path.basename(TREEBANKS[lang]["dir"])
            print(f"  git submodule add https://github.com/UniversalDependencies/"
                  f"{spec_dir} external/{spec_dir}")
            continue
        any_found = True
        stats = evaluate(path, verbose=verbose, lang=lang)
        _print_report(stats, path)
    if not any_found:
        sys.exit(1)
