# -*- coding: utf-8 -*-

from collections import defaultdict


def feats2set(feats_map: dict):
    if feats_map is not None:
        return {f"{k}={v}" for k, v in feats_map.items()}
    return set([])


def _map_to_rules(tag_map):
    """ Reads the dictified Apertium List-of-Symbols page
        and turns in into rules for conversion"""

    ud_combination2apertium = defaultdict(lambda: [])
    apertium2ud_combination = defaultdict(lambda: [])

    # traversing nodes via BFS
    queue = [("root", tag_map)]

    while len(queue) > 0:
        name, item = queue.pop(0)

        # if 'terminal' node (essentially, leaf node)
        if "t" in item:
            tags = item.get("tags", [])
            # ...add the rule to ud2a
            key = tuple(tags + sorted(item.get("feats", [])))
            value = name
            ud_combination2apertium[key].append(value)
            # ... add the rule to a2ud
            if len(tags) < 2:
                apertium2ud_combination[name].append({"tag": item["tags"] if "tags" in item else [],
                                                      "feats": item["feats"] if "feats" in item else []})
            elif len(tags) == 2:
                for tag in tags:
                    apertium2ud_combination[name].append({"tag": tag,
                                                          "feats": item["feats"] if "feats" in item else []})
            else:
                raise AssertionError(f"Can't have tags {item['tags']} all at once")
        else:
            # ...go deeper
            for k in item:
                queue.append((k, item[k]))

    ud2a_results = sorted(list(ud_combination2apertium.items()), key=lambda x: len(x[0]), reverse=True)

    return ud2a_results, dict(apertium2ud_combination)
