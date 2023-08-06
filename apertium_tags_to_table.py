# coding: utf-8
# quick and dirty table preparation

import pandas as pd
import json

if __name__ == "__main__":

    with open("apertium2ud/resources/tags_map.json", "r", encoding="utf-8") as rf:
        raw_json = json.load(rf)

    table = []

    for segment in raw_json:
        # print("Section", segment)
        if segment == "POS":
            for pos_tag in raw_json[segment]:
                current = raw_json[segment][pos_tag]
                if "t" in current and current["t"]:
                    # print(" ", pos_tag, end=" -> ")
                    # print(f"{','.join(current.get('tags', '?'))}\t{','.join(current.get('feats', '?'))}\t{current.get('gloss', '?')}")
                    table.append({
                        "tag": pos_tag,
                        "tag-type": segment,
                        "ut-tag": ','.join(current.get('tags', [])),
                        "ut-feats": ','.join(current.get('feats', [])),
                        "gloss-english": current.get('gloss', None)
                    })
                else:
                    # print("Section", pos_tag)
                    for lower_pos_tag in current:
                        # print(" ", lower_pos_tag, end=" -> ")
                        lower_current = current[lower_pos_tag]
                        if "t" in lower_current and lower_current["t"]:
                            # print(f"{','.join(lower_current.get('tags', '?'))}\t{','.join(lower_current.get('feats', '?'))}\t{lower_current.get('gloss', '?')}")
                            table.append({
                                "tag": lower_pos_tag,
                                "tag-type": pos_tag,
                                "ut-tag": ','.join(lower_current.get('tags', [])),
                                "ut-feats": ','.join(lower_current.get('feats', [])),
                                "gloss-english": lower_current.get('gloss', None)
                            })
                        else:
                            raise Exception()

        elif segment == "subtype" or segment == "infl":
            for subsegment in raw_json[segment]:
                # print("Section", subsegment)
                for tag in raw_json[segment][subsegment]:
                    current = raw_json[segment][subsegment][tag]
                    if "t" in current and current["t"]:
                        # print(" ", tag, end=" -> ")
                        # print(f"{','.join(current.get('tags', '?'))}\t{','.join(current.get('feats', '?'))}\t{current.get('gloss', '?')}")
                        table.append({
                            "tag": tag,
                            "tag-type": subsegment,
                            "ut-tag": ','.join(current.get('tags', [])),
                            "ut-feats": ','.join(current.get('feats', [])),
                            "gloss-english": current.get('gloss', None)
                        })
                    else:
                        # print("Section", tag)
                        for lower_tag in current:
                            # print(" ", lower_tag, end=" -> ")
                            lower_current = current[lower_tag]
                            if "t" in lower_current and lower_current["t"]:
                                # print(
                                #     f"{','.join(lower_current.get('tags', '?'))}\t{','.join(lower_current.get('feats', '?'))}\t{lower_current.get('gloss', '?')}")
                                table.append({
                                    "tag": lower_tag,
                                    "tag-type": tag,
                                    "ut-tag": ','.join(lower_current.get('tags', [])),
                                    "ut-feats": ','.join(lower_current.get('feats', [])),
                                    "gloss-english": lower_current.get('gloss', None)
                                })
                            else:
                                raise Exception()

    all_tags_known = {d["tag"] for d in table}
    assert len(all_tags_known) == 276

    extra_tags = []

    for line in open("apertium2ud/resources/custom.udx"):
        line = line.strip().split("\t")
        tags = [tt for t in line[1:4] for tt in t.split("|") if t != "_"]
        extra_tags.extend(tags)

    extra_tags = set(extra_tags)
    should_add = extra_tags.difference(all_tags_known)
    table.extend([{"tag": t, "tag-type": "custom", "gloss-english": ""} for t in should_add])

    print("added", should_add)

    df = pd.DataFrame(table)
    df["gloss-kyrgyz"] = None
    df["gloss-russian"] = None

    df.to_csv("apertium.csv")

    with open("apertium_tags_description.md", "w+", encoding="utf-8") as wf:
        df = df[["tag", "gloss-english", "gloss-kyrgyz", "gloss-russian", "tag-type"]]
        wf.write(df.to_markdown(index=None))
