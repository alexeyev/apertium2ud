# -*- coding: utf-8 -*-

import json
from collections import defaultdict
from typing import List, Set


def _map2rules(tag_map):

    combination2tag = defaultdict(lambda: [])
    queue = [("root", tag_map)]

    while len(queue) > 0:
        name, item = queue.pop(0)

        if "t" in item:
            key = tuple(item.get("tags", []) + sorted(item.get("feats", [])))
            value = name
            combination2tag[key].append(value)
        else:
            for k in item:
                queue.append((k, item[k]))
    results = sorted(list(combination2tag.items()), key=lambda x: len(x[0]), reverse=True)
    return results


_MAP = json.load(open("tags_map.json", "r", encoding="utf-8"))
_RULES = _map2rules(_MAP)

ALL_APERTIUM_TAGS = {tagname: idx for idx, tagname in enumerate(sorted(list(set([t for k, v in _RULES for t in v]))))}


def _feats2set(feats_map: dict):
    if feats_map is not None:
        return {f"{k}={v}" for k, v in feats_map.items()}
    return set([])


def convert(upos: str, feats: Set[str]) -> List[str]:
    pool = {upos}.union(feats)
    results = []

    for keys_tuple, values_list in _RULES:
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


if __name__ == "__main__":

    from conllu import parse

    for a, b in _RULES:
        print(f"Combination of UD's {a} yields Apertium tags {b}.")

    # a really small set
    train_str = open("./UD_Kyrgyz-KTMU/ky_ktmu-ud-train.conllu", "r+", encoding="utf-8").read()
    sentences = []

    with open("ky_ktmu-ud-train.unannotated.txt", "w+", encoding="utf-8") as wf:
        for seq in parse(train_str):
            # 1	Менин	Мен	PRON	PRP	Case=Gen|Number=Sing|Person=1|PronType=Prs	2	nmod	_	_
            sentence_tagged = [(seq[i]["form"], seq[i]["upos"], seq[i]["feats"]) for i in range(len(seq))]
            sentences.append(sentence_tagged)
            wf.write(" ".join([form for form, pos, feats in sentence_tagged]) + "\n")

    for sentence in sentences:
        for word, upos, feats in sentence:
            feats = _feats2set(feats)
            aptm_tags = convert(upos, feats)
            formatted_apertium_tags = "".join(
                [f"<{t[0]}>" if len(t) == 1 else f"<{'?'.join(t) + '?'}>" for t in aptm_tags])
            print(word, upos, feats, "->")
            print(formatted_apertium_tags, "\n")
        print()
