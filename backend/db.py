"""SQLite 存储：持仓 + 自选"""
import sqlite3
DB = "fund.db"

def conn(): return sqlite3.connect(DB)

def init_db():
    c = conn(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS watch(code TEXT PRIMARY KEY)")
    cur.execute("""CREATE TABLE IF NOT EXISTS holding(
        code TEXT PRIMARY KEY, cost REAL, shares REAL, name TEXT DEFAULT '', region TEXT DEFAULT 'A股')""")
    try:
        cur.execute("ALTER TABLE holding ADD COLUMN region TEXT DEFAULT 'A股'")
    except:
        pass
    c.commit(); c.close()

def add_watch(code):
    c = conn(); c.execute("INSERT OR IGNORE INTO watch VALUES(?)", (code,)); c.commit(); c.close()
def del_watch(code):
    c = conn(); c.execute("DELETE FROM watch WHERE code=?", (code,)); c.commit(); c.close()
def list_watch():
    c = conn(); rows = c.execute("SELECT code FROM watch").fetchall(); c.close()
    return [{"code": r[0]} for r in rows]

def save_holding(code, cost, shares, name="", region="A股"):
    c = conn()
    c.execute("INSERT OR REPLACE INTO holding VALUES(?,?,?,?,?)", (code, cost, shares, name, region))
    c.commit(); c.close()
def list_holdings():
    c = conn(); rows = c.execute("SELECT code, cost, shares, name, region FROM holding").fetchall(); c.close()
    return [{"code":r[0],"cost":r[1],"shares":r[2],"name":r[3],"region":r[4]} for r in rows]
def del_holding(code):
    c = conn(); c.execute("DELETE FROM holding WHERE code=?", (code,)); c.commit(); c.close()
