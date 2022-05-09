import pytest
import pytest_mock

from kanki.kanki import Kanki
from merriam_webster import MWDictionary


def test_remove_books_until_safe(mocker: pytest_mock.MockerFixture):
    kanki = Kanki()
    kanki.dictionary = MWDictionary('dummy_api_key')
    books = {'BOOK_A': 1, 'BOOK_B': MWDictionary.max_queries // 2, 'BOOK_C': MWDictionary.max_queries // 2}
    book_titles = list(books.keys())

    def mock_count_lookups(self, book_title: str):
        return books.get(book_title)

    mocker.patch.object(
        Kanki,
        'count_lookups',
        mock_count_lookups
    )

    actual_1 = kanki.remove_books_until_safe(book_titles)
    expected_1 = ['BOOK_A', 'BOOK_B']
    actual_2 = kanki.remove_books_until_safe(book_titles)
    expected_2 = expected_1

    assert expected_1 == actual_1, 'wrong book remaining'
    assert expected_2 == actual_2, 'the book should stay in the list'


def test_remove_unsafe_book(mocker: pytest_mock.MockerFixture):
    kanki = Kanki()
    kanki.dictionary = MWDictionary('dummy_api_key')

    def mock_count_lookups(self, book_title: str):
        unsafe_book_lookups = MWDictionary.max_queries + 1
        return unsafe_book_lookups

    mocker.patch.object(Kanki, 'count_lookups', mock_count_lookups)
    with pytest.raises(SystemExit):
        kanki.remove_books_until_safe(['A'])


def test_flatten():
    assert Kanki.flatten([]) == []
    assert Kanki.flatten([[]]) == []
    assert Kanki.flatten([[], [], []]) == []
    assert Kanki.flatten([[], [], [1]]) == [1]
    assert Kanki.flatten([[1], [2]]) == [1, 2]
    assert Kanki.flatten([[1, 2], [3]]) == [1, 2, 3]


def test_replace_nones():
    assert Kanki.replace_nones([]) == []
    assert Kanki.replace_nones([None]) == ['']
    assert Kanki.replace_nones([None, None]) == ['', '']
    assert Kanki.replace_nones(['a', None, 'b']) == ['a', '', 'b']
