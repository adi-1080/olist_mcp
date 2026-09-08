"""
Persistent Storage & Lifecycle Management for Pinnable Dashboard Items.
Stores pins in SQLite with refresh and diff detection support.
"""

import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from src.database.loader import get_db_connection
from src.agent.base import AgentResponse
from src.dashboard.diff_engine import detect_significant_changes

logger = logging.getLogger(__name__)

def init_pins_table():
    """Initializes dashboard_pins table in SQLite database."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_pins (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            chart_type TEXT NOT NULL,
            justification TEXT NOT NULL,
            insight TEXT NOT NULL,
            chart_config TEXT NOT NULL,
            raw_data TEXT NOT NULL,
            pinned_at TEXT NOT NULL,
            last_refreshed_at TEXT NOT NULL,
            has_significant_change INTEGER DEFAULT 0,
            change_summary TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def pin_chart(response: AgentResponse) -> Dict[str, Any]:
    """Saves a chart query result to the persistent dashboard."""
    init_pins_table()
    conn = get_db_connection()

    pin_id = str(uuid.uuid4())[:8]
    now_str = datetime.datetime.now().isoformat()

    conn.execute("""
        INSERT INTO dashboard_pins (
            id, query, chart_type, justification, insight, chart_config, raw_data, pinned_at, last_refreshed_at, has_significant_change, change_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'Pinned initially.')
    """, (
        pin_id,
        response.query,
        response.chart_type,
        response.justification,
        response.insight,
        json.dumps(response.chart_config),
        json.dumps(response.raw_data),
        now_str,
        now_str
    ))
    conn.commit()
    conn.close()

    logger.info(f"Chart pinned successfully with ID: {pin_id}")
    return get_pin_by_id(pin_id)

def get_all_pins() -> List[Dict[str, Any]]:
    """Retrieves all pinned dashboard charts."""
    init_pins_table()
    conn = get_db_connection()

    rows = conn.execute("SELECT id, query, chart_type, justification, insight, chart_config, raw_data, pinned_at, last_refreshed_at, has_significant_change, change_summary FROM dashboard_pins ORDER BY pinned_at DESC").fetchall()
    conn.close()

    pins = []
    for r in rows:
        pins.append({
            "id": r[0],
            "query": r[1],
            "chart_type": r[2],
            "justification": r[3],
            "insight": r[4],
            "chart_config": json.loads(r[5]),
            "raw_data": json.loads(r[6]),
            "pinned_at": r[7],
            "last_refreshed_at": r[8],
            "has_significant_change": bool(r[9]),
            "change_summary": r[10]
        })
    return pins

def get_pin_by_id(pin_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single pinned item by ID."""
    init_pins_table()
    conn = get_db_connection()
    row = conn.execute("SELECT id, query, chart_type, justification, insight, chart_config, raw_data, pinned_at, last_refreshed_at, has_significant_change, change_summary FROM dashboard_pins WHERE id = ?", (pin_id,)).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "query": row[1],
        "chart_type": row[2],
        "justification": row[3],
        "insight": row[4],
        "chart_config": json.loads(row[5]),
        "raw_data": json.loads(row[6]),
        "pinned_at": row[7],
        "last_refreshed_at": row[8],
        "has_significant_change": bool(row[9]),
        "change_summary": row[10]
    }

async def refresh_pin(pin_id: str) -> Optional[Dict[str, Any]]:
    """
    Refreshes a pinned chart by re-running its original query against current database state
    and detecting significant metric changes.
    """
    pin = get_pin_by_id(pin_id)
    if not pin:
        return None

    from src.agent.factory import get_agent
    agent = get_agent()
    new_response = await agent.process_query(pin["query"])

    has_sig_change, summary, _ = detect_significant_changes(
        old_data=pin["raw_data"],
        new_data=new_response.raw_data
    )

    now_str = datetime.datetime.now().isoformat()
    conn = get_db_connection()
    conn.execute("""
        UPDATE dashboard_pins
        SET chart_type = ?,
            justification = ?,
            insight = ?,
            chart_config = ?,
            raw_data = ?,
            last_refreshed_at = ?,
            has_significant_change = ?,
            change_summary = ?
        WHERE id = ?
    """, (
        new_response.chart_type,
        new_response.justification,
        new_response.insight,
        json.dumps(new_response.chart_config),
        json.dumps(new_response.raw_data),
        now_str,
        1 if has_sig_change else 0,
        summary,
        pin_id
    ))
    conn.commit()
    conn.close()

    logger.info(f"Pin {pin_id} refreshed. Significant change: {has_sig_change}")
    return get_pin_by_id(pin_id)

def delete_pin(pin_id: str) -> bool:
    """Deletes a pinned chart from dashboard."""
    init_pins_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dashboard_pins WHERE id = ?", (pin_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
