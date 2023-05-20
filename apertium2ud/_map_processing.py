# coding: utf-8

from collections import defaultdict


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
