# -*- coding: utf-8 -*-

from typing import List, Set

from apertium2ud import UD2APERTIUM_RULES


def _feats2set(feats_map: dict):
    if feats_map is not None:
        return {f"{k}={v}" for k, v in feats_map.items()}
    return set([])


def convert(upos: str, feats: Set[str]) -> List[str]:
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

