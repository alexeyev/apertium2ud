# -*- coding: utf-8 -*-

import numpy as np

from streamparser import parse, LexicalUnit
from typing import Set, List
from ud2apertium import ALL_APERTIUM_TAGS


def _vectorize_tags(tags_sets: List[Set[str]]) -> np.ndarray:
    encoded_sets = np.zeros((len(tags_sets), len(ALL_APERTIUM_TAGS)))

    for i, tag_set in enumerate(tags_sets):
        for tag in tag_set:
            encoded_sets[i, ALL_APERTIUM_TAGS[tag]] += 1

    return encoded_sets


def _get_btg(lexical_unit: LexicalUnit):
    """
        Each parse produces multiple reads, each provides
        its base form of the word and a set of morphological tags;
        LexicalUnit is a list of such reads, providing
        more details, including the base form segmentation
        (with the corresponding tags for each segment).

        This function retains only base forms, all the tags and their encoding as vectors in one bag.
    """
    baseforms, tag_sets = [], []

    for i_segm, possible_reading in enumerate(lexical_unit.readings):
        baseform = "".join([r.baseform for r in possible_reading])
        all_tags = set([t for r in possible_reading for t in r.tags])
        baseforms.append(baseform)
        tag_sets.append(all_tags)

    return baseforms, tag_sets, _vectorize_tags(tag_sets)


class MorphoParsedSentence(object):

    def __init__(self, parser_output: str):
        self.raw_parser_string = parser_output.strip()
        lexical_units = parse(self.raw_parser_string)
        self.parsed_results = [(_get_btg(lu), lu) for lu in lexical_units]

    def get_original_sentence(self):
        return [lu.wordform for _, lu in self.parsed_results]

    def get_vectors_sequence(self):
        return [vec for (_, _, vec), _ in self.parsed_results]


if __name__ == "__main__":
    with open("ky_ktmu-ud-train.apertium-kir.txt", "r", encoding="utf-8") as rf:
        for line in rf:
            lexical_units = parse(line.strip())

            for item in lexical_units:
                """A single subreading of an analysis of a token.
                    Fields:
                        baseform (str): The base form (lemma, lexical form, citation form) of the reading.
                        tags (list of str): The morphological tags associated with the reading.
                """
                print("Original word:", item.wordform, item.knownness)
                print()

                for i_segm, possible_reading in enumerate(item.readings):
                    segmentation = "|".join([r.baseform for r in possible_reading])
                    all_tags = [t for r in possible_reading for t in r.tags]
                    all_tags_str = "".join([f"<{t}>" for t in all_tags])
                    all_together = "".join(
                        [f"{r.baseform}{''.join([f'<{t}>' for t in r.tags])} " for r in possible_reading])
                    print(segmentation, all_tags_str, "=>", all_together)

                print()
