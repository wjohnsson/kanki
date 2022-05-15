from kanki.card import Card


def test_replace_nones():
    assert Card.replace_nones([]) == []
    assert Card.replace_nones([None]) == ['']
    assert Card.replace_nones([None, None]) == ['', '']
    assert Card.replace_nones(['a', None, 'b']) == ['a', '', 'b']


def test_get_csv_encoding():
    card = Card('word', 'sentence', 'book_title', 'author')
    assert card.get_csv_encoding() == '"word","","sentence","","book_title","author"'
    card.sentence = '"trouble"'
    assert card.get_csv_encoding() == '"word","","\'trouble\'","","book_title","author"'
    card.book_title = '"also_trouble"'
    assert card.get_csv_encoding() == '"word","","\'trouble\'","","\'also_trouble\'","author"'
