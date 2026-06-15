"""
    Conversion functions.

    Analyzers often come with .udx files
    defining conversion rules; these rules
    seem to be more precise than List_of_Symbols,
    that mostly maps one Apertium tag to UD tags;
    therefore they are given higher priority
"""

import logging
from itertools import chain, combinations
from typing import List, Set

from apertium2ud import APERTIUM2UD_RULES, POS_TAGS_SET, UD2APERTIUM_RULES

logger = logging.getLogger(__name__)


def _powerset(iterable, max_size=None):
    """ All combinations of Apertium tags, from largest to smallest subsets.

        If max_size is given, only subsets of that size or smaller are produced.
        Subsets larger than the largest rule key can never match a rule, so
        bounding the size avoids generating an exponential number of useless
        candidates for long readings. """
    s = list(iterable)
    upper = len(s) if max_size is None else min(len(s), max_size)
    return chain.from_iterable(combinations(s, r) for r in range(upper, 0, -1))


def _max_rule_key_size(rules):
    """ Size of the largest tag-combination used as a rule key (cached per
        rules-dict identity, since rule dicts are built once and reused). """
    cached = _MAX_RULE_KEY_SIZE_CACHE.get(id(rules))
    if cached is None:
        cached = max((len(k) for k in rules), default=1)
        _MAX_RULE_KEY_SIZE_CACHE[id(rules)] = cached
    return cached


_MAX_RULE_KEY_SIZE_CACHE = {}


def ud2a(upos: str, feats: Set[str]) -> List[str]:
    """ Universal tagset to Apertium tagset """

    # all universal tagset tags as a single set
    pool = frozenset({upos}.union(feats))
    results = []

    for keys_tuple, values_list in UD2APERTIUM_RULES:

        if len(keys_tuple) == 0:
            break

        matches = True

        for key in keys_tuple:
            if key not in pool:
                matches = False
                break
        if matches:
            results.append(values_list)

    return results


def a2ud(tags: List[str], disable_undocumented_tags_warnings=False, rules=None,
         report_unmapped=False):
    """
        Apertium tagset to universal tagset
        :param tags: all Apertium tags for a given word in the order of parsing (important!)
        :param disable_undocumented_tags_warnings: whether should spam into stderr
                about unknown tags (which are ignored by design)
        :param rules: optional APERTIUM2UD rule dict to use instead of the default
                (Kyrgyz) rules; obtain one via apertium2ud.load_language_rules(lang)
        :param report_unmapped: if True, also return the sorted list of input
                tags that produced no UD POS or feature (e.g. undocumented
                apertium-kir subtags). Lets callers see silent drops.
        :return: (upos tags, feats) or (upos tags, feats, unmapped) if report_unmapped
    """
    if rules is None:
        rules = APERTIUM2UD_RULES

    # removing PoS tags from segmentations other than the first one
    # todo: check if this approach is valid!
    filtered_tags, first_seen = [], False

    for tag in tags:
        if tag in POS_TAGS_SET:
            if not first_seen:
                filtered_tags.append(tag)
                first_seen = True
        else:
            filtered_tags.append(tag)

    tags = filtered_tags
    result_tags, result_feats = [], []
    contributing = set()  # tags that produced at least one POS/feature

    # Only subsets up to the largest rule key can ever match; bounding the
    # powerset size keeps long readings from blowing up exponentially.
    max_size = _max_rule_key_size(rules)

    for tags_subset in _powerset(tags, max_size=max_size):

        tags_subset = frozenset(tags_subset)

        if tags_subset not in rules and not len(tags_subset) == 1:
            continue

        if tags_subset not in rules and len(tags_subset) == 1:
            (t,) = tags_subset
            if not disable_undocumented_tags_warnings:
                logger.warning("<%s> not documented, skipping.", t)
            continue

        matched_rules = rules[tags_subset]

        for rule in matched_rules:
            if rule.get("tag") or rule.get("feats"):
                contributing.update(tags_subset)
            if "tag" in rule:
                result_tags.extend(rule["tag"])
            if "feats" in rule:
                result_feats.extend(rule["feats"])

    # The powerset intentionally matches overlapping tag subsets (e.g. a
    # portmanteau tag like <past3p> alongside <past> and <p3>), so the same UD
    # POS / feature can be appended more than once. UD requires each feature to
    # appear at most once, so we de-duplicate here while preserving the order
    # in which values were first produced.
    result_tags = list(dict.fromkeys(result_tags))
    result_feats = list(dict.fromkeys(result_feats))

    if report_unmapped:
        unmapped = sorted(t for t in tags if t not in contributing)
        return result_tags, result_feats, unmapped

    return result_tags, result_feats
