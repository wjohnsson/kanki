import argparse
import os.path
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple, Iterable, Union

import requests


def main():
    # Argument handling
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()
    no_args_given = len(sys.argv) == 1
    if no_args_given:
        arg_parser.print_help()
        sys.exit()

    # API key management
    api_key_path = '../api_key.txt'
    api_key = args.key
    if api_key:
        save_api_key_to_file(api_key, api_key_path)
    else:
        api_key = read_api_key_from_file(api_key_path)

    # Connect sqlite3 module to vocabulary file
    require_sql = args.list or args.title
    if require_sql:
        cursor = get_sql_cursor(args.db_path)

        if args.list:
            print_books(cursor)

        if args.title:
            export_book_vocab(cursor, api_key, flatten(args.title))

    if args.word:
        # For debugging, we can look up single words instead of going through a whole book.
        lookup_word(args.word, api_key)


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
                            help='A word to look up in the dictionary.')
    return arg_parser


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


def print_books(cursor):
    """Print all books in database"""
    cursor.execute("SELECT title FROM BOOK_INFO")
    # Some books seem to appear multiple times, so take unique
    books = set([book_name[0] for book_name in cursor.fetchall()])

    print('Books:')
    for b in sorted(books):
        print('  ' + b)


def export_book_vocab(cursor: sqlite3.Cursor, api_key: str, book_titles: List[str]):
    """Export all words from the given book titles."""
    cards, failed_words, missing_words = create_flashcards(cursor, api_key, book_titles)

    successful_words_path = '../kanki_export.txt'
    failed_file_path = '../kanki_failed_words.txt'

    write_to_export_file(cards, book_titles, successful_words_path)
    write_to_export_file(failed_words + missing_words, book_titles, failed_file_path)

    print(f'\n####  EXPORT INFO  ####'
          f'\nBooks exported: {book_titles}'
          f'\nSuccessfully exported {len(cards)} cards to \'{successful_words_path}.\''
          f'\n{len(failed_words)} words not in expected format, written to {failed_file_path}.'
          f'\n{len(missing_words)} words not in the online dictionary, also written to {failed_file_path}.')


def create_flashcards(cursor: sqlite3.Cursor, api_key: str, book_titles: List[str]):
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
                card = set_word_meta_data(api_key, card, word)
                cards.append(card)
            except KeyError:
                failed_words.append(card)
            except TypeError:
                missing_words.append(card)
    return cards, failed_words, missing_words


def lookup_word(word, api_key):
    """Looks up a word in the dictionary, returning a card with the word itself,
    as well as its definition and pronunciation."""
    api_request = 'https://www.dictionaryapi.com/api/v3/references/learners/json/' + word + '?key=' + api_key

    print('Looking up word: ' + word + '... ')
    response = requests.get(api_request)

    if response.status_code != 200:
        print('\nError when querying Merriam-Webster\'s Dictionary API.')
    elif 'Invalid API key' in response.text:
        print('Invalid API key. Make sure it is subscribed to Merriam Websters Learners Dictionary.\n'
              'You can replace the current key by providing the argument [-k KEY].\n'
              'Exiting...')
        sys.exit()

    response = response.json()[0]
    try:
        # Take the interesting parts of the response
        word_stem = response['meta']['stems'][0]
        definitions = response['shortdef']
        ipa = get_pronunciation(response)
        print('OK')
        return word_stem, definitions, ipa
    except KeyError as err:
        # Sometimes the response doesn't have the format we expected, will have to handle these edge cases as they
        # become known.
        print(f'Response wasn\'t in the expected format. Reason: key {str(err)} not found')
        raise
    except TypeError:
        # If the response isn't a dictionary, it means we get a list of suggested words so looking up keys won't work.
        print(word + ' not found in Merriam-Webster\'s Learner\'s dictionary!')
        raise


class Card:
    def __init__(self, word, sentence, book_title, author, ipa=None, definitions=None):
        self.word = word
        self.sentence = surround_substring_with_html(sentence, word, 'b')
        self.book_title = book_title
        self.author = author
        self.ipa = ipa  # pronunciation
        self.definitions = definitions  # definitions


def get_pronunciation(response):
    """Return pronunciation from response."""
    # Where to find the pronunciation differs from word to word
    prs = response['hwi'].get('prs', None)
    altprs = response['hwi'].get('altprs', None)

    ipa = None
    if prs is not None:
        # Prefer to use prs
        ipa = prs[0]['ipa']
    elif altprs is not None:
        ipa = altprs[0]['ipa']

    if altprs is None and prs is None:
        # Couldn't find it in "hwi", it sometimes is in "vrs"
        ipa = response['vrs'][0]['prs'][0]['ipa']

    return ipa


def get_book_dicts(cursor):
    """Return two dictionaries, one from book key to book title and author
    as well as one from book title to book keys."""
    cursor.execute('SELECT id, title, authors FROM BOOK_INFO')
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


def get_book_keys(cursor, book_title: str) -> List[str]:
    """Return the keys used to identify a book in the Kindle vocabulary database."""
    cursor.execute(f'SELECT id FROM BOOK_INFO WHERE title = "{book_title}"')
    book_keys = cursor.fetchall()
    return flatten(book_keys)


def write_to_export_file(cards: List[Card], book_titles: List[str], path: Union[str, bytes, os.PathLike]):
    """Write all cards to a file in an Anki readable format."""
    datetime_now = datetime.today().strftime('%Y-%m-%d %H:%M')
    with open(path, 'w') as output:
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

            # Had some issues with text encoding, hence the strange need for encoding/decoding
            output.write(card_data_str.encode('utf-8').decode())


def replace_nones(strings: List[str]):
    """Replaces all None to empty string."""
    return list(map(lambda s: '' if s is None else s, strings))


def set_word_meta_data(api_key, card, word):
    word_stem, definitions, ipa = lookup_word(word, api_key)

    # Might give two inflections of a word - could be useful for learning
    card.word = word_stem
    card.definitions = definitions
    card.ipa = ipa
    return card


def surround_substring_with_html(string: str, substring: str, html: str):
    open_tag = f'<{html}>'
    close_tag = f'</{html}>'
    return string.replace(substring, open_tag + substring + close_tag)


def get_word(lookup: Tuple) -> str:
    """Return the word from a Kindle lookup"""
    word_index = 0
    assert lookup[word_index][:2] == 'en', 'Only english words are supported.'
    word = lookup[word_index][3:]  # remove 'en:' from word_key
    return word


def get_lookups(cursor, book_title):
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
