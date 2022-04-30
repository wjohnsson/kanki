from merriam_webster import MWDictionary


class Card:
    """A vocabulary flashcard."""
    def __init__(self, word, sentence, book_title, author, ipa=None, definitions=None):
        self.word = word
        self.sentence = surround_substring_with_html(sentence, word, 'b')
        self.book_title = book_title
        self.author = author
        self.ipa = ipa  # pronunciation
        self.definitions = definitions  # definitions

    def set_word_meta_data(self, dictionary: MWDictionary, word: str):
        word_stem, definitions, ipa = dictionary.lookup(word)

        # The dictionary might give another inflection of a word, different from the one used in the example sentence
        self.word = word_stem
        self.definitions = definitions
        self.ipa = ipa


def surround_substring_with_html(string: str, substring: str, html: str):
    open_tag = f'<{html}>'
    close_tag = f'</{html}>'
    return string.replace(substring, open_tag + substring + close_tag)

