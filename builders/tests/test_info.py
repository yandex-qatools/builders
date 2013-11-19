def test_info_exists():
    '''
        Tests that info exists
    '''
    import builders.info as info

    assert info.__version__
    assert info.__package_name__
