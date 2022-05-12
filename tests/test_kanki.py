import pytest
import pytest_mock

from kanki.exceptions import MissingBookError
from kanki.run import Kanki
from merriam_webster import MWDictionary


def test_remove_books_until_safe(mocker: pytest_mock.MockerFixture):
    # books = {name: number of lookups}
    books = {'BOOK_A': 1,
             'BOOK_B': MWDictionary.max_queries // 2,
             'BOOK_C': MWDictionary.max_queries // 2}
    kanki = Kanki(dictionary=MWDictionary(api_key='dummy'), book_titles=list(books.keys()))

    def mock_count_lookups(self, book_title):
        return books.get(book_title)

    mocker.patch.object(
        Kanki,
        'count_lookups',
        mock_count_lookups
    )

    actual_1 = kanki.remove_books_until_safe()
    expected_1 = ['BOOK_A', 'BOOK_B']

    actual_2 = kanki.remove_books_until_safe()
    expected_2 = expected_1

    assert expected_1 == actual_1, 'wrong book remaining'
    assert expected_2 == actual_2, 'the book should stay in the list'


def test_remove_unsafe_book(mocker: pytest_mock.MockerFixture):
    kanki = Kanki(dictionary=MWDictionary('dummy'), book_titles=['B'])

    def mock_count_lookups(self, book_title):
        unsafe_book_lookups = MWDictionary.max_queries + 1
        return unsafe_book_lookups

    mocker.patch.object(Kanki, 'count_lookups', mock_count_lookups)
    with pytest.raises(SystemExit):
        kanki.remove_books_until_safe()


def test_count_lookups(setup_database):
    kanki = Kanki(db_cursor=setup_database)
    assert 0 == kanki.count_lookups('"Surely You\'re Joking, Mr. Feynman!": Adventures of a Curious Character')
    assert 3 == kanki.count_lookups('The Stand')
    with pytest.raises(MissingBookError):
        kanki.count_lookups('Unknown book')


def test_get_book_keys(setup_database):
    kanki = Kanki(db_cursor=setup_database)
    # TODO: Add tests where no exception is raised
    with pytest.raises(MissingBookError):
        kanki.count_lookups('')


def test_get_sql_placeholders():
    assert Kanki.get_sql_placeholders(1) == '?'
    assert Kanki.get_sql_placeholders(5) == '?,?,?,?,?'
    try:
        Kanki.get_sql_placeholders(999)
    except ValueError:
        pytest.fail('Unexpected exception, 999 placeholders should be fine')


@pytest.mark.parametrize('amount', [0, -1, -1000, 1000])
def test_get_invalid_sql_placeholders(amount: int):
    with pytest.raises(ValueError):
        Kanki.get_sql_placeholders(amount)


def test_flatten():
    assert Kanki.flatten([]) == []
    assert Kanki.flatten([[]]) == []
    assert Kanki.flatten([[], [], []]) == []
    assert Kanki.flatten([[], [], [1]]) == [1]
    assert Kanki.flatten([[1], [2]]) == [1, 2]
    assert Kanki.flatten([[1, 2], [3]]) == [1, 2, 3]
