"""
Unit Tests for Natural Language Parameter Extraction & Intent Resolution.
"""

from src.agent.extractor import extract_parameters, check_out_of_bounds

def test_extract_date_ranges():
    params, assumptions = extract_parameters("Show monthly revenue trend for last year")
    assert params.get("start_date") == "2017-01-01"
    assert params.get("end_date") == "2017-12-31"

    params, assumptions = extract_parameters("Show orders for first half of 2017")
    assert params.get("start_date") == "2017-01-01"
    assert params.get("end_date") == "2017-06-30"

def test_extract_state_and_limit():
    params, assumptions = extract_parameters("Top 10 sellers by revenue in São Paulo")
    assert params.get("state") == "SP"
    assert params.get("limit") == 10

def test_check_out_of_bounds():
    assert check_out_of_bounds("What is the current stock price of Apple?") is True
    assert check_out_of_bounds("Show monthly revenue trend for 2017") is False
