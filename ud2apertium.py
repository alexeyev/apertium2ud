# coding: utf-8

import json
from typing import List

_MAP = json.load(open("tags_map.json", "r", encoding="utf-8"))


def convert(upos: str, feats: str) -> List[str]:
    return []


if __name__ == "__main__":

    from conllu import parse

    # a really small set
    train_str = open("./UD_Kyrgyz-KTMU/ky_ktmu-ud-train.conllu", "r+", encoding="utf-8").read()

    train_sentences = []

    with open("ky_ktmu-ud-train.unannotated.txt", "w+", encoding="utf-8") as wf:
        for seq in parse(train_str):
            # 1	Менин	Мен	PRON	PRP	Case=Gen|Number=Sing|Person=1|PronType=Prs	2	nmod	_	_
            sentence_tagged = [(seq[i]["form"], seq[i]["upos"], seq[i]["feats"]) for i in range(len(seq))]
            train_sentences.append(sentence_tagged)
            wf.write(" ".join([form for form, pos, feats in sentence_tagged]) + "\n")

    print(train_sentences)
