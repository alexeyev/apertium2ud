#!/usr/bin/python3

import html
from typing import List

import requests


def parse_ud_cell(section: List[str], cell_content: str, apertium_tag: str=None) -> List[str]:

    cell_content = cell_content.strip()
    section = [s.strip() for s in section]

    if section[0] == "POS":
        if len(section) == 1:
            # "VERB or AUX"
            if " or " in cell_content:
                return {"tags": cell_content.split(" or ")}
            elif not cell_content:
                return {}
            return {"tags": [cell_content]}
        elif section[-1] == "punct":
                splitted = cell_content.split(" ")
                result = {"tags": [splitted[0]]}
                if len(splitted) > 1:
                    result["feats"] = splitted[1:]
                return result
        else:
            raise Exception(f"Something's changed on the page in {section}, should update the parser")
    elif section[0] == "subtype":
        if section[-1] in {"gender", "countability", "animacy", "adj_type", "transitivity"}:
            if cell_content:
                return {"feats": [cell_content.split("<")[0].strip()]}
            else:
                return {}
        elif section[-1] in {"n_class", "separable", "np_type"}:
            return {}
        elif section[-1] in {"prn_type"}:
            if "=" in cell_content:
                return {"feats": [cell_content]}
            elif cell_content.isupper():
                return {"tags": [cell_content]}
            elif not cell_content:
                return {}
            else:
                raise Exception(f"Something's changed on the page in {section}, should update the parser")
        else:
            raise Exception(f"Something's changed on the page in {section}, should update the parser")
    elif section[0] == "infl":
        if section[1] in {"number", "case", "voice", "aspect", "adj_infl", "compound"}:
            if cell_content:
                return {"feats": [cell_content.split("<")[0].strip()]}
            else:
                return {}
        elif section[1] in {"verb_deriv", "formality", "other", "chunk"}:
            return {}
        elif section[1] in {"tense", "person", "possessor", "subject", "object"}:
            if " " in cell_content:
                return {"feats": cell_content.split(" ")}
            elif cell_content:
                return {"feats": [cell_content]}
            else:
                return {}
        elif section[1] == "nonfinite":
            if section[2] in {"verbal-nouns", "verbal-adjectives", "verbal-adverbs", "infinitives"}:
                if " " in cell_content:
                    return {"feats": cell_content.split(" ")}
                elif cell_content:
                    return {"feats": [cell_content]}
                else:
                    return {}
            else:
                raise Exception(f"Something's changed on the page in {section}, should update the parser")
        elif section[1] == "specificity":
            # todo: this is a wiki page bug, so I had to hardcode this
            if apertium_tag == "spc":
                return {"feats": ["Definite=Spec"]}
            return {}
        else:
            raise Exception(f"Something's changed on the page in {section}, should update the parser")

    return {"dummy": cell_content}


def scrape_tags():
    """ Scrape tag database from Apertium wiki """

    current, all_tags = [], {}

    # getting raw Wikipedia page
    r = requests.get("http://wiki.apertium.org/w/index.php?title=List_of_symbols&action=raw")

    if r.status_code != 200:
        raise Exception("Couldn\'t get wiki page")

    # really really markup-dependent parsing (can't do anything about that though)
    for line in html.unescape(r.content.decode('utf-8')).splitlines():

        # this means it's a section
        if line.startswith('==') and '<!--' in line:

            # the name is in the comments section
            name = line.split('<!--')[1].split('-->')[0].strip()

            if name == "xml" or name == "chunk":
                break

            depth = 0

            if line.startswith('==='):
                depth = 1

            if line.startswith('===='):
                depth = 2

            if len(current) == depth:
                current.append(name)
            else:
                current = current[:depth] + [name]

            if len(current) == 1:
                all_tags[current[0]] = {}
            elif len(current) == 2:
                all_tags[current[0]][current[1]] = {}
            elif len(current) == 3:
                all_tags[current[0]][current[1]][current[2]] = {}

        # table row
        elif line.startswith('| <code>'):

            tag = line.split('<code>')[1].split('</code>')[0]
            gloss = line.split('||')[1].strip().replace('"', "'")

            if len(line.split('||')) > 3:
                item_of_interest = line.split('||')[3].strip().replace('"', "'")
            else:
                item_of_interest = ""

            item_of_interest = parse_ud_cell(current, item_of_interest, tag)
            item_of_interest["gloss"] = gloss

            # debug
            # print("PAIR:", current, tag, item_of_interest)

            if len(current) == 1:
                all_tags[current[0]][tag] = item_of_interest
            elif len(current) == 2:
                all_tags[current[0]][current[1]][tag] = item_of_interest
            elif len(current) == 3:
                all_tags[current[0]][current[1]][current[2]][tag] = item_of_interest

    return all_tags


if __name__ == '__main__':
    import json
    tags = scrape_tags()

    with open("tags_map.json", "w+", encoding="utf-8") as wf:
        json.dump(tags, wf)
