# apertium2ud

Obtaining the mapping between the two tagsets based 
on the [information from Apertium Wiki](https://wiki.apertium.org/w/index.php?title=List_of_symbols).

Loosely based on [this code](https://github.com/mr-martian/apertium-recursive-learning/blob/master/tags.py), 
hence the GPLv3 license.

To install the latest released version, run

```bash
python -m pip install apertium2ud
```

**NB!**

1. The instrument is far from being perfect.
2. It was originally developed for working with `apertium-kir`, i.e. with the Kyrgyz language.
3. The package ships with the [apertium-kir](https://github.com/apertium/apertium-kir/blob/main/apertium-kir.kir.udx) `.udx` conversion rules. For other languages, you may need to add the corresponding submodule (see below).

## Building from source

The package needs two kinds of resources that are **generated at build time and
not committed** to the repository:

* `apertium2ud/resources/tags_map.json` — the Apertium↔UD tag map, scraped from
  the [Apertium wiki "List of symbols"](https://wiki.apertium.org/w/index.php?title=List_of_symbols) page; and
* `apertium2ud/resources/<lang>.udx` — copied from the relevant Apertium
  language repository, vendored as a **git submodule** under `external/`.

The Apertium language repositories are referenced as submodules, so clone with:

```bash
git clone --recurse-submodules https://github.com/alexeyev/apertium2ud.git
# or, if already cloned:
git submodule update --init --recursive
```

Languages with packaged `.udx` rules: **Kyrgyz** (`apertium-kir`, the default),
**Kazakh** (`apertium-kaz`), and **Uyghur** (`apertium-uig`). Also selectable,
but falling back to the generic wiki-scraped map (no language-specific
overrides) because their Apertium repo ships no `.udx`: **Tatar**, **Turkish**,
**Uzbek**, **Azerbaijani**, and **Sakha/Yakut**. To add a language, add its
Apertium repo as a submodule and list it in `SUPPORTED_LANGS` (or, if it has no
`.udx`, `GENERIC_MAP_LANGS`) in `build_resources.py`:

```bash
git submodule add https://github.com/apertium/apertium-tat external/apertium-tat
```

Building the package generates the resources automatically (a plain
`pip install .` or `python -m build` runs the wiki scrape and copies the
`.udx` files via an in-tree build backend), so the produced wheel/sdist already
contains them. To (re)generate the resources manually:

```bash
python build_resources.py            # all configured languages
python build_resources.py --langs kir
python build_resources.py --skip-wiki  # reuse existing tags_map.json
```

`.udx` files are sanitized on copy to repair known upstream defects that would
otherwise emit invalid UD output (e.g. comma-joined feature values such as
`Number[psor]=Plur,Sing`, which is dropped as underspecified).

## Apertium to Universal tags

```
>>> from apertium2ud.convert import a2ud
>>> a2ud(["n", "pl", "acc"])
(['NOUN'], ['Number=Plur', 'Case=Acc', 'Definite=Def'])
>>> a2ud(["v", "tv", "ger", "nom", "cop", "aor", "p3", "pl"])
(['VERB'], ['VerbForm=Ger', 'Case=Nom', 'Tense=Aor', 'VerbForm=Fin', 'Mood=Ind', 'Person=3', 'Number=Plur'])
```

(Exact features depend on the bundled `.udx` rules; the examples above reflect
the packaged `apertium-kir` rules.)

### Selecting a language

By default `a2ud` uses the Kyrgyz (`apertium-kir`) rules. To use another
packaged language's rules, load them and pass them in:

```
>>> import apertium2ud
>>> apertium2ud.available_languages()
['aze', 'kaz', 'kir', 'sah', 'tat', 'tur', 'uig', 'uzb']
>>> kaz_rules = apertium2ud.load_language_rules("kaz")
>>> from apertium2ud.convert import a2ud
>>> a2ud(["n", "pl", "acc"], rules=kaz_rules)
(['NOUN'], ['Number=Plur', 'Case=Acc'])
```

The default behaviour (calling `a2ud` without `rules=`) is unchanged.

## Universal tags to Apertium

So far the conversion is far from perfect
```
Кыз NOUN {'Number[psor]=Sing', 'Number=Sing', 'Case=Nom', 'Person[psor]=3', 'Person=3'} ->
<px3sg><n><subj?nom?><sg><p3><px3sp> 

досуна NOUN {'Number[psor]=Sing', 'Number=Sing', 'Person[psor]=3', 'Case=Dat', 'Person=3'} ->
<px3sg><n><sg><dat><p3><px3sp> 

кат NOUN {'Case=Nom', 'Person=3', 'Number=Sing'} ->
<n><subj?nom?><sg><p3> 

жазган VERB {'Aspect=Perf', 'Polarity=Pos', 'Number=Sing', 'Tense=Past', 'Person=3', 'Evident=Fh'} ->
<past3p><vblex?v?vbmod?><sg><aff><aor?past?pret?><perf><p3> 

. PUNCT set() ->
<sent?apos?percent?clb?punct?> 
```

## Testing

```bash
python build_resources.py          # generate resources first
python -m pytest
ruff check .                       # lint
```

CI (GitHub Actions) lints with ruff, checks out the submodules recursively,
builds the resources, runs the test suite across Python 3.8–3.12, and verifies
that a freshly built wheel installs and works in a clean environment.

### Evaluation against real UD treebanks

`tests/integration_ud_eval.py` evaluates the converter against real Universal
Dependencies data, with the treebanks vendored as submodules under `external/`.
Run a full report with:

```bash
python tests/integration_ud_eval.py          # all available languages
python tests/integration_ud_eval.py kaz      # one language
```

The converter is exercised against eight Turkic UD treebanks (~52K tokens). For
each, UPOS round-trip recovery is reported, and **no invalid UD feature values
are produced for any language**:

| Lang | Treebank          | Tokens | UPOS round-trip | Forward POS\* |
|------|-------------------|-------:|----------------:|--------------:|
| kir  | Kyrgyz-KTMU       | 11771  | 100.0%          | —             |
| kaz  | Kazakh-KTB        | 10007  | 98.9%           | **98.2%**     |
| uig  | Uyghur-UDT        | 10330  | 99.9%           | —             |
| tur  | Turkish-IMST      | 10032  | 100.0%          | —             |
| uzb  | Uzbek-UT          |  5930  | 99.9%           | —             |
| tat  | Tatar-NMCTT       |  2280  | 99.9%           | —             |
| sah  | Yakut-YKTDT       |  1460  | 100.0%          | **99.6%**     |
| aze  | Azerbaijani-TueCL |   912  | 100.0%          | —             |

\* **Forward POS** is the stronger, real-direction metric (gold Apertium tag →
`a2ud` → compared to gold UPOS). It is only available when a treebank stores
genuine Apertium tags in its `XPOS` column — among these, Kazakh-KTB and
Yakut-YKTDT do. The others either use a non-Apertium `XPOS`
(Kyrgyz/Turkish/Uyghur) or leave it blank (Uzbek/Tatar/Azerbaijani), so only the
(lossier) round-trip metric applies there; this is detected automatically.

Caveats: `kir`/`kaz`/`uig` use packaged `.udx` rules, while `tat`/`tur`/`uzb`/
`aze`/`sah` use the generic wiki map (less refined feature output). Some
treebanks add noise — Tatar-NMCTT is a Tatar–Russian code-switching corpus, so a
portion of its tokens are Russian.

## Not covered / limitations

* **POS:** fully covered — every UPOS in the eight treebanks is produced.
* **Features:** ~1.4% of feature instances in the treebanks use a UD pair the
  converter cannot produce (most frequent: `Aspect=Prog`, `Polite=Infm`,
  `Reflex=Yes` for generic-map langs, `Mood=Des`, `Voice=Rcp`, `Case=Equ`).
  These are absent from the Apertium "List of symbols" wiki and from the
  upstream `.udx` files; they are **not invented here**.
* **Generic-map languages** (`tat`/`tur`/`uzb`/`aze`/`sah`) have no upstream
  `.udx`, so their feature output is coarser than `kir`/`kaz`/`uig`.
* **`chunks` and [XML tags](https://wiki.apertium.org/w/index.php?title=List_of_symbols#XML_tags)** are intentionally out of scope ([upstream](https://github.com/apertium/apertium/issues/185)).
* **Verb transitivity** (`tv`/`iv`) is not emitted as a feature, matching the
  upstream `.udx` decision.
* No Turkic language with **both** an Apertium analyser and a UD treebank is
  currently left out; languages missing one of the two (e.g. Chuvash, Bashkir,
  Crimean Tatar, Dungan) cannot be added.

## How to cite

Greatly appreciated, if you use this work.

```
@misc{apertium2ud2023alekseev,
  title     = {{alexeyev/apertium2ud: mapping tagsets}},
  year      = {2023},
  url       = {https://github.com/alexeyev/apertium2ud}
}
```
