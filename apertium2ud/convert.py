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

from apertium2ud import UD2APERTIUM_RULES, APERTIUM2UD_RULES
from itertools import chain, combinations


def _powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1, 0, -1))


def ud2a(upos: str, feats: Set[str]) -> List[str]:
    pool = {upos}.union(feats)
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


def a2ud(tags: Collection[str]):

    result_tags, result_feats = [], []

    for tags_subset in _powerset(tags):

        tags_subset = frozenset(tags_subset)

        if tags_subset not in APERTIUM2UD_RULES and not len(tags_subset) == 1:
            continue

        if tags_subset not in APERTIUM2UD_RULES and len(tags_subset) == 1:
            (t,) = tags_subset
            print(f"<{t}> not documented, skipping.", file=sys.stderr)
            continue

        rules = APERTIUM2UD_RULES[tags_subset]

        for rule in rules:
            if "tag" in rule:
                result_tags.extend(rule["tag"])
            if "feats" in rule:
                result_feats.extend(rule["feats"])

    return result_tags, result_feats
