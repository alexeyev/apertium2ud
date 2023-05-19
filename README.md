# apertium2ud

Obtaining the mapping between the two tagsets based 
on the [information from Apertium Wiki](https://wiki.apertium.org/w/index.php?title=List_of_symbols).

Loosely based on [this code](https://github.com/mr-martian/apertium-recursive-learning/blob/master/tags.py), 
hence the GPLv3 license.

To build the machine-readable mapping, run

```bash
python apertium_wiki_parser.py
```

## TODO

* Should sections `chunks` and [XML tags](https://wiki.apertium.org/w/index.php?title=List_of_symbols#XML_tags) be added?
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
