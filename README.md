# apertium2ud

Obtaining the mapping between the two tagsets based on the [information from Apertium Wiki](https://wiki.apertium.org/w/index.php?title=List_of_symbols).

Loosely based on [this code](https://github.com/mr-martian/apertium-recursive-learning/blob/master/tags.py), hence the GPLv3 license.

```bash
python 
```

## TODO

* Should sections `chunks` and [XML tags](https://wiki.apertium.org/w/index.php?title=List_of_symbols#XML_tags) be added?
* Add conversions Apertium -> UD, UD -> Apertium based on the constructed JSON file
* Upload the converter as a package to PyPI
* Tests: Apertium -> UD -> Apertium, UD -> Apertium -> UD (sometimes losses are inevitable)
