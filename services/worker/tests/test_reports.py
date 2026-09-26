import pytest
from hypothesis import given
from hypothesis import strategies as st
from toads_worker.jobs.sync import new_report_codes
from toads_worker.reports import InvalidReportCodeError, parse_report_input, validate_report_code

CODE = "aBcD1234eFgH5678"


@pytest.mark.parametrize(
    "value",
    [
        CODE,
        f"https://fresh.warcraftlogs.com/reports/{CODE}",
        f"https://classic.warcraftlogs.com/reports/{CODE}#fight=3",
        f"www.warcraftlogs.com/reports/{CODE}/",
    ],
)
def test_accepts_codes_and_urls(value: str) -> None:
    assert parse_report_input(value) == CODE


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        "short",
        f"{CODE}x",
        'abc") { __schema',
        f"https://evil.example/reports/{CODE}",
        f"https://fresh.warcraftlogs.com/character/{CODE}",
    ],
)
def test_rejects_bad_input(value: str) -> None:
    with pytest.raises(InvalidReportCodeError):
        parse_report_input(value)


@pytest.mark.security
@given(st.text())
def test_only_alnum16_ever_passes(value: str) -> None:
    try:
        code = validate_report_code(value)
    except InvalidReportCodeError:
        return
    assert len(code) == 16 and code.isascii() and code.isalnum()


def test_new_report_codes_diff() -> None:
    assert new_report_codes(["a", "b", "b", "c"], ["a"]) == ["b", "c"]
