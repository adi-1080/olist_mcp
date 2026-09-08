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
    "electronics": "eletronicos",
    "bed bath table": "cama_mesa_banho",
    "health beauty": "beleza_saude",
    "sports leisure": "esporte_lazer",
    "computers": "informatica_acessorios",
    "furniture": "moveis_decoracao",
    "housewares": "utilidades_domesticas",
    "watches": "relogios_presentes",
    "telephony": "telefonia",
    "automotive": "automotivo",
}

OUT_OF_BOUNDS_KEYWORDS = [
    "stock price", "stock", "shares", "nasdaq", "crypto", "bitcoin",
    "weather", "temperature", "demographics", "salary", "employee",
    "twitter", "instagram", "facebook", "marketing ad spend"
]

def check_out_of_bounds(query: str) -> bool:
    """Checks if query requests information not present in the Olist dataset."""
    q_lower = query.lower()
    for kw in OUT_OF_BOUNDS_KEYWORDS:
        if kw in q_lower:
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
