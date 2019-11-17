import argparse
import sqlite3
import requests


def parse_args():
    """Add arguments and parse user input"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-b", "--books",
                            help="list books in which words have been looked up",
                            action="store_true")
    arg_parser.add_argument("db_path", help="the path to vocab.db")
    return arg_parser.parse_args()


def print_books(cursor):
    """Print all books in database"""
    cursor.execute("SELECT title FROM BOOK_INFO")
    # Some books seem to appear multiple times, so take unique
    books = set([book_name[0] for book_name in cursor.fetchall()])

    print("Books:")
    for b in books:
        print("  " + b)


def lookup_word(word):
    api_key = "your_api_key_here"
    api_request = "https://www.dictionaryapi.com/api/v3/references/learners/json/" + word + "?key=" + api_key

    print("Looking up word... " + word)
    response = requests.get(api_request)
    print("Status code: " + str(response.status_code))
    return response.json()


def parse_lookup_entry(cursor):
    """Parses a row in the LOOKUPS table"""
    cursor.execute("SELECT word_key, usage FROM LOOKUPS")
    word, sentence = cursor.fetchone()

    # remove 'en:' from word
    return word[3:], sentence


def main():
    args = parse_args()

    # Connect to vocabulary database file
    connection = sqlite3.connect(args.db_path)
    cursor = connection.cursor()

    if args.books:
        print_books(cursor)
    else:
        word, sentence = parse_lookup_entry(cursor)
        print("Resulting json: " + str(lookup_word(word)))


if __name__ == "__main__":
    main()
