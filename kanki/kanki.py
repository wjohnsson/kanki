import argparse
import os.path
import sqlite3
import sys
from datetime import datetime
from typing import List, Iterable, Union

from card import Card
from merriam_webster import MWDictionary


def main():
    # Argument handling
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()
    no_args_given = len(sys.argv) == 1
    if no_args_given:
        arg_parser.print_help()
        sys.exit()

    api_key_path = 'api_key.txt'
    api_key = args.key
    if api_key:
        save_api_key_to_file(api_key, api_key_path)

    dictionary = None
    dictionary_required = args.title or args.word
    if dictionary_required:
        if not api_key:
            api_key = read_api_key_from_file(api_key_path)
        dictionary = MWDictionary(api_key)

    sql_required = args.list or args.title
    if sql_required:
        cursor = get_sql_cursor(args.db_path)

        if args.list:
            print_books(cursor)

        if args.title:
            export_book_vocab(cursor, dictionary, flatten(args.title))

    if args.word:
        # For debugging, we can look up single words instead of going through a whole book.
        dictionary.lookup(args.word)


def get_arg_parser():
    """Add arguments and parse user input"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-l', '--list',
                            help='list books in vocabulary file',
                            action='store_true')
    arg_parser.add_argument('-t', '--title',
                            help='the title(s) of the book(s) to export',
                            nargs='+',
                            action='append')
    arg_parser.add_argument('-p', '--db_path', type=str, default='vocab.db',
                            help='the path to the vocabulary database (default: ./vocab.db)')
    arg_parser.add_argument('-k', '--key', type=str,
                            help='your Merriam-Websters Learner\'s Dictionary API key')
    arg_parser.add_argument('-w', '--word',
                            help='a single word to look up in the dictionary.')
    return arg_parser


class Kanki:
    def __init__(self):
        self.dictionary = None
        self.db_cursor = None


def get_sql_cursor(db_path: str) -> sqlite3.Cursor:
    """Return the sqlite cursor connected to the Kindle vocabulary database."""
    if not os.path.isfile(db_path):
        print(f'ERROR: Vocabulary database file {db_path} not found.\n'
              f'See kanki documentation on GitHub for how to export it from your Kindle.')
        sys.exit()
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    return cursor


def read_api_key_from_file(path: Union[str, bytes, os.PathLike]):
    """Read API key that might be saved in a file, if kanki was used before."""
    try:
        with open(path, 'r') as f:
            api_key = f.read()
    except FileNotFoundError:
        print(f'ERROR: Couldn\'t find file {str(path)}')
        print('You need to add an API key to Merriam-Websters Learners Dictionary using the [-k KEY] argument.\n'
              'See https://www.dictionaryapi.com/.')
        sys.exit()
    return api_key


def save_api_key_to_file(key: str, path: Union[str, bytes, os.PathLike]):
    """Save the user's API key to file (as plaintext)."""
    with open(path, 'w') as f:
        f.write(key)
        print(f'API key written to {key}.\n'
              f'Next time you run kanki, this key will be used (unless you provide a new one).\n')


def print_books(cursor: sqlite3.Cursor):
    """Print all books in database"""
    cursor.execute("SELECT title FROM BOOK_INFO")
    # Some books seem to appear multiple times, so take unique
    books = set([book_name[0] for book_name in cursor.fetchall()])

    print('Books:')
    for b in sorted(books):
        print('  ' + b)


def export_book_vocab(cursor: sqlite3.Cursor, dictionary: MWDictionary, book_titles: List[str]):
    """Export all words from the given book titles."""
    cards, failed_words, missing_words = create_flashcards(cursor, dictionary, book_titles)

    successful_words_path = 'kanki_export.txt'
    failed_file_path = 'kanki_failed_words.txt'

    write_to_export_file(cards, book_titles, successful_words_path)
    write_to_export_file(failed_words + missing_words, book_titles, failed_file_path)

    print(f'\n####  EXPORT INFO  ####'
          f'\nBooks exported: {book_titles}'
          f'\nSuccessfully exported {len(cards)} cards to \'{successful_words_path}.\''
          f'\n{len(failed_words)} words not in expected format, written to {failed_file_path}.'
          f'\n{len(missing_words)} words not in the online dictionary, also written to {failed_file_path}.')


