# coding: utf-8

import numpy as np

from streamparser import parse, LexicalUnit
from typing import Set, List
from apertium2ud import ALL_APERTIUM_TAGS_MAP
from apertium2ud.convert import a2ud

if __name__ == "__main__":

    from tqdm import tqdm

    with open("ky_ktmu-ud.apertium-kir.txt", "r", encoding="utf-8") as rf:

        unseen_tags = []

        for line in tqdm(rf):
            lexical_units = parse(line.strip())

            for item in lexical_units:
                """A single subreading of an analysis of a token.
                    Fields:
                        baseform (str): The base form (lemma, lexical form, citation form) of the reading.
                        tags (list of str): The morphological tags associated with the reading.
                """
                # print("RAW:", item)
                print("Original word:", item.wordform)
                print()

                for i_segm, possible_reading in enumerate(item.readings):
                    print(f"- Reading {i_segm + 1}")
                    segmentation = "|".join([r.baseform for r in possible_reading])
                    all_tags = [t for r in possible_reading for t in r.tags]
                    all_tags_str = "".join([f"<{t}>" for t in all_tags])
                    all_together = "".join(
                        [f"{r.baseform}{''.join([f'<{t}>' for t in r.tags])} " for r in possible_reading])
                    # print(segmentation, all_tags_str, "=>", all_together)
                    print("  ", all_together)
                    ud_possibilities = a2ud(all_tags)
                    print(ud_possibilities)

                print()

        print("unseen tags", ", ".join([f"'{s}'" for s in set(unseen_tags)]))