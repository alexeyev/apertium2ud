# -*- coding: utf-8 -*-

from typing import List, Set, Collection

from apertium2ud import UD2APERTIUM_RULES, APERTIUM2UD_RULES


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

    for tag in tags:
        rules = APERTIUM2UD_RULES[tag]
        for rule in rules:
            if "tag" in rule:
                result_tags.extend(rule["tag"])
            if "feats" in rule:
                result_feats.extend(rule["feats"])

    return result_tags, result_feats
