import json
import logging

from . import meta, resources
from ._map_processing import _map_to_rules
from ._map_processing import feats2set as feats2set  # re-exported public API

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Trying backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

logger = logging.getLogger(__name__)

__version__ = meta.version
__author__ = meta.authors[0]
__license__ = meta.license
__copyright__ = meta.copyright

# ------- const -------

with pkg_resources.path(resources, "tags_map.json") as filepath:
    raw_text = open(filepath, "r+", encoding="utf-8").read().strip()
    RAW_WIKI_MAP = json.loads(raw_text)
    del raw_text

def _load_udx_mapping(filepath):
    """ Parse a .udx rules file into a {frozenset(apertium_tags): [rule]} dict.

        Column layout (tab-separated, 8 columns):
          0..4  Apertium tag groups (pipe-separated alternatives within a cell)
          5     UD POS tag ('_' if none)
          6..7  UD feature groups (pipe-separated) """
    rows = [line.strip().split("\t")
            for line in open(filepath, "r+", encoding="utf-8").readlines()
            if line.strip()]
    mapping = [(frozenset([tag for col in seq[:5] for tag in col.split("|")]).difference({"_"}),
                [{"tag": [seq[5]] if seq[5] != "_" else [],
                  "feats": list(set([utag
                                     for col in seq[6:]
                                     for utag in col.split("|")])
                                .difference({"_"}))}])
               for seq in rows]
    return dict(mapping)


# Languages that are selectable but whose Apertium repo ships no .udx; they use
# the generic wiki-scraped map with no language-specific overrides. Kept here so
# the runtime can offer them even though no <lang>.udx is packaged. (These
# Apertium repos have no upstream .udx; we deliberately do not invent rules.)
GENERIC_MAP_LANGS = ["tat", "tur", "uzb", "aze", "sah"]


def available_languages():
    """ Languages this install can convert: those with packaged <lang>.udx
        rules, plus generic-map languages that fall back to the wiki map. """
    langs = set(GENERIC_MAP_LANGS)
    try:
        names = list(pkg_resources.contents(resources))
    except Exception:
        return sorted(langs)
    for name in names:
        if name.endswith(".udx") and name != "custom.udx":
            langs.add(name[:-len(".udx")])
    return sorted(langs)


def load_language_rules(lang):
    """ Return the APERTIUM2UD rule dict for a specific language.

        For a language with a packaged <lang>.udx (e.g. "kir", "kaz"), the rules
        are the wiki map overridden by that language's .udx. For a generic-map
        language with no .udx (e.g. "tat"), the pure wiki map is returned.
        Does not mutate the module-level default rules.

        Raises FileNotFoundError if the language is not available at all. """
    _, rules = _map_to_rules(RAW_WIKI_MAP)

    fname = f"{lang}.udx"
    has_udx = False
    try:
        has_udx = pkg_resources.is_resource(resources, fname)
    except Exception:
        has_udx = False

    if has_udx:
        with pkg_resources.path(resources, fname) as filepath:
            for k, v in _load_udx_mapping(filepath).items():
                rules[k] = v
        return rules

    if lang in GENERIC_MAP_LANGS:
        # No .udx upstream: generic wiki map only, no language-specific rules.
        return rules

    raise FileNotFoundError(
        f"no rules for language {lang!r}; available: {available_languages()}"
    )


try:
    with pkg_resources.path(resources, "custom.udx") as filepath:
        default_udx_mapping = _load_udx_mapping(filepath)
except Exception:
    default_udx_mapping = None
    logger.warning("`custom.udx` was not packaged")


UD2APERTIUM_RULES, APERTIUM2UD_RULES = _map_to_rules(RAW_WIKI_MAP)

# override the generic wiki-map rules with the default language's .udx rules
if default_udx_mapping:
    for k, v in default_udx_mapping.items():
        APERTIUM2UD_RULES[k] = v

POS_TAGS_LIST = sorted(list(set(RAW_WIKI_MAP["POS"].keys())
                            .difference({"punkt"})
                            .union(RAW_WIKI_MAP["POS"]["punkt"].keys())))
POS_TAGS_SET = set(POS_TAGS_LIST)

OTHER_TAGS_LIST = sorted(list(set([t for k, v in UD2APERTIUM_RULES for t in v if t not in POS_TAGS_LIST])))

ALL_APERTIUM_TAGS_LIST = POS_TAGS_LIST + OTHER_TAGS_LIST
ALL_APERTIUM_TAGS_MAP = {tagname: idx for idx, tagname in enumerate(ALL_APERTIUM_TAGS_LIST)}

# print(f"The first {len(POS_TAGS_LIST)} tags are PoS, the next {len(OTHER_TAGS_LIST)} are not.")
# > The first 40 tags are PoS (0..39), the next 236 are not.
