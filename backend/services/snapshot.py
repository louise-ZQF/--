"""快照缓存：5小时内返回同一份数据，过期才重算。"""
import json
import time
import sqlite3
from typing import Optional
from db import DB

SNAPSHOT_TTL = 5 * 3600  # 5 hours

def get_snapshot(key: str) -> Optional[dict]:
    """读取快照，未过期返回数据，过期返回None。"""
    try:
        with sqlite3.connect(DB) as conn:
            row = conn.execute(
                "SELECT json, updated_at FROM snapshot WHERE key=?",
                (key,)
            ).fetchone()
            if row:
                data = json.loads(row[0])
                age = time.time() - row[1]
                if age < SNAPSHOT_TTL:
                    return data
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        _init_snapshot_table()
    except Exception:
        pass
    return None

def set_snapshot(key: str, data) -> None:
    """写入快照。"""
    try:
        with sqlite3.connect(DB) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO snapshot(key, json, updated_at) VALUES(?,?,?)",
                (key, json.dumps(data, ensure_ascii=False, default=str), time.time())
            )
            conn.commit()
    except sqlite3.OperationalError:
        _init_snapshot_table()
        set_snapshot(key, data)
    except Exception:
        pass

def _init_snapshot_table():
    """创建快照表。"""
    try:
        with sqlite3.connect(DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS snapshot ("
                "key TEXT PRIMARY KEY, json TEXT, updated_at REAL)"
            )
            conn.commit()
    except Exception:
        pass
