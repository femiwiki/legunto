import legunto


def test_to_filename():
    assert legunto.to_filename('Module:foo') == \
        'foo'

    assert legunto.to_filename('Module:foo bar') == \
        'foo bar'

    assert legunto.to_filename('Module:foo/bar') == \
        'foo-bar'

    assert legunto.to_filename('모듈:foo/bar') == \
        'foo-bar'
