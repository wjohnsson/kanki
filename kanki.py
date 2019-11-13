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


def main():
    args = parse_args()

    connection = sqlite3.connect(args.db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type= 'table'")
    print(str(cursor.fetchall()) + "\n")

    if args.books:
        cursor.execute("SELECT title FROM BOOK_INFO")
        print(cursor.fetchall())


if __name__ == "__main__":
    main()
