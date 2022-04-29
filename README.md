<div id="top"></div>

# kanki
A command line utility for exporting and finding definitions of words looked up in Kindle to the flashcard program
[Anki](https://apps.ankiweb.net/). Every word you highlight while reading will be stored in a file on your Kindle
called `vocab.db`, which kanki uses. Definitions are provided by Meriam-Webster's Learner's Dictionary.

![Preview of what kanki does](img/preview.jpg)

## Dependencies
- [Python 3.8](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/)

To download the remaining python package dependencies run:
```shell
poetry install
```

kanki is known to work with Kindle Paperwhite 3 and flashcards can be imported to Anki 2.1.49.

## Usage
```
usage: kanki [-h] [-l] [-t TITLE [TITLE ...]] [-p DB_PATH] [-k KEY] [-w WORD]

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            list books in vocabulary file
  -t TITLE [TITLE ...], --title TITLE [TITLE ...]
                        the title(s) of the book(s) to export
  -p DB_PATH, --db_path DB_PATH
                        the path to the vocabulary database (default: ./vocab.db)
  -k KEY, --key KEY     your Merriam-Websters Learner's Dictionary API key
  -w WORD, --word WORD  A word to look up in the dictionary.
```


1. Plug in your Kindle and search for `vocab.db` (mine was in the hidden folder `system/vocabulary`).
2. Create an account on [Merriam Webster's Developer Center](https://www.dictionaryapi.com/) to generate an API key to the Learner's Dictionary.

3. For example, to extract all words looked up in two books book run:
````shell
poetry run python kanki --title "Dune" "Hello World" --key "your_api_key" --db_path "path/to/vocab.db"
````


4. If it's the first time you use kanki you must first [import the kanki card type](#import-kanki-card-type-into-anki) into Anki. 

5. kanki will export to a file called `kanki_export.txt` which you can then import to Anki (using `File > Import...`) to
   a deck of your choosing. Use the card type kanki, select _"Fields separated by: Comma"_ and _"Allow HTML in fields"_.

Unfortunately, some words looked up may be missing from the dictionary. These will be written to `kanki_failed_words.txt` which you can manually add later.

![Preview of what an import should look like](img/import.PNG)

### Import kanki card type into Anki
The first time you use kanki you must import the card type, so you get the correct fields and formatting.
In the Anki deck view press `Import File` and select `kanki.apkg` provided in the repo.
This will create a new deck containing one sample card with the kanki card type. 

You can edit the formatting and the name of this card type as you wish, as long as the order of the fields remain the same.

<p align="right">(<a href="#top">back to top</a>)</p>
