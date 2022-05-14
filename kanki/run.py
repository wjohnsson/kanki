import argparse
import logging
import os
import os.path
import sqlite3
import sys
from datetime import datetime
from typing import Iterable, List, Optional, Tuple, Union

from kanki.exceptions import MissingBookError
from kanki.card import Card
from kanki.merriam_webster import MWDictionary


def main():
    logging.basicConfig()
    # Argument handling
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    no_args_given = len(sys.argv) == 1
    if no_args_given:
        arg_parser.print_help()
        print('Exiting...')
        sys.exit()

    kanki = Kanki()
    api_key_path = 'api_key.txt'
    api_key = args.key
    if api_key:
        save_api_key_to_file(api_key, api_key_path)

    dictionary_required = args.title or args.word
    if dictionary_required:
        if not api_key:
            api_key = read_api_key_from_file(api_key_path)
        kanki.dictionary = MWDictionary(api_key)

    sql_required = args.list or args.title
    if sql_required:
        kanki.connect_sql_cursor(args.db_path)

        if args.list:
            kanki.print_books()

        if args.title:
            kanki.book_titles = Kanki.flatten(args.title)
            kanki.export_book_lookups()

    if args.word:
        # For debugging, we can look up single words instead of going through a whole book.
        kanki.dictionary.lookup(args.word)


def get_arg_parser():
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


def save_api_key_to_file(key: str, path: Union[str, bytes, os.PathLike]):
    """Save the user's API key to file (as plaintext)."""
    with open(path, 'w') as f:
        f.write(key)
        print(f'API key written to "{path}".\n'
              f'Next time you run kanki, this key will be used (unless you provide a new one).\n')


def read_api_key_from_file(path: Union[str, bytes, os.PathLike]):
    """Read API key that might be saved in a file, if kanki was used before."""
    try:
        with open(path, 'r') as f:
            api_key = f.read()
    except FileNotFoundError:
        logging.error(f'Couldn\'t find API key file "{str(path)}".')
        print(f'You need to add an API key to Merriam-Websters Learners Dictionary using the [-k KEY] argument.\n'
              f'See https://www.dictionaryapi.com/.')
        print('Exiting...')
        sys.exit(1)
    return api_key


