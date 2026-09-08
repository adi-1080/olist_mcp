"""
Natural Language Parameter Extraction & Intent Resolution Module.
Resolves dates, locations, categories, limits, and guardrails according to assignment specs.
"""

import re
from typing import Dict, Any, Tuple, List, Optional

STATE_MAPPINGS = {
    "são paulo": "SP",
    "sao paulo": "SP",
    "rio de janeiro": "RJ",
    "minas gerais": "MG",
    "rio grande do sul": "RS",
    "paraná": "PR",
    "parana": "PR",
    "santa catarina": "SC",
    "bahia": "BA",
    "pernambuco": "PE",
    "distrito federal": "DF",
    "ceará": "CE",
    "ceara": "CE",
}

CATEGORY_TRANSLATIONS = {
    "electronics": "electronics",
    "bed bath table": "bed bath table",
    "health beauty": "health beauty",
    "sports leisure": "sports leisure",
    "computers": "computers accessories",
    "furniture": "furniture decor",
    "housewares": "housewares",
    "watches": "watches gifts",
    "telephony": "telephony",
    "automotive": "auto",
}

# Topics the Olist e-commerce dataset cannot answer.
OUT_OF_BOUNDS_PATTERNS = [
    r"\bstock prices?\b",
    r"\bshare price\b",
    r"\bnasdaq\b",
    r"\bcrypto(currency)?\b",
    r"\bbitcoin\b",
    r"\bweather\b",
    r"\btemperature\b",
    r"\bforecast\b",
    r"\bdemographics?\b",
    r"\bsalary\b",
    r"\bemployee(s)?\b",
    r"\btwitter\b",
    r"\binstagram\b",
    r"\bfacebook\b",
    r"marketing ad spend",
    r"\bnews\b",
    r"\bheadline(s)?\b",
    r"\bwar(s)?\b",
    r"\bmilitary\b",
    r"\bpolitics?\b",
    r"\belection(s)?\b",
    r"\bpresident\b",
    r"\bfootball\b",
    r"\bsoccer\b",
    r"\bnba\b",
    r"\bmovie(s)?\b",
    r"\bcelebrity\b",
    r"\bcovid\b",
    r"\bpandemic\b",
    r"\brecipe(s)?\b",
    r"\bmedical\b",
    r"\bdiagnosis\b",
]

# Signals that the question is about this dataset's analytics surface.
IN_DOMAIN_PATTERNS = [
    r"\border(s)?\b",
    r"\brevenue\b",
    r"\bsales?\b",
    r"\bproduct(s)?\b",
    r"\bcategor(y|ies)\b",
    r"\bseller(s)?\b",
    r"\breview(s)?\b",
    r"\bpayment(s)?\b",
    r"credit card",
    r"\bboleto\b",
    r"\bvoucher\b",
    r"\bdebit\b",
    r"\bdeliver(y|ed|ies)\b",
    r"\bfreight\b",
    r"\bshipping\b",
    r"\bcustomer(s)?\b",
    r"\btrend(s)?\b",
    r"\bmonthly\b",
    r"\bweekly\b",
    r"\bvolume\b",
    r"\brating(s)?\b",
    r"\bscore(s)?\b",
    r"\binstallment(s)?\b",
    r"\bdelay\b",
    r"on[- ]?time",
    r"são paulo",
    r"sao paulo",
    r"\belectronics\b",
    r"\be-?commerce\b",
    r"\bolist\b",
    r"\bchart\b",
    r"\bperformance\b",
    r"\btop\s+\d+\b",
    r"\bworst rated\b",
]


def _matches_any(query: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, query) for pattern in patterns)


def check_out_of_bounds(query: str) -> bool:
    """
    True when the query is not answerable from the Olist e-commerce tables.

    Rejects explicit off-domain topics (news, war, stocks, weather, ...) and
    questions that have no analytics/dataset vocabulary at all. Unmatched
    questions must not fall through to a default product chart.
    """
    q_lower = query.lower().strip()
    if not q_lower:
        return True
    if _matches_any(q_lower, OUT_OF_BOUNDS_PATTERNS):
        return True
    if not _matches_any(q_lower, IN_DOMAIN_PATTERNS):
        return True
    return False

def extract_parameters(query: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Extracts date range, state, category, limit, and sort parameters from natural language query.
    Returns (extracted_params_dict, assumptions_list).
    """
    q_lower = query.lower()
    params: Dict[str, Any] = {}
    assumptions: List[str] = []

    # 1. Date Range Extraction
    if "last year" in q_lower:
        params["start_date"] = "2017-01-01"
        params["end_date"] = "2017-12-31"
        assumptions.append("Resolved 'last year' to dataset active year 2017 (2017-01-01 to 2017-12-31).")
    elif "first half of 2017" in q_lower or "h1 2017" in q_lower:
        params["start_date"] = "2017-01-01"
        params["end_date"] = "2017-06-30"
        assumptions.append("Resolved 'first half of 2017' to 2017-01-01 to 2017-06-30.")
    elif "2017" in q_lower:
        params["start_date"] = "2017-01-01"
        params["end_date"] = "2017-12-31"
        assumptions.append("Filtered date range for year 2017.")
    elif "2018" in q_lower:
        params["start_date"] = "2018-01-01"
        params["end_date"] = "2018-12-31"
        assumptions.append("Filtered date range for year 2018.")
    elif "2016" in q_lower:
        params["start_date"] = "2016-01-01"
        params["end_date"] = "2016-12-31"
        assumptions.append("Filtered date range for year 2016.")
    else:
        assumptions.append("No specific date range provided; defaulting to full dataset (2016-2018).")

    # 2. State Extraction
    state_found = None
    for city_or_state, abbr in STATE_MAPPINGS.items():
        if city_or_state in q_lower:
            state_found = abbr
            break
    if not state_found:
        # Check direct 2-letter uppercase state codes
        state_match = re.search(r'\b(sp|rj|mg|rs|pr|sc|ba|pe|df|ce)\b', q_lower)
        if state_match:
            state_found = state_match.group(1).upper()

    if state_found:
        params["state"] = state_found
        assumptions.append(f"Resolved geographic region to Brazilian state '{state_found}'.")

    # 3. Limit & Sort Extraction
    limit_match = re.search(r'\btop\s+(\d+)\b', q_lower)
    if limit_match:
        params["limit"] = int(limit_match.group(1))
        params["sort_by"] = "revenue"
    elif "worst rated" in q_lower or "lowest score" in q_lower:
        params["sort_by"] = "review_score"
        params["order"] = "asc"
        params["limit"] = 10
    elif "most revenue" in q_lower or "top categories" in q_lower:
        params["sort_by"] = "revenue"
        params["limit"] = 10
    elif "top sellers" in q_lower:
        params["sort_by"] = "revenue"
        params["limit"] = 10

    # 4. Category Extraction
    for cat_name in ["electronics", "computers", "telephony", "furniture", "housewares", "watches", "health beauty", "bed bath table"]:
        if cat_name in q_lower:
            params["category"] = cat_name
            assumptions.append(f"Mapped category keyword '{cat_name}' to standard English category taxonomy.")
            break

    return params, assumptions
