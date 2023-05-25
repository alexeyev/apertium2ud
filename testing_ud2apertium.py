# coding: utf-8

from apertium2ud.convert import ud2a
from apertium2ud import feats2set


if __name__ == "__main__":

    from conllu import parse

    # a really small set
    test_str = open("./UD_Kyrgyz-KTMU/ky_ktmu-ud-test.conllu", "r+", encoding="utf-8").read()
    train_str = open("./UD_Kyrgyz-KTMU/ky_ktmu-ud-train.conllu", "r+", encoding="utf-8").read()
    sentences = []

    with open("ky_ktmu-ud.unannotated.txt", "w+", encoding="utf-8") as wf:
        for f in [test_str, train_str]:
            for seq in parse(f):
                # 1	Менин	Мен	PRON	PRP	Case=Gen|Number=Sing|Person=1|PronType=Prs	2	nmod	_	_
                sentence_tagged = [(seq[i]["form"], seq[i]["upos"], seq[i]["feats"]) for i in range(len(seq))]
                sentences.append(sentence_tagged)
                wf.write(" ".join([form for form, pos, feats in sentence_tagged]) + "\n")

    for sentence in sentences:
        for word, upos, feats in sentence:
            feats = feats2set(feats)
            aptm_tags = ud2a(upos, feats)
            formatted_apertium_tags = "".join(
                [f"<{t[0]}>" if len(t) == 1 else f"<{'?'.join(t) + '?'}>" for t in aptm_tags])
            print(word, upos, feats, "->")
            print(formatted_apertium_tags, "\n")
        print()
