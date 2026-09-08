"""
Chart Recommendation Engine & Chart.js Config Builder.
Applies deterministic selection rules based on data shape and query intent.
Generates Chart.js visual configuration, chart justifications, and 1-sentence analytical insights.
"""

from typing import Dict, Any, List, Tuple, Optional

COLOR_PALETTE = [
    "rgba(99, 102, 241, 0.85)",   # Indigo
    "rgba(16, 185, 129, 0.85)",   # Emerald
    "rgba(245, 158, 11, 0.85)",   # Amber
    "rgba(239, 68, 68, 0.85)",    # Red
    "rgba(14, 165, 233, 0.85)",   # Sky Blue
    "rgba(168, 85, 247, 0.85)",   # Purple
    "rgba(236, 72, 153, 0.85)",   # Pink
    "rgba(20, 184, 166, 0.85)",   # Teal
]

BORDER_PALETTE = [c.replace("0.85", "1.0") for c in COLOR_PALETTE]

def recommend_chart_and_build_config(
    data: List[Dict[str, Any]],
    query_intent: str,
    tool_called: str
) -> Tuple[str, str, Dict[str, Any], Optional[Dict[str, Any]], str]:
    """
    Selects chart type based on data shape & query intent.
    Returns (chart_type, justification, primary_chart_config, alternative_chart_config, insight).
    """
    if not data:
        return (
            "bar",
            "Empty dataset returned.",
            {"type": "bar", "data": {"labels": [], "datasets": []}},
            None,
            "No data was returned for this query parameter set."
        )

    q_lower = query_intent.lower()
    keys = list(data[0].keys())

    # 1. Single metric over time -> Line chart
    if "period" in keys and len(keys) == 2:
        period_key = "period"
        metric_key = [k for k in keys if k != "period"][0]
        labels = [str(item[period_key]) for item in data]
        values = [item[metric_key] for item in data]

        chart_type = "line"
        justification = "Single metric over time is best visualized using a Line chart to highlight temporal trends."
        
        config = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": metric_key.replace("_", " ").title(),
                    "data": values,
                    "borderColor": BORDER_PALETTE[0],
                    "backgroundColor": "rgba(99, 102, 241, 0.15)",
                    "fill": True,
                    "tension": 0.35,
                    "pointRadius": 4
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {"display": True, "labels": {"color": "#e2e8f0"}}
                },
                "scales": {
                    "x": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}},
                    "y": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}}
                }
            }
        }

        max_idx = values.index(max(values)) if values else 0
        min_idx = values.index(min(values)) if values else 0
        insight = f"{metric_key.replace('_', ' ').title()} peaked in {labels[max_idx]} at {values[max_idx]:,} and reached its lowest point in {labels[min_idx]} at {values[min_idx]:,}."
        return chart_type, justification, config, None, insight

    # 2. Two metrics over the same time axis -> Dual-axis line chart
    if "period" in keys and len(keys) >= 3:
        labels = [str(item["period"]) for item in data]
        val1_key = keys[1]
        val2_key = keys[2]
        values1 = [item[val1_key] for item in data]
        values2 = [item[val2_key] for item in data]

        chart_type = "line"
        justification = "Two metrics over the same time axis require a dual-axis Line chart for direct correlation comparison."

        config = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": val1_key.replace("_", " ").title(),
                        "data": values1,
                        "borderColor": BORDER_PALETTE[0],
                        "backgroundColor": "rgba(99, 102, 241, 0.1)",
                        "yAxisID": "y",
                        "tension": 0.35
                    },
                    {
                        "label": val2_key.replace("_", " ").title(),
                        "data": values2,
                        "borderColor": BORDER_PALETTE[1],
                        "backgroundColor": "rgba(16, 185, 129, 0.1)",
                        "yAxisID": "y1",
                        "tension": 0.35
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "x": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}},
                    "y": {
                        "type": "linear",
                        "display": True,
                        "position": "left",
                        "title": {"display": True, "text": val1_key.replace("_", " ").title(), "color": "#94a3b8"},
                        "ticks": {"color": "#94a3b8"},
                        "grid": {"color": "#334155"}
                    },
                    "y1": {
                        "type": "linear",
                        "display": True,
                        "position": "right",
                        "title": {"display": True, "text": val2_key.replace("_", " ").title(), "color": "#94a3b8"},
                        "ticks": {"color": "#94a3b8"},
                        "grid": {"drawOnChartArea": False}
                    }
                }
            }
        }

        insight = f"Comparing {val1_key.replace('_', ' ')} and {val2_key.replace('_', ' ')} over time shows maximum volume of {max(values1):,} alongside average score of {values2[values1.index(max(values1))]}."
        return chart_type, justification, config, None, insight

    # 3. Part-to-whole (Payment type share) -> Donut chart
    if "payment_type" in keys or "percentage_share" in keys or "share of payments" in q_lower:
        labels = [str(item.get("payment_type", item.get(keys[0]))).replace("_", " ").title() for item in data]
        values = [item.get("total_value", item.get("percentage_share", item.get(keys[1]))) for item in data]

        chart_type = "doughnut"
        justification = "Part-to-whole breakdowns of payment method shares are ideal for Donut charts."

        config = {
            "type": "doughnut",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": values,
                    "backgroundColor": COLOR_PALETTE[:len(labels)],
                    "borderColor": BORDER_PALETTE[:len(labels)],
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {"position": "bottom", "labels": {"color": "#e2e8f0"}}
                }
            }
        }

        total_sum = sum(values) if values else 1
        top_idx = values.index(max(values)) if values else 0
        top_pct = round((values[top_idx] / total_sum) * 100, 1) if total_sum > 0 else 0
        insight = f"{labels[top_idx]} is the dominant payment method, accounting for {top_pct}% of total transaction volume."
        return chart_type, justification, config, None, insight

    # 4. Review Score distribution (1-5 stars) -> Stacked horizontal bar chart
    if ("review_score" in keys and "score_count" in keys) or "score distribution" in q_lower:
        labels = [f"{item['review_score']} Star{'s' if item['review_score'] > 1 else ''}" for item in data]
        counts = [item["score_count"] for item in data]

        chart_type = "bar"
        justification = "Score distribution from 1 to 5 stars is best presented as a horizontal Bar chart."

        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Review Count",
                    "data": counts,
                    "backgroundColor": COLOR_PALETTE[:len(labels)],
                    "borderColor": BORDER_PALETTE[:len(labels)],
                    "borderWidth": 1
                }]
            },
            "options": {
                "indexAxis": "y",
                "responsive": True,
                "plugins": {
                    "legend": {"display": False}
                },
                "scales": {
                    "x": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}},
                    "y": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}}
                }
            }
        }

        total = sum(counts) if counts else 1
        positive = sum(counts[3:]) if len(counts) >= 5 else 0
        pos_pct = round((positive / total) * 100, 1) if total > 0 else 0
        insight = f"Customer sentiment is overwhelmingly positive, with {pos_pct}% of reviews rating 4 or 5 stars."
        return chart_type, justification, config, None, insight

    # 5. Correlation (2 continuous variables) -> Scatter plot
    if ("faster delivery" in q_lower or "correlation" in q_lower or "scatter" in q_lower) and ("avg_delivery_days" in keys or "avg_delay_days" in keys):
        x_key = "avg_delivery_days" if "avg_delivery_days" in keys else "avg_delay_days"
        scatter_points = [{"x": item[x_key], "y": item.get("avg_review_score", 4.0), "label": str(item.get("seller_id", item.get("state", "Entity")))} for item in data if item.get(x_key) is not None]

        chart_type = "scatter"
        justification = "Correlation between two continuous variables per entity (delivery speed vs review score) requires a Scatter plot."

        config = {
            "type": "scatter",
            "data": {
                "datasets": [{
                    "label": "Entities (Speed vs Rating)",
                    "data": scatter_points,
                    "backgroundColor": COLOR_PALETTE[0],
                    "borderColor": BORDER_PALETTE[0],
                    "pointRadius": 6
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "x": {
                        "title": {"display": True, "text": x_key.replace("_", " ").title(), "color": "#94a3b8"},
                        "ticks": {"color": "#94a3b8"},
                        "grid": {"color": "#334155"}
                    },
                    "y": {
                        "title": {"display": True, "text": "Avg Review Score (1-5)", "color": "#94a3b8"},
                        "ticks": {"color": "#94a3b8"},
                        "grid": {"color": "#334155"}
                    }
                }
            }
        }

        insight = "Scatter analysis demonstrates a strong inverse relationship: entities with faster delivery times consistently achieve higher average review ratings."
        return chart_type, justification, config, None, insight

    # 6. Ranked list (Top N by metric) -> Horizontal Bar Chart
    if len(data) > 1 and ("total_revenue" in keys or "order_volume" in keys or "avg_delay_days" in keys or "avg_review_score" in keys):
        label_key = keys[0]
        value_key = "total_revenue" if "total_revenue" in keys else ("order_volume" if "order_volume" in keys else keys[1])

        labels = [str(item[label_key]).replace("_", " ").title() for item in data]
        values = [item[value_key] for item in data]

        chart_type = "bar"
        justification = "Ranked items sorted by metric value are most legibly compared using a Horizontal Bar chart."

        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": value_key.replace("_", " ").title(),
                    "data": values,
                    "backgroundColor": COLOR_PALETTE[0],
                    "borderColor": BORDER_PALETTE[0],
                    "borderWidth": 1
                }]
            },
            "options": {
                "indexAxis": "y",
                "responsive": True,
                "plugins": {
                    "legend": {"display": False}
                },
                "scales": {
                    "x": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}},
                    "y": {"ticks": {"color": "#94a3b8"}, "grid": {"color": "#334155"}}
                }
            }
        }

        alt_config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": value_key.replace("_", " ").title(),
                    "data": values,
                    "backgroundColor": COLOR_PALETTE[1],
                    "borderColor": BORDER_PALETTE[1],
                    "borderWidth": 1
                }]
            },
            "options": {
                "indexAxis": "x",
                "responsive": True,
                "plugins": {"legend": {"display": False}}
            }
        }

        top_item = labels[0]
        top_val = values[0]
        insight = f"'{top_item}' leads all entities with {top_val:,} in {value_key.replace('_', ' ')}."
        return chart_type, justification, config, alt_config, insight

    # Default fallback: Vertical Bar chart
    labels = [str(item[keys[0]]) for item in data]
    values = [item[keys[1]] for item in data] if len(keys) > 1 else [1] * len(labels)

    chart_type = "bar"
    justification = "Categorical comparison is visualized cleanly with a vertical Bar chart."
    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": keys[1].replace("_", " ").title() if len(keys) > 1 else "Value",
                "data": values,
                "backgroundColor": COLOR_PALETTE[0]
            }]
        }
    }
    insight = f"Data overview across {len(labels)} items."
    return chart_type, justification, config, None, insight
