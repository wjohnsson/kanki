from typing import List, Optional


class Card:
    """A vocabulary flashcard."""

    def __init__(self, word, sentence, book_title, author):
        self.word = word
        self.sentence = Card.surround_substring_with_html(sentence, word, 'b')
        self.sentence = sentence
        self.book_title = book_title
        self.author = author

        # Need to be found in dictionary
        self._definitions = None
        self.pronunciation = None

    @property
    def sentence(self):
        return self._sentence

    @property
    def book_title(self):
        return self._book_title

    @property
    def definitions(self):
        return self._definitions

    @sentence.setter
    def sentence(self, sentence: str):
        # Anki expects strings enclosed in double quotes, replace any already existing ones to avoid trouble
        self._sentence = sentence.replace('"', "\'")

    @book_title.setter
    def book_title(self, sentence: str):
        # Anki expects strings enclosed in double quotes, replace any already existing ones to avoid trouble
        self._book_title = sentence.replace('"', "\'")

    @definitions.setter
    def definitions(self, definitions: List[str]):
        self._definitions = '; '.join(definitions)

    def get_csv_encoding(self):
        fields = Card.replace_nones(self.card_fields_in_order())
        # Surround all fields in double quotes, separate with commas
        encoding = '"{0}"'.format('","'.join(fields))
        return encoding

    def card_fields_in_order(self) -> List[str]:
        """Return the card's fields in the order expected by the kanki card type."""
        card_in_anki_order = [self.word, self.pronunciation, self.sentence,
                              self.definitions, self.book_title, self.author]
        return card_in_anki_order

    @staticmethod
    def replace_nones(strings: List[Optional[str]]) -> List[str]:
        """Replace all Nones in a list with empty strings."""
        return list(map(lambda s: '' if s is None else s, strings))

    @staticmethod
    def surround_substring_with_html(string: str, substring: str, html: str):
        open_tag = f'<{html}>'
        close_tag = f'</{html}>'
        return string.replace(substring, open_tag + substring + close_tag)
