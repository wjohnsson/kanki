from typing import List, Optional

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

    def get_csv_encoding(self):
        definitions = self.definitions
        if self.definitions:
            # A word may have multiple definitions, join them with a semicolon.
            definitions = '; '.join(self.definitions)
        # Collect all card data in a list and make sure all double quotes are
        # single quotes in the file so that it is readable by Anki
        encoding = [self.word,
                    self.ipa,
                    self.sentence.replace('"', '\''),
                    definitions,
                    self.book_title.replace('"', '\''),
                    self.author]
        encoding = Card.replace_nones(encoding)
        # Anki accepts plaintext files with fields separated by commas.
        # Surround all fields in quotes and write in same order as the kanki card type.
        card_data_str = '"{0}"\n'.format('","'.join(encoding))
        return card_data_str

    @staticmethod
    def replace_nones(strings: List[Optional[str]]) -> List[str]:
        """Replace all Nones in a list with empty strings."""
        return list(map(lambda s: '' if s is None else s, strings))


def surround_substring_with_html(string: str, substring: str, html: str):
    open_tag = f'<{html}>'
    close_tag = f'</{html}>'
    return string.replace(substring, open_tag + substring + close_tag)
