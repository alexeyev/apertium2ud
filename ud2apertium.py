# coding: utf-8

import json
from collections import defaultdict
from typing import List


def _map2rules(tag_map):

    combination2tag = defaultdict(lambda: [])
    queue = [("root", tag_map)]

    while len(queue) > 0:
        name, item = queue.pop(0)

        if "t" in item:
            key = tuple(item.get("tags", []) + item.get("feats", []))
            value = name
            combination2tag[key].append(value)
        else:
            for k in item:
                queue.append((k, item[k]))
    results = sorted(list(combination2tag.items()), key=lambda x: len(x[0]), reverse=True)
    return results


_MAP = json.load(open("tags_map.json", "r", encoding="utf-8"))
_RULES = _map2rules(_MAP)


def _feats2set(feats_map: dict):
    if feats_map is not None:
        return {f"{k}={v}" for k, v in feats_map.items()}
    return None


def convert(upos: str, feats: str) -> List[str]:
    # todo: iterate the rules and find the best-fitting thing
    return []


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
            print(word)
            print(upos)
            print(feats)
            print()
        quit()
