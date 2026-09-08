"""
Significant Change Detection Engine.
Compares refreshed query results against baseline metrics stored at pin creation.
Flags significant metric shifts (> 5% change or top entity rank change).
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

SIGNIFICANT_CHANGE_THRESHOLD_PCT = 5.0  # 5% threshold

def detect_significant_changes(
    old_data: List[Dict[str, Any]],
    new_data: List[Dict[str, Any]]
) -> Tuple[bool, str, List[str]]:
    """
    Compares baseline old_data with new_data.
    Returns (has_significant_change: bool, summary: str, details_list: List[str]).
    """
    if not old_data and not new_data:
        return False, "No data available in baseline or current refresh.", []

    if not old_data and new_data:
        return True, "New dataset items detected since pin creation.", ["Baseline was empty, current has data."]

    if old_data and not new_data:
        return True, "Dataset items disappeared upon refresh.", ["Data no longer available for this query."]

    diff_details = []
    has_change = False

    # 1. Top Entity Rank Shift Check
    first_key = list(old_data[0].keys())[0]
    old_top_entity = old_data[0].get(first_key)
    new_top_entity = new_data[0].get(first_key)

    if old_top_entity != new_top_entity:
        has_change = True
        diff_details.append(f"Top entity shifted from '{old_top_entity}' to '{new_top_entity}'.")

    # 2. Metric Aggregation Shift Check
    metric_keys = [k for k in old_data[0].keys() if isinstance(old_data[0][k], (int, float))]
    
    for key in metric_keys[:2]:  # Check top 2 numeric metrics
        old_sum = sum(item.get(key, 0) or 0 for item in old_data)
        new_sum = sum(item.get(key, 0) or 0 for item in new_data)

        if old_sum != 0:
            pct_diff = ((new_sum - old_sum) / abs(old_sum)) * 100.0
            sign = "+" if pct_diff > 0 else ""
            
            if abs(pct_diff) >= SIGNIFICANT_CHANGE_THRESHOLD_PCT:
                has_change = True
                diff_details.append(f"{key.replace('_', ' ').title()} shifted by {sign}{pct_diff:.1f}% (from {old_sum:,.2f} to {new_sum:,.2f}).")
            else:
                diff_details.append(f"{key.replace('_', ' ').title()} changed slightly by {sign}{pct_diff:.1f}% (below 5% threshold).")

    if has_change:
        summary = "Significant change detected! " + "; ".join(diff_details)
    else:
        summary = "No significant metric change detected since last pin."

    return has_change, summary, diff_details