class Kanki:
    def __init__(self, dictionary=None, db_cursor=None, book_titles=None):
        self.dictionary: Optional[MWDictionary] = dictionary
        self.db_cursor: Optional[sqlite3.Cursor] = db_cursor
        self.book_titles: Optional[List[str]] = book_titles

    def connect_sql_cursor(self, db_path: str) -> None:
        """Connect the sql cursor to the given Kindle vocabulary file."""
        if not os.path.isfile(db_path):
            logging.error(f'Vocabulary database file "{db_path}" not found')
            print(f'See https://github.com/wjohnsson/kanki/blob/master/README.md#usage how to find the Kindle '
                  f'vocabulary database file.')
            print('Exiting...')
            sys.exit(1)
        connection = sqlite3.connect(db_path)
        self.db_cursor = connection.cursor()

    def export_book_lookups(self) -> None:
        """Export all lookups in the given book titles to a Kanki readable format."""
        try:
            self.book_titles = self.remove_books_until_safe()
        except MissingBookError:
            print('Make sure all given book titles match the output given by --list (case insensitive)')
            print('Exiting...')
            sys.exit(1)

        cards, failed_words, missing_words = self.create_flashcards()

        successful_words_path = 'kanki_export.txt'
        failed_file_path = 'kanki_failed_words.txt'

        self.write_to_export_file(cards, successful_words_path)
        self.write_to_export_file(failed_words + missing_words, failed_file_path)

        print(f'\n####  EXPORT INFO  ####'
              f'\nBooks exported: {self.book_titles}'
              f'\nSuccessfully exported {len(cards)} cards to \'{successful_words_path}.\''
              f'\n{len(failed_words)} words not in expected format, written to {failed_file_path}.'
              f'\n{len(missing_words)} words not in the online dictionary, also written to {failed_file_path}.')

    def remove_books_until_safe(self) -> List[str]:
        """Remove books until we are below the API query limit."""
        remaining_books = self.book_titles.copy()  # to ensure the function has no side effects

        # TODO: See if this can be replaced with itertools.dropwhile()
        while self.too_many_api_queries(remaining_books):
            remaining_books.pop()
            if not remaining_books:
                logging.error(f'ERROR: kanki cannot handle the case where one book has more than '
                              f'{self.dictionary.max_queries} lookups')
                print('The chosen book(s) have too many lookups for the free version of Merriam Webster\'s API. '
                      'Please choose another set of books.')
                print('Exiting...')
                sys.exit(1)
        return remaining_books

    def too_many_api_queries(self, books: List[str]) -> bool:
        """Return true if the given book titles have more lookups than the dictionary supports."""
        total_lookups = sum(self.count_lookups(b) for b in books)
        return total_lookups > self.dictionary.max_queries

    def count_lookups(self, book_title: str) -> int:
        """Return the number of Kindle lookups in the given book title."""
        book_keys = self.get_book_keys(book_title)
        placeholders = Kanki.get_sql_placeholders(len(book_keys))
        sql_query = f'SELECT COUNT (*) FROM LOOKUPS WHERE book_key IN ({placeholders})'
        self.db_cursor.execute(sql_query, book_keys)
        count = self.db_cursor.fetchone()[0]
        return count

    def get_book_keys(self, book_title: str) -> List[str]:
        """Return the keys used to identify a book in the Kindle vocabulary database."""
        sql_query = 'SELECT id FROM BOOK_INFO WHERE title = (?) COLLATE NOCASE'
        self.db_cursor.execute(sql_query, (book_title,))
        book_keys = self.db_cursor.fetchall()

        if not book_keys:
            raise MissingBookError(f'The book {book_title} is not in the vocabulary database')

        return Kanki.flatten(book_keys)

    def create_flashcards(self) -> Tuple[List[Card], List[Card], List[Card]]:
        cards = []  # words successfully found in dictionary
        failed_words = []  # words where the response from the dictionary was not what we expected
        missing_words = []  # words not in the dictionary

        for book_title in self.book_titles:
            lookups = self.get_lookups(book_title)

            print(f'--- Exporting {len(lookups)} lookups from book: {book_title}')
            for i, lookup in enumerate(lookups):
                word = Kanki.get_word(lookup)
                sentence = lookup[2]  # the sentence in which the word was looked up
                author = self.get_author(book_title)

                card = Card(word, sentence, book_title, author)
                try:
                    digits = len(str(len(lookups)))
                    progress = f'[{str(i + 1).zfill(digits)}/{len(lookups)}]'
                    print(f'{progress} Looking up word {word}... ', end='')
                    card.set_word_meta_data(self.dictionary, word)
                    cards.append(card)
                except KeyError:
                    failed_words.append(card)
                except TypeError:
                    missing_words.append(card)
        return cards, failed_words, missing_words

    @staticmethod
    def get_word(lookup: tuple) -> str:
        """Return the word from a Kindle lookup."""
        word_index = 0
        assert lookup[word_index][:2] == 'en', 'ERROR: Only english books are supported.'
        word = lookup[word_index][3:]  # remove 'en:' from word_key
        return word

    def print_books(self) -> None:
        """Print all books in the Kindle database."""
        sql_query = "SELECT title FROM BOOK_INFO"
        self.db_cursor.execute(sql_query)
        # Some books seem to appear multiple times, so take only unique
        books = set([book_name[0] for book_name in self.db_cursor.fetchall()])

        # Pretty printing
        max_book_len = max(map(len, books))
        digits = len(str(max_book_len))
        spaces_count = 2
        dashes_count = max_book_len + digits + spaces_count

        print('Books found:')
        print(f'{"":-<{dashes_count}}')
        for i, book in enumerate(sorted(books)):
            print(f'{i + 1:<{digits + spaces_count}}{book:<40s}')

    def get_lookups(self, book_title: str) -> List[tuple]:
        """Return all Kindle lookups in the given book."""
        book_keys = self.get_book_keys(book_title)
        placeholders = Kanki.get_sql_placeholders(len(book_keys))
        sql_query = f'SELECT word_key, book_key, usage FROM LOOKUPS WHERE book_key IN ({placeholders})'
        self.db_cursor.execute(sql_query, book_keys)
        rows = self.db_cursor.fetchall()
        return rows

    def get_author(self, book_title: str) -> str:
        """Return the author of a book in the Kindle database given the book's title."""
        sql_query = 'SELECT authors FROM BOOK_INFO WHERE title = ?'
        self.db_cursor.execute(sql_query, (book_title,))
        book_author = self.db_cursor.fetchone()[0]
        return book_author

    @staticmethod
    def get_sql_placeholders(amount: int) -> str:
        """Return the SQL string used for a given amount of placeholders."""
        if amount <= 0:
            raise ValueError(f'Bad number of placeholders: {amount}, expected a non-zero positive amount')
        if amount > 999:
            raise ValueError('sqlite only supports 999 placeholders: '
                             'https://www.sqlite.org/limits.html#max_variable_number')
        placeholders = ','.join('?' * amount)
        return placeholders

    @staticmethod
    def flatten(items: List[Iterable]) -> List:
        return [item for sublist in items for item in sublist]

    def write_to_export_file(self, cards: List[Card], path: Union[str, bytes, os.PathLike]) -> None:
        """Write all cards to file in an Anki readable format."""
        with open(path, 'w', encoding='utf-8') as output:
            output.write(self.metadata_about_export())

            for card in cards:
                output.write(card.get_csv_encoding())

        if not cards:
            return
        Kanki.check_number_of_card_fields(cards[0])

    @staticmethod
    def check_number_of_card_fields(card: Card):
        number_of_fields = len(vars(card))
        expected_number_of_fields = len(card.card_fields_in_order())
        if number_of_fields > expected_number_of_fields:
            logging.warning(f'The number of fields in a card have increased, '
                            f'consider adding them to the Anki card type.')

    def metadata_about_export(self) -> str:
        datetime_now = datetime.today().strftime('%Y-%m-%d %H:%M')
        itemized_books = ''.join([f'#  - {title}\n' for title in self.book_titles])
        metadata = (f'# Card data generated on {datetime_now} by kanki from book(s):\n'
                    f'{itemized_books}'
                    '#\n'
                    '# Format:\n'
                    '# word,pronunciation,sentence,definition,author\n\n')
        return metadata


if __name__ == '__main__':
    main()
