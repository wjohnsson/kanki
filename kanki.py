import argparse
import sqlite3
import requests


def parse_args():
    """Add arguments and parse user input"""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-b", "--books",
                            help="list books in vocabulary file",
                            action="store_true")
    arg_parser.add_argument("-t", "--title",
                            help="the title of the book to export")
    arg_parser.add_argument("db_path",
                            help="the path to the vocabulary database")
    return arg_parser.parse_args()


def print_books(cursor):
    """Print all books in database"""
    cursor.execute("SELECT title FROM BOOK_INFO")
    # Some books seem to appear multiple times, so take unique
    books = set([book_name[0] for book_name in cursor.fetchall()])

    print("Books:")
    for b in books:
        print("  " + b)


def get_pronunciation(response):
    """Return pronunciation from response"""
    # Where to find the pronunciation differs from word to word
    prs = response[0]["hwi"].get("prs", None)
    altprs = response[0]["hwi"].get("altprs", None)

    if altprs is not None:
        ipa = altprs[0]["ipa"]
    if prs is not None:
        # Choose prs by default
        ipa = prs[0]["ipa"]

    if altprs is None and prs is None:
        # Couldn't find it in "hwi", it sometimes is in "vrs"
        ipa = response[0]["vrs"][0]["prs"][0]["ipa"]

    return ipa


def lookup_word(word):
    """ Looks up a word in the dictionary, returning a card with the word itself,
    definition and pronunciation"""
    api_key = "your_api_key_here"
    api_request = "https://www.dictionaryapi.com/api/v3/references/learners/json/" + word + "?key=" + api_key

    print("Looking up word: " + word + "... ")
    response = requests.get(api_request)

    if response.status_code != 200:
        print("\nError when querying Merriam Webster's Dictionary API.")
    else:
        print("OK")

    response = response.json()

    card = dict()
    try:
        # Take the interesting parts of the response
        card["word"] = response[0]["meta"]["stems"][0]
        card["shortdef"] = response[0]["shortdef"]
        card["ipa"] = get_pronunciation(response)
        return card
    except KeyError as err:
        # Sometimes the response doesn't have the format we expected, will have
        # to handle these edge cases as they become known
        print("Response wasn't in the expected format. Reason: key "
              + str(err) + " not found")
        raise
    except TypeError as err:
        # If the response isn't a dictionary, it means we get a list of
        # suggested words so looking up keys won't work
        print(word + " not found in Merriam Webster's Learner's dictionary!")
        raise


def book_dict(cursor):
    """Return two dictionaries, one from book key to book title and author
    as well as one from book title to book key"""
    cursor.execute("SELECT id, title, authors FROM BOOK_INFO")
    book_info = cursor.fetchall()
    key_to_book = dict()
    title_to_key = dict()

    for book in book_info:
        book_key = book[0]
        title = book[1]
        author = book[2]

        key_to_book[book_key] = (title, author)
        title_to_key[title] = book_key

    return key_to_book, title_to_key


def write_to_export_file(cards):
    """Write cards to an Anki readable format."""
    # Anki accepts plaintext files with fields separated by commas
    output = open("kanki.txt", "w", encoding="utf-8")

    for card in cards:
        # A word may have multiple definitions, join them with a semicolon
        definitions = "; ".join(card["shortdef"])
        # Surround all fields in quotes and write in same order as in Anki
        output.write('"{0}"'.format('", "'.join(
            [card["word"],
             card["ipa"],
             card["sentence"].replace('"', "'"),  # escape " in sentences
             definitions,
             card["book_title"],
             card["author"]])) + "\n")


def export_book_vocab(cursor, book_title, amount=-1):
    """Export all words from the given book."""
    key_to_book, title_to_id = book_dict(cursor)
    book_key = title_to_id[book_title]

    cards = []          # successful lookups
    failed_words = []   # words not in expected format
    missing_words = []  # words not in the dictionary

    # Grab all words from the given book
    cursor.execute("SELECT word_key, book_key, usage FROM LOOKUPS" +
                   " WHERE book_key = '" + book_key + "'")
    lookups = cursor.fetchall()

    # For testing: specify the amount of words you want to export
    if amount >= -1:
        lookups = lookups[:amount]

    for lookup in lookups:
        word = lookup[0][3:]  # remove 'en: ' from word_key
        sentence = lookup[2]  # the sentence in which the word was looked up

        try:
            card = lookup_word(word)
            card["sentence"] = sentence
            card["book_title"] = book_title
            card["author"] = key_to_book[book_key][1]
            cards.append(card)
        except KeyError:
            failed_words.append(word)
        except TypeError:
            missing_words.append(word)

    write_to_export_file(cards)

    # Result
    print("\n####  EXPORT INFO  ####" +
          "\n  Succesfully exported " + str(len(cards)) + " cards"
          "\n  Words not in expected format: " + str(failed_words) +
          "\n  Words not in the dictionary: " + str(missing_words))


def main():
    args = parse_args()

    # Connect to vocabulary database file (vocab.db)
    connection = sqlite3.connect(args.db_path)
    cursor = connection.cursor()

    if args.books:
        print_books(cursor)
    elif args.title is not None:
        export_book_vocab(cursor, args.title, 10)
    else:
        print("Please specify the title of a book using -t TITLE." +
              "\nTo see which books are available for export " +
              "run kanki with the argument -b (or --books)")


if __name__ == "__main__":
    main()
