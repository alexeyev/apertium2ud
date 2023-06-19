# -*- coding: utf-8 -*-
"""
    Conversion functions.

    Analyzers often come with .udx files
    defining conversion rules; these rules
    seem to be more precise than List_of_Symbols,
    that mostly maps one Apertium tag to UD tags;
    therefore they are given higher priority
"""

import sys

from typing import List, Set, Collection

from apertium2ud import UD2APERTIUM_RULES, APERTIUM2UD_RULES, POS_TAGS_SET
from itertools import chain, combinations


def _powerset(iterable):
    """ All possible combinations of Apertium tags, from largest to smallest subsets """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1, 0, -1))


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


def a2ud(tags: List[str], disable_undocumented_tags_warnings=False):
    """
        Apertium tagset to universal tagset
        :param tags: all Apertium tags for a given word in the order of parsing (important!)
        :param disable_undocumented_tags_warnings: whether should spam into stderr
                about unknown tags (which are ignored by design)
        :return: (upos tags, feats)
    """

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

    for tags_subset in _powerset(tags):

        tags_subset = frozenset(tags_subset)

        if tags_subset not in APERTIUM2UD_RULES and not len(tags_subset) == 1:
            continue

        if tags_subset not in APERTIUM2UD_RULES and len(tags_subset) == 1:
            (t,) = tags_subset
            if not disable_undocumented_tags_warnings:
                print(f"<{t}> not documented, skipping.", file=sys.stderr)
            continue

        rules = APERTIUM2UD_RULES[tags_subset]

        for rule in rules:
            if "tag" in rule:
                result_tags.extend(rule["tag"])
            if "feats" in rule:
                result_feats.extend(rule["feats"])

    return result_tags, result_feats
