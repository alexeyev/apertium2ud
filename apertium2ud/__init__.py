import json
import sys

from . import meta
from ._map_processing import _map_to_rules, feats2set

__version__ = meta.version
__author__ = meta.authors[0]
__license__ = meta.license
__copyright__ = meta.copyright

# ------- const -------

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Trying backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

from . import resources

with pkg_resources.path(resources, "tags_map.json") as filepath:
    raw_text = open(filepath, "r+", encoding="utf-8").read().strip()
    RAW_WIKI_MAP = json.loads(raw_text)
    del raw_text

try:
    with pkg_resources.path(resources, "custom.udx") as filepath:

        # todo: looks horrible, should wrap into some nice functions
        default_udx_mapping = [line.strip().split("\t")
                               for line in open(filepath, "r+", encoding="utf-8").readlines()
                               if line.strip()]
        default_udx_mapping = [(frozenset([tag for col in seq[:5] for tag in col.split("|")]).difference({"_"}),
                                [{"tag": [seq[5]] if seq[5] != "_" else [],
                                  "feats":
                                      list(set([utag
                                                for col in seq[6:]
                                                for utag in col.split("|")])
                                           .difference({"_"}))}])
                               for seq in default_udx_mapping]
        default_udx_mapping = dict(default_udx_mapping)
except Exception as e:
    default_udx_mapping = None
    print("`custom.udx` was not packaged", file=sys.stderr)


UD2APERTIUM_RULES, APERTIUM2UD_RULES = _map_to_rules(RAW_WIKI_MAP)

# overriding
for k, v in default_udx_mapping.items(): APERTIUM2UD_RULES[k] = v

POS_TAGS_LIST = sorted(list(set(RAW_WIKI_MAP["POS"].keys())
                            .difference({"punkt"})
                            .union(RAW_WIKI_MAP["POS"]["punkt"].keys())))
POS_TAGS_SET = set(POS_TAGS_LIST)

OTHER_TAGS_LIST = sorted(list(set([t for k, v in UD2APERTIUM_RULES for t in v if not t in POS_TAGS_LIST])))

ALL_APERTIUM_TAGS_LIST = POS_TAGS_LIST + OTHER_TAGS_LIST
ALL_APERTIUM_TAGS_MAP = {tagname: idx for idx, tagname in enumerate(ALL_APERTIUM_TAGS_LIST)}

# print(f"The first {len(POS_TAGS_LIST)} tags are PoS, the next {len(OTHER_TAGS_LIST)} are not.")
# > The first 40 tags are PoS (0..39), the next 236 are not.