def create_flashcards(cursor: sqlite3.Cursor, dictionary: MWDictionary, book_titles: List[str]):
    cards = []  # words successfully found in dictionary
    failed_words = []  # words where the response from the dictionary was not what we expected
    missing_words = []  # words not in the dictionary
    for book_title in book_titles:
        print(f'\n--- Exporting book: {book_title}')

        lookups = get_lookups(cursor, book_title)
        for lookup in lookups:
            word = get_word(lookup)
            sentence = lookup[2]  # the sentence in which the word was looked up
            author = get_author(cursor, book_title)

            card = Card(word, sentence, book_title, author)
            try:
                card.set_word_meta_data(dictionary, word)
                cards.append(card)
            except KeyError:
                failed_words.append(card)
            except TypeError:
                missing_words.append(card)
    return cards, failed_words, missing_words


def get_book_keys(cursor: sqlite3.Cursor, book_title: str) -> List[str]:
    """Return the keys used to identify a book in the Kindle vocabulary database."""
    cursor.execute(f'SELECT id FROM BOOK_INFO WHERE title = "{book_title}"')
    book_keys = cursor.fetchall()
    return flatten(book_keys)


def write_to_export_file(cards: List[Card], book_titles: List[str], path: Union[str, bytes, os.PathLike]):
    """Write all cards to a file in an Anki readable format."""
    datetime_now = datetime.today().strftime('%Y-%m-%d %H:%M')
    with open(path, 'w', encoding='utf-8') as output:
        # Nice to have some metadata in the export file
        listed_books = ''.join(['\n#  - ' + title for title in book_titles])
        comment = (f'# Card data generated on {datetime_now} by kanki from book(s):'
                   f'{listed_books}'
                   '\n#'
                   '\n# Format:'
                   '\n# word,pronunciation,sentence,definition,author\n\n')
        output.write(comment)

        for card in cards:
            definitions = card.definitions
            if card.definitions is not None:
                # A word may have multiple definitions, join them with a semicolon.
                definitions = '; '.join(card.definitions)

            # Collect all card data in a list and make sure all double quotes are
            # single quotes in the file so that it is readable by Anki
            card_data = [card.word,
                         card.ipa,
                         card.sentence.replace('"', '\''),
                         definitions,
                         card.book_title.replace('"', '\''),
                         card.author]
            card_data = replace_nones(card_data)

            # Anki accepts plaintext files with fields separated by commas.
            # Surround all fields in quotes and write in same order as the kanki card type.
            card_data_str = '"{0}"\n'.format('", "'.join(card_data))

            output.write(card_data_str)


def replace_nones(strings: List[str]) -> List[str]:
    """Replaces all Nones in a list with an empty string."""
    return list(map(lambda s: '' if s is None else s, strings))


def get_word(lookup: tuple) -> str:
    """Return the word from a Kindle lookup"""
    word_index = 0
    assert lookup[word_index][:2] == 'en', 'ERROR: Only english books are supported.'
    word = lookup[word_index][3:]  # remove 'en:' from word_key
    return word


def get_lookups(cursor: sqlite3.Cursor, book_title: str) -> List[tuple]:
    """Return all Kindle lookups in the given book."""
    book_keys = get_book_keys(cursor, book_title)
    condition = "'" + "' OR '".join(book_keys) + "'"  # surround keys with single quotes
    cursor.execute(f'SELECT word_key, book_key, usage FROM LOOKUPS WHERE book_key = {condition}')
    rows = cursor.fetchall()
    return rows


def get_author(cursor: sqlite3.Cursor, book_title: str) -> str:
    """Return the author of a book in the Kindle database given the book's title."""
    cursor.execute(f'SELECT authors FROM BOOK_INFO WHERE title = "{book_title}"')
    book_author = cursor.fetchone()[0]
    return book_author


def flatten(items: List[Iterable]) -> List:
    return [item for sublist in items for item in sublist]


if __name__ == '__main__':
    main()
