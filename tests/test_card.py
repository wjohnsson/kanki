from kanki import Card


def test_replace_nones():
    assert Card.replace_nones([]) == []
    assert Card.replace_nones([None]) == ['']
    assert Card.replace_nones([None, None]) == ['', '']
    assert Card.replace_nones(['a', None, 'b']) == ['a', '', 'b']
