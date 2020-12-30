import argparse
import sqlite3
import requests
from collections import defaultdict
import os.path
import sys
from datetime import datetime


def main():
    args = parse_args()

    # Connect sqlite3 to vocabulary database file (default: vocab.db)
    db_path = "vocab.db"
    if args.path:
        db_path = args.path
        assert os.path.isfile(db_path), f"{db_path} not found."
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    if args.list:
        print_books(cursor)
        return

    api_key = args.key
    if args.key:
        file_name = "api_key.txt"
        with open(file_name, "w") as f:
            f.write(args.key)
            print(f"API key written to {file_name}.\n"
                  f"Next time you run kanki, this key will be used (unless you provide a new one).\n")
    else:
        # If no key is given, try to use one that might be saved.
        try:
            with open("api_key.txt", "r") as f:
                api_key = f.read()
        except FileNotFoundError:
            print("You need to add an API key to Merriam-Websters Learners Dictionary using the --key KEY argument.\n"
                  "See https://www.dictionaryapi.com/.")
            return

    if args.title:
        export_book_vocab(cursor, args.title, api_key)


def parse_args():
    """Add arguments and parse user input"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-l", "--list",
                            help="list books in vocabulary file",
                            action="store_true")
    arg_parser.add_argument("-t", "--title",
                            help="the title(s) of the book(s) to export",
                            nargs="+",
                            action="append")
    arg_parser.add_argument("-p", "--path",
                            help="the path to the vocabulary database (default: ./vocab.db)")
    arg_parser.add_argument("-k", "--key",
                            help="your Merriam-Websters Learner's Dictionary API key")

    if len(sys.argv) == 1:
        print("Please specify the title of a book using -t TITLE.\n")
        arg_parser.print_help()

    return arg_parser.parse_args()


def print_books(cursor):
    """Print all books in database"""
    cursor.execute("SELECT title FROM BOOK_INFO")
    # Some books seem to appear multiple times, so take unique
    books = set([book_name[0] for book_name in cursor.fetchall()])

    print("Books:")
    for b in sorted(books):
        print("  " + b)


class Card:
    def __init__(self, word=None, ipa=None, definitions=None, sentence=None, book_title=None, author=None):
        self.word = word
        self.ipa = ipa  # pronunciation
        self.definitions = definitions  # definitions
        self.sentence = sentence
        self.book_title = book_title
        self.author = author


def get_pronunciation(response):
    """Return pronunciation from response."""
    # Where to find the pronunciation differs from word to word
    prs = response["hwi"].get("prs", None)
    altprs = response["hwi"].get("altprs", None)

    ipa = None
    if prs is not None:
        # Prefer to use prs
        ipa = prs[0]["ipa"]
    elif altprs is not None:
        ipa = altprs[0]["ipa"]

    if altprs is None and prs is None:
        # Couldn't find it in "hwi", it sometimes is in "vrs"
        ipa = response["vrs"][0]["prs"][0]["ipa"]

    return ipa


def lookup_word(word, api_key):
    """Looks up a word in the dictionary, returning a card with the word itself,
    as well as its definition and pronunciation."""
    api_request = "https://www.dictionaryapi.com/api/v3/references/learners/json/" + word + "?key=" + api_key

    print("Looking up word: " + word + "... ")
    response = requests.get(api_request)

    if response.status_code != 200:
        print("\nError when querying Merriam-Webster's Dictionary API.")
    elif "Invalid API key" in response.text:
        print("Invalid API key. Make sure it is subscribed to Merriam Websters Learners Dictionary.\n"
              "You can replace the current key by providing the argument --key KEY.\n"
              "Exiting...")
        sys.exit()

    response = response.json()[0]
    try:
        # Take the interesting parts of the response
        word_stem = response["meta"]["stems"][0]
        definitions = response["shortdef"]
        ipa = get_pronunciation(response)
        print("OK")
        return word_stem, definitions, ipa
    except KeyError as err:
        # Sometimes the response doesn't have the format we expected, will have
        # to handle these edge cases as they become known
        print("Response wasn't in the expected format. Reason: key "
              + str(err) + " not found")
        raise
    except TypeError:
        # If the response isn't a dictionary, it means we get a list of
        # suggested words so looking up keys won't work
        print(word + " not found in Merriam-Webster's Learner's dictionary!")
        raise


def book_dicts(cursor):
    """Return two dictionaries, one from book key to book title and author
    as well as one from book title to book keys."""
    cursor.execute("SELECT id, title, authors FROM BOOK_INFO")
    book_info = cursor.fetchall()
    key_to_book = dict()
    # One book can have multiple keys (maybe has something to do with Kindle versions?)
    title_to_keys = defaultdict(list)

    for book in book_info:
        book_key = book[0]
        title = book[1]
        author = book[2]

        key_to_book[book_key] = (title, author)
        title_to_keys[title].append(book_key)

    return key_to_book, title_to_keys


def write_to_export_file(cards, book_titles, file_name="kanki_export.txt"):
    """Write all cards to a file in an Anki readable format."""
    today = datetime.today().strftime("%Y-%m-%d %H:%M")
    with open(file_name, "w") as output:
        # Nice to have some metadata in the export file
        listed_books = "".join(["\n#  -" + title for title in book_titles])
        comment = (f"# Card data generated on {today} by kanki from book(s):"
                   f"{listed_books}"
                   "\n#"
                   "\n# Format is:"
                   "\n# 'word', 'pronunciation', 'sentence', 'definition', 'author'\n\n")
        output.write(comment)

        for card in cards:
            definitions = card.definitions
            if card.definitions is not None:
                # A word may have multiple definitions, join them with a semicolon.
                definitions = "; ".join(card.definitions)

            # Collect all card data in a list and make sure all double quotes are
            # single quotes in the file so that it is readable by Anki
            card_data = [card.word,
                         card.ipa,
                         card.sentence.replace('"', "'"),
                         definitions,
                         card.book_title.replace('"', "'"),
                         card.author]
            card_data = replace_nones(card_data)

            # Anki accepts plaintext files with fields separated by commas.
            # Surround all fields in quotes and write in same order as the kanki card type.
            output.write('"{0}"\n'.format('", "'.join(card_data)))


def replace_nones(strings):
    """Replaces all None to empty string."""
    return list(map(lambda s: "" if s is None else s, strings))


def export_book_vocab(cursor, book_titles, api_key, amount=-1):
    """Export all words from the given book titles."""
    key_to_book, title_to_keys = book_dicts(cursor)

    cards = []  # successful lookups
    failed_words = []  # words not in expected format
    missing_words = []  # words not in the dictionary

    # Flatten list given by argparse
    book_titles = [book for sublist in book_titles for book in sublist]
    for book_title in book_titles:
        print(f"\n--- Exporting book: {book_title}")
        book_keys = title_to_keys[book_title]

        # Grab all words from the given book
        condition = "'" + "' OR '".join(book_keys) + "'"  # surround keys with single quotes
        cursor.execute("SELECT word_key, book_key, usage FROM LOOKUPS" +
                       " WHERE book_key = " + condition)
        rows = cursor.fetchall()

        # For testing: specify the amount of words you want to export from each book
        if amount >= -1:
            rows = rows[:amount]

        for row in rows:
            assert row[0][:2] == "en", "Only english words are supported."
            word = row[0][3:]  # remove 'en:' from word_key
            sentence = row[2]  # the sentence in which the word was looked up

            card = Card()
            card.word = word
            card.sentence = sentence.replace(word, "<b>" + word + "</b>")
            card.book_title = book_title
            card.author = key_to_book[book_keys[0]][1]
            try:
                word_stem, definitions, ipa = lookup_word(word, api_key)

                # Might give two inflections of a word - could be useful for learning
                card.word = word_stem
                card.definitions = definitions
                card.ipa = ipa
                cards.append(card)
            except KeyError:
                failed_words.append(card)
            except TypeError:
                missing_words.append(card)

    success_file_path = "kanki_export.txt"
    failed_file_path = "kanki_failed_words.txt"
    write_to_export_file(cards, book_titles, success_file_path)
    write_to_export_file(failed_words + missing_words, book_titles, failed_file_path)

    print(f"\n####  EXPORT INFO  ####"
          f"\nBooks exported: {book_titles}"
          f"\nSuccessfully exported {len(cards)} cards to '{success_file_path}.'"
          f"\n{len(failed_words)} words not in expected format, written to {failed_file_path}."
          f"\n{len(missing_words)} words not in the online dictionary, also written to {failed_file_path}.")


if __name__ == "__main__":
    main()
