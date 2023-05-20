# apertium2ud

Obtaining the mapping between the two tagsets based 
on the [information from Apertium Wiki](https://wiki.apertium.org/w/index.php?title=List_of_symbols).

Loosely based on [this code](https://github.com/mr-martian/apertium-recursive-learning/blob/master/tags.py), 
hence the GPLv3 license.

To build the machine-readable mapping, run

```bash
python apertium_wiki_parser.py
```

## UD to Apertium

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

## TODO

* Should sections `chunks` and [XML tags](https://wiki.apertium.org/w/index.php?title=List_of_symbols#XML_tags) be added? [No](https://github.com/apertium/apertium/issues/185).
* Add conversions Apertium -> UD, UD -> Apertium based on the constructed JSON file
* Upload the converter as a package to PyPI
* Tests: Apertium -> UD -> Apertium, UD -> Apertium -> UD (sometimes losses are inevitable)

## How to cite

Greatly appreciated, if you use this work.

```
@misc{apertium2ud2023alekseev,
  title     = {{alexeyev/apertium2ud: mapping tagsets}},
  year      = {2023},
  url       = {https://github.com/alexeyev/apertium2ud}
}
```
