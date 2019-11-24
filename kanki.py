import argparse
import sqlite3
import requests


def parse_args():
    """Add arguments and parse user input"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-b", "--books",
                            help="list books in which words have been looked" +
                                 " up",
                            action="store_true")
    arg_parser.add_argument("db_path", help="the path to vocab.db")
    arg_parser.add_argument("title", help="the title of the book to export")
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
    """Looks up a word in the dictionary, returning a card with the containing
    information"""
    api_key = "your_api_key_here"
    api_request = "https://www.dictionaryapi.com/api/v3/references/learners/json/" + word + "?key=" + api_key

    print("Looking up word... " + word)
    response = requests.get(api_request)
    print("Status code: " + str(response.status_code))

    response = response.json()

    card = dict()
    try:
        # Take the interesting parts of the response
        card["word"] = response[0]["meta"]["id"]
        card["shortdef"] = response[0]["shortdef"]
        card["ipa"] = response[0]["hwi"]["prs"][0]["ipa"]
        return card
    except KeyError as err:
        # Sometimes the response doesn't have the format we expected, will have
        # to handle these edge cases as they become known
        print("Response wasn't in the expected format, key " + str(err) +
              " not found")
        raise
    except TypeError as err:
        # If the response isn't a dictionary, it means we get a list of
        # suggested words so looking up keys won't work
        print(word + " not in learners dictionary! " + str(err))
        raise


def parse_lookup_entry(cursor):
    """Parses a row in the vocab.db LOOKUPS table, returning the word itself and
    the sentence in which it was looked up"""
    word, book_key, sentence = cursor.fetchone()

    # remove 'en:' from word
    return word[3:], sentence


def book_dict(cursor):
    """Create two maps, one from id to book and one from title to book id"""
    cursor.execute("SELECT id, title, authors FROM BOOK_INFO")
    book_info = cursor.fetchall()
    key_to_book = dict()
    title_to_id = dict()

    for book in book_info:
        id = book[0]
        title = book[1]
        author = book[2]
        key_to_book[id] = (title, author)
        title_to_id[title] = id

    return key_to_book, title_to_id


def export_db(cursor, book_title):
    """Will eventually export the vocabulary database to an Anki-readable
    format"""
    key_to_book, title_to_id = book_dict(cursor)
    book_key = title_to_id[book_title]

    cards = []          # successful lookups
    failed_words = []   # words not in expected format
    missing_words = []  # words not in the dictionary

    # Grab all words from the given book
    cursor.execute("SELECT word_key, book_key, usage FROM LOOKUPS" +
                   "WHERE book_key = '" + book_key + "'")
    # Grab a few words for testing
    for _ in range(5):
        word, sentence = parse_lookup_entry(cursor)
        try:
            card = lookup_word(word)
            card["book_title"] = book_title
            card["author"] = key_to_book[book_key]
            cards.append(card)
        except KeyError:
            failed_words.append(word)
        except TypeError:
            missing_words.append(word)

    # Result
    print("\n#################" +
          "\nSuccessfully created cards: " + str(cards) +
          "\nWords not in expected format: " + str(failed_words) +
          "\nWords not in the dictionary: " + str(missing_words))


def main():
    args = parse_args()

    # Connect to vocabulary database file (vocab.db)
    connection = sqlite3.connect(args.db_path)
    cursor = connection.cursor()

    if args.books:
        print_books(cursor)
    else:
        export_db(cursor, args.title)


if __name__ == "__main__":
    main()
