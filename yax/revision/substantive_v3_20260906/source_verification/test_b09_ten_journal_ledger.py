from check_b09_ten_journal_ledger import EXPECTED, LEDGER, main


def test_declared_journal_set_is_complete_and_qualified() -> None:
    assert LEDGER.is_file()
    assert len(EXPECTED) == 10
    main()
