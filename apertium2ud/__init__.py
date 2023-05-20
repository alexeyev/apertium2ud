# -*- coding: utf-8 -*-

import json

from . import meta
from ._map_processing import _map2rules

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
UD2APERTIUM_RULES = _map2rules(RAW_WIKI_MAP)

POS_TAGS_LIST = sorted(list(set(RAW_WIKI_MAP["POS"].keys())
                            .difference({"punkt"})
                            .union(RAW_WIKI_MAP["POS"]["punkt"].keys())))


OTHER_TAGS_LIST = sorted(list(set([t for k, v in UD2APERTIUM_RULES for t in v if not t in POS_TAGS_LIST])))

ALL_APERTIUM_TAGS_LIST = POS_TAGS_LIST + OTHER_TAGS_LIST
ALL_APERTIUM_TAGS_MAP = {tagname: idx for idx, tagname in enumerate(ALL_APERTIUM_TAGS_LIST)}

# print(f"The first {len(POS_TAGS_LIST)} tags are PoS, the next {len(OTHER_TAGS_LIST)} are not.")
# > The first 40 tags are PoS (0..39), the next 236 are not.
