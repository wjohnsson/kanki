# kanki
kanki is a command line utility for exporting and finding definitions of words looked up in Kindle to the flashcard program [Anki](https://apps.ankiweb.net/). Every word you highlight while reading will be stored in a file on your Kindle called `vocab.db`, which kanki uses. Definitions are provided by Meriam-Webster's Learner's Dictionary.

![Preview of what kanki does](img/preview.jpg)

## How to use
```
usage: kanki.py [-h] [-l] [-t TITLE [TITLE ...]] [-p PATH] [-k KEY]

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            list books in vocabulary file
  -t TITLE [TITLE ...], --title TITLE [TITLE ...]
                        the title(s) of the book(s) to export
  -p PATH, --path PATH  the path to the vocabulary database (default: ./vocab.db)
  -k KEY, --key KEY     your Merriam-Websters Learner's Dictionary API key
```

kanki is known to work with Kindle Paperwhite 3. It uses python3 and the [Requests library](https://requests.readthedocs.io/en/master/) so first make sure you have that installed eg. by running `pip install requests`.

1. Clone the repository: `git clone https://github.com/wjohnsson/kanki.git`

2. If it's the first time you use kanki you must first [import the kanki card type](#import-kanki-card-type) into Anki. Also you have to create an account on [Merriam Webster's Developer Center](https://www.dictionaryapi.com/) to generate an API key to the Learner's Dictionary.

3. Plug in your Kindle and search for `vocab.db` (mine was in a hidden folder called `system/vocabulary/`).

4. Run the script, eg. `python kanki.py --title "1984" --path vocab.db --key <api-key>`

5. kanki will export to a file called `kanki_export.txt` which you can then import to Anki (using `file > import...`) to a deck of your choosing. Make sure you have the card type kanki (or whatever you've renamed it to), select "Fields separated by: Comma" and "Allow HTML in fields".

![Preview of what an import should look like](img/import.PNG)

### Import kanki card type into Anki
The first time you use kanki you must import the card type so you get the correct fields and formatting. In the Anki deck view press `Import File` and select `kanki.apkg` provided in the repo. This will create a new deck containing one sample card with the kanki card type. 

You can edit the formatting and the name of this card type as you wish, as long as the order of the fields remain the same.

