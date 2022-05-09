from typing import List, Optional

from .merriam_webster import MWDictionary


class Card:
    """A vocabulary flashcard."""

    def __init__(self, word, sentence, book_title, author, pronunciation=None, definitions=None):
        self.word = word
        self.sentence = surround_substring_with_html(sentence, word, 'b')
        # Anki expects strings enclosed in double quotes, replace them to avoid trouble
        self.sentence = self.sentence.replace('"', '\'')
        self.book_title = book_title.replace('"', '\'')
        self.author = author
        self.pronunciation = pronunciation
        self.definitions = definitions

    def set_word_meta_data(self, dictionary: MWDictionary, word: str):
        word_stem, definitions, ipa = dictionary.lookup(word)

        # The dictionary might give another inflection of a word, different from the one used in the example sentence
        self.word = word_stem
        self.definitions = definitions
        if self.definitions:
            assert type(self.definitions) == list, "definitions should be a list"
            self.definitions = '; '.join(self.definitions)
        self.pronunciation = ipa

    def get_csv_encoding(self):
        encoding = Card.replace_nones(self.card_fields_in_order())

        # Anki accepts plaintext files with fields separated by commas.
        # Surround all fields in quotes and write in same order as the kanki card type.
        card_data_str = '"{0}"\n'.format('","'.join(encoding))
        return card_data_str

    def card_fields_in_order(self) -> List[str]:
        """Return the card's fields in the order expected by the kanki card type."""
        card_in_anki_order = [self.word, self.pronunciation, self.sentence,
                              self.definitions, self.book_title, self.author]
        return card_in_anki_order

    @staticmethod
    def replace_nones(strings: List[Optional[str]]) -> List[str]:
        """Replace all Nones in a list with empty strings."""
        return list(map(lambda s: '' if s is None else s, strings))


def surround_substring_with_html(string: str, substring: str, html: str):
    open_tag = f'<{html}>'
    close_tag = f'</{html}>'
    return string.replace(substring, open_tag + substring + close_tag)
