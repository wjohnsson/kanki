import sqlite3

import pytest


@pytest.fixture
def setup_database() -> sqlite3.Cursor:
    """Return a reusable in-memory database with test data"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    insert_books(cursor)
    insert_lookups(cursor)

    return cursor


def insert_lookups(cursor):
    cursor.execute('CREATE TABLE LOOKUPS '
                   '(id text UNIQUE, word_key text, book_key text,'
                   'dict_key text, pos text, usage text, timestamp integer)')
    sample_lookups = [
        ('ID1:pos:1', 'en:hello', 'ID1', 'dict1', 'pos:1', 'hello sir', 1),
        ('ID1:pos:2', 'en:foo', 'ID1', 'dict1', 'pos:2', 'foo sentence', 2),
        ('ID1:pos:3', 'en:bar', 'ID1', 'dict1', 'pos:3', 'bar sentence', 3),
        ('ID2:pos:1', 'en:physics', 'ID2', 'dict1', 'pos:1', 'Physics are astounding!', 4)
    ]
    cursor.executemany('INSERT INTO LOOKUPS VALUES (?, ?, ?, ?, ?, ?, ?)', sample_lookups)


def insert_books(cursor):
    cursor.execute('CREATE TABLE BOOK_INFO '
                   '(id text UNIQUE, asin text, guid text, lang text, title text, authors text)')
    sample_books = [
        ('ID1', 'asin', 'ID1', 'en', 'The Stand', 'King, Stephen'),
        ('ID2', 'asin', 'ID2', 'en',
         '"Surely You\'re Joking, Mr. Feynman!": Adventures of a Curious Character', 'Feynman, Richard P.'),
        ('ID3', 'asin', 'ID3', 'en', 'Dune Messiah', 'Herbert, Frank'),
        ('ID4', 'asin', 'ID4', 'en', 'Dune Messiah', 'Herbert, Frank')
    ]
    cursor.executemany('INSERT INTO BOOK_INFO VALUES (?, ?, ?, ?, ?, ?)', sample_books)
