import argparse
import sqlite3


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


def main():
    args = parse_args()

    # Connect to vocabulary database
    connection = sqlite3.connect(args.db_path)
    cursor = connection.cursor()

    if args.books:
        print_books(cursor)


if __name__ == "__main__":
    main()
