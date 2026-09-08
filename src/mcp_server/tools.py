"""
Implementation of domain-specific SQL analytics tools over Olist SQLite Database.
Includes structured error handling, safety checks, and automatic Portuguese-to-English category translation joins.
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.database.loader import get_db_connection

logger = logging.getLogger(__name__)

def _format_error(code: str, message: str) -> Dict[str, Any]:
    """Returns standardized JSON error dictionary."""
    return {
        "status": "error",
        "error_code": code,
        "message": message
    }

def query_order_trends(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    frequency: str = "monthly"
) -> Dict[str, Any]:
    """
    Queries order volume, revenue, and delivery performance over time.
    """
    try:
        conn = get_db_connection()
        date_format = "%Y-%m" if frequency == "monthly" else "%Y-%W"

        where_clauses = ["o.order_status != 'canceled'"]
        params = []
        if start_date:
            where_clauses.append("o.order_purchase_timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            where_clauses.append("o.order_purchase_timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where_sql = " WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT 
                strftime('{date_format}', o.order_purchase_timestamp) AS period,
                COUNT(DISTINCT o.order_id) AS order_volume,
                COALESCE(SUM(p.payment_value), 0.0) AS total_revenue,
                ROUND(COALESCE(AVG(p.payment_value), 0.0), 2) AS avg_order_value,
                ROUND(AVG(
                    CASE 
                        WHEN o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL
                        THEN (julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date))
                        ELSE NULL 
                    END
                ), 2) AS avg_delay_days
            FROM olist_orders o
            LEFT JOIN olist_order_payments p ON o.order_id = p.order_id
            {where_sql}
            GROUP BY period
            HAVING period IS NOT NULL
            ORDER BY period ASC
        """

        df = conn.execute(query, params).fetchall()
        columns = ["period", "order_volume", "total_revenue", "avg_order_value", "avg_delay_days"]
        results = [dict(zip(columns, row)) for row in df]

        conn.close()

        if not results:
            return {
                "status": "empty",
                "message": "No order trend data found for the given parameters.",
                "data": []
            }

        return {
            "status": "success",
            "frequency": frequency,
            "data": results,
            "total_records": len(results)
        }
    except Exception as e:
        logger.error(f"Error in query_order_trends: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_product_performance(
    category: Optional[str] = None,
    limit: int = 10,
    sort_by: str = "revenue"
) -> Dict[str, Any]:
    """
    Queries revenue, order volume, review scores, and freight cost by product category.
    ALWAYS joins product_category_name_translation table.
    """
    try:
        conn = get_db_connection()
        where_clauses = ["t.product_category_name_english IS NOT NULL"]
        params = []

        if category:
            where_clauses.append("LOWER(t.product_category_name_english) LIKE ?")
            params.append(f"%{category.lower().replace('_', ' ')}%")

        where_sql = " WHERE " + " AND ".join(where_clauses)
        order_col = "total_revenue" if sort_by == "revenue" else ("avg_review_score" if sort_by == "review_score" else "order_volume")

        query = f"""
            SELECT 
                t.product_category_name_english AS category_english,
                COUNT(DISTINCT i.order_id) AS order_volume,
                ROUND(SUM(i.price), 2) AS total_revenue,
                ROUND(AVG(i.price), 2) AS avg_price,
                ROUND(AVG(i.freight_value), 2) AS avg_freight,
                ROUND(AVG(r.review_score), 2) AS avg_review_score
            FROM olist_products p
            JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
            JOIN olist_order_items i ON p.product_id = i.product_id
            LEFT JOIN olist_order_reviews r ON i.order_id = r.order_id
            {where_sql}
            GROUP BY category_english
            ORDER BY {order_col} DESC
            LIMIT ?
        """
        params.append(limit)

        df = conn.execute(query, params).fetchall()
        columns = ["category_english", "order_volume", "total_revenue", "avg_price", "avg_freight", "avg_review_score"]
        results = [dict(zip(columns, row)) for row in df]
        conn.close()

        if not results:
            return {
                "status": "empty",
                "message": f"No product performance data found for category filter '{category}'.",
                "data": []
            }

        return {
            "status": "success",
            "data": results,
            "total_records": len(results)
        }
    except Exception as e:
        logger.error(f"Error in query_product_performance: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_seller_performance(
    state: Optional[str] = None,
    limit: int = 10,
    sort_by: str = "revenue"
) -> Dict[str, Any]:
    """
    Queries seller revenue, review ratings, delivery speed, and location.
    """
    try:
        conn = get_db_connection()
        where_clauses = ["s.seller_id IS NOT NULL"]
        params = []

        if state:
            where_clauses.append("UPPER(s.seller_state) = ?")
            params.append(state.upper())

        where_sql = " WHERE " + " AND ".join(where_clauses)
        order_col = "total_revenue" if sort_by == "revenue" else ("avg_review_score" if sort_by == "review_score" else "avg_delivery_days")
        order_dir = "ASC" if sort_by == "delivery_speed" else "DESC"

        query = f"""
            SELECT 
                s.seller_id,
                s.seller_state,
                s.seller_city,
                COUNT(DISTINCT i.order_id) AS total_orders,
                ROUND(SUM(i.price), 2) AS total_revenue,
                ROUND(AVG(r.review_score), 2) AS avg_review_score,
                ROUND(AVG(
                    CASE 
                        WHEN o.order_delivered_customer_date IS NOT NULL AND o.order_purchase_timestamp IS NOT NULL
                        THEN (julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp))
                        ELSE NULL 
                    END
                ), 2) AS avg_delivery_days
            FROM olist_sellers s
            JOIN olist_order_items i ON s.seller_id = i.seller_id
            JOIN olist_orders o ON i.order_id = o.order_id
            LEFT JOIN olist_order_reviews r ON i.order_id = r.order_id
            {where_sql}
            GROUP BY s.seller_id
            ORDER BY {order_col} {order_dir}
            LIMIT ?
        """
        params.append(limit)

        df = conn.execute(query, params).fetchall()
        columns = ["seller_id", "seller_state", "seller_city", "total_orders", "total_revenue", "avg_review_score", "avg_delivery_days"]
        results = [dict(zip(columns, row)) for row in df]
        conn.close()

        if not results:
            return {
                "status": "empty",
                "message": f"No seller performance data found for state '{state}'.",
                "data": []
            }

        return {
            "status": "success",
            "data": results,
            "total_records": len(results)
        }
    except Exception as e:
        logger.error(f"Error in query_seller_performance: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_customer_reviews(
    category: Optional[str] = None,
    state: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries score distributions (1-5 stars), response times, and review statistics.
    """
    try:
        conn = get_db_connection()
        where_clauses = ["r.review_score IS NOT NULL"]
        params = []

        if category:
            where_clauses.append("LOWER(t.product_category_name_english) LIKE ?")
            params.append(f"%{category.lower().replace('_', ' ')}%")

        if state:
            where_clauses.append("UPPER(c.customer_state) = ?")
            params.append(state.upper())

        if start_date:
            where_clauses.append("o.order_purchase_timestamp >= ?")
            params.append(f"{start_date} 00:00:00")

        if end_date:
            where_clauses.append("o.order_purchase_timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where_sql = " WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT 
                r.review_score,
                COUNT(r.review_id) AS score_count,
                ROUND(AVG(
                    CASE 
                        WHEN r.review_answer_timestamp IS NOT NULL AND r.review_creation_date IS NOT NULL
                        THEN (julianday(r.review_answer_timestamp) - julianday(r.review_creation_date)) * 24.0
                        ELSE NULL 
                    END
                ), 2) AS avg_response_hours
            FROM olist_order_reviews r
            JOIN olist_orders o ON r.order_id = o.order_id
            LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
            LEFT JOIN olist_order_items i ON o.order_id = i.order_id
            LEFT JOIN olist_products p ON i.product_id = p.product_id
            LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
            {where_sql}
            GROUP BY r.review_score
            ORDER BY r.review_score ASC
        """

        df = conn.execute(query, params).fetchall()
        columns = ["review_score", "score_count", "avg_response_hours"]
        dist = [dict(zip(columns, row)) for row in df]

        conn.close()

        total_reviews = sum(item["score_count"] for item in dist)
        avg_score = round(sum(item["review_score"] * item["score_count"] for item in dist) / total_reviews, 2) if total_reviews > 0 else 0

        return {
            "status": "success",
            "summary": {
                "total_reviews": total_reviews,
                "average_score": avg_score,
                "category_filter": category,
                "state_filter": state
            },
            "data": dist
        }
    except Exception as e:
        logger.error(f"Error in query_customer_reviews: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_payment_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries payment type breakdown (credit card, boleto, voucher, debit card), installments, and values.
    """
    try:
        conn = get_db_connection()
        where_clauses = ["p.payment_type IS NOT NULL"]
        params = []

        if start_date:
            where_clauses.append("o.order_purchase_timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            where_clauses.append("o.order_purchase_timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where_sql = " WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT 
                p.payment_type,
                COUNT(p.order_id) AS transaction_count,
                ROUND(SUM(p.payment_value), 2) AS total_value,
                ROUND(AVG(p.payment_installments), 2) AS avg_installments
            FROM olist_order_payments p
            JOIN olist_orders o ON p.order_id = o.order_id
            {where_sql}
            GROUP BY p.payment_type
            ORDER BY total_value DESC
        """

        df = conn.execute(query, params).fetchall()
        columns = ["payment_type", "transaction_count", "total_value", "avg_installments"]
        results = [dict(zip(columns, row)) for row in df]
        conn.close()

        total_value_sum = sum(r["total_value"] for r in results)
        for r in results:
            r["percentage_share"] = round((r["total_value"] / total_value_sum * 100.0), 2) if total_value_sum > 0 else 0.0

        return {
            "status": "success",
            "data": results,
            "total_value_all_types": round(total_value_sum, 2)
        }
    except Exception as e:
        logger.error(f"Error in query_payment_breakdown: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_delivery_performance(
    state: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries delivery performance: estimated vs actual delivery dates, delay days, and on-time rates by customer state.
    """
    try:
        conn = get_db_connection()
        where_clauses = [
            "o.order_status = 'delivered'",
            "o.order_delivered_customer_date IS NOT NULL",
            "o.order_estimated_delivery_date IS NOT NULL"
        ]
        params = []

        if state:
            where_clauses.append("UPPER(c.customer_state) = ?")
            params.append(state.upper())

        if start_date:
            where_clauses.append("o.order_purchase_timestamp >= ?")
            params.append(f"{start_date} 00:00:00")

        if end_date:
            where_clauses.append("o.order_purchase_timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where_sql = " WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT 
                c.customer_state AS state,
                COUNT(o.order_id) AS total_delivered_orders,
                ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 2) AS avg_delivery_days,
                ROUND(AVG(julianday(o.order_estimated_delivery_date) - julianday(o.order_purchase_timestamp)), 2) AS avg_estimated_days,
                ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)), 2) AS avg_delay_days,
                ROUND(
                    (SUM(CASE WHEN julianday(o.order_delivered_customer_date) <= julianday(o.order_estimated_delivery_date) THEN 1 ELSE 0 END) * 100.0) / COUNT(o.order_id), 
                    2
                ) AS on_time_rate_pct
            FROM olist_orders o
            JOIN olist_customers c ON o.customer_id = c.customer_id
            {where_sql}
            GROUP BY c.customer_state
            ORDER BY avg_delay_days DESC
        """

        df = conn.execute(query, params).fetchall()
        columns = ["state", "total_delivered_orders", "avg_delivery_days", "avg_estimated_days", "avg_delay_days", "on_time_rate_pct"]
        results = [dict(zip(columns, row)) for row in df]
        conn.close()

        if not results:
            return {
                "status": "empty",
                "message": f"No delivery performance data found for state filter '{state}'.",
                "data": []
            }

        return {
            "status": "success",
            "data": results,
            "total_records": len(results)
        }
    except Exception as e:
        logger.error(f"Error in query_delivery_performance: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))


def query_multi_tool_join(
    query_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handles joint multi-domain queries requiring data combined across products, sellers, reviews, and delivery.
    """
    try:
        conn = get_db_connection()

        if query_type == "top_categories_review_comparison":
            # Compare review scores across top 5 categories by order volume
            sql = """
                WITH top_cats AS (
                    SELECT 
                        t.product_category_name_english AS cat,
                        COUNT(DISTINCT i.order_id) AS order_vol
                    FROM olist_order_items i
                    JOIN olist_products p ON i.product_id = p.product_id
                    JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
                    GROUP BY cat
                    ORDER BY order_vol DESC
                    LIMIT 5
                )
                SELECT 
                    tc.cat AS category,
                    tc.order_vol AS order_volume,
                    ROUND(AVG(r.review_score), 2) AS avg_review_score
                FROM top_cats tc
                JOIN product_category_name_translation t ON tc.cat = t.product_category_name_english
                JOIN olist_products p ON t.product_category_name = p.product_category_name
                JOIN olist_order_items i ON p.product_id = i.product_id
                LEFT JOIN olist_order_reviews r ON i.order_id = r.order_id
                GROUP BY tc.cat
                ORDER BY tc.order_vol DESC
            """
            rows = conn.execute(sql).fetchall()
            cols = ["category", "order_volume", "avg_review_score"]
            data = [dict(zip(cols, r)) for r in rows]

        elif query_type == "monthly_orders_and_reviews":
            # Monthly orders and avg review score together
            where = "WHERE o.order_purchase_timestamp >= '2017-01-01 00:00:00' AND o.order_purchase_timestamp <= '2017-12-31 23:59:59'" if not start_date else f"WHERE o.order_purchase_timestamp >= '{start_date}' AND o.order_purchase_timestamp <= '{end_date or '2018-12-31'}'"
            sql = f"""
                SELECT 
                    strftime('%Y-%m', o.order_purchase_timestamp) AS period,
                    COUNT(DISTINCT o.order_id) AS total_orders,
                    ROUND(AVG(r.review_score), 2) AS avg_review_score
                FROM olist_orders o
                LEFT JOIN olist_order_reviews r ON o.order_id = r.order_id
                {where}
                GROUP BY period
                ORDER BY period ASC
            """
            rows = conn.execute(sql).fetchall()
            cols = ["period", "total_orders", "avg_review_score"]
            data = [dict(zip(cols, r)) for r in rows]

        elif query_type == "seller_delivery_vs_reviews":
            # Correlation scatter data: seller delivery speed vs review score
            sql = """
                SELECT 
                    s.seller_id,
                    ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 2) AS avg_delivery_days,
                    ROUND(AVG(r.review_score), 2) AS avg_review_score,
                    COUNT(DISTINCT o.order_id) AS total_orders
                FROM olist_sellers s
                JOIN olist_order_items i ON s.seller_id = i.seller_id
                JOIN olist_orders o ON i.order_id = o.order_id
                JOIN olist_order_reviews r ON o.order_id = r.order_id
                WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
                GROUP BY s.seller_id
                HAVING total_orders >= 5
                ORDER BY total_orders DESC
                LIMIT 50
            """
            rows = conn.execute(sql).fetchall()
            cols = ["seller_id", "avg_delivery_days", "avg_review_score", "total_orders"]
            data = [dict(zip(cols, r)) for r in rows]

        elif query_type == "state_delay_vs_reviews":
            # State delivery delay and review score side by side
            sql = """
                SELECT 
                    c.customer_state AS state,
                    ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date)), 2) AS avg_delay_days,
                    ROUND(AVG(r.review_score), 2) AS avg_review_score,
                    COUNT(DISTINCT o.order_id) AS total_orders
                FROM olist_orders o
                JOIN olist_customers c ON o.customer_id = c.customer_id
                LEFT JOIN olist_order_reviews r ON o.order_id = r.order_id
                WHERE o.order_status = 'delivered'
                GROUP BY c.customer_state
                ORDER BY avg_delay_days DESC
            """
            rows = conn.execute(sql).fetchall()
            cols = ["state", "avg_delay_days", "avg_review_score", "total_orders"]
            data = [dict(zip(cols, r)) for r in rows]

        else:
            conn.close()
            return _format_error("INVALID_MULTI_QUERY", f"Unknown query_type: {query_type}")

        conn.close()
        return {
            "status": "success",
            "query_type": query_type,
            "data": data
        }
    except Exception as e:
        logger.error(f"Error in query_multi_tool_join: {e}")
        return _format_error("QUERY_EXECUTION_ERROR", str(e))
