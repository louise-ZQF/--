from fastapi import APIRouter
from pydantic import BaseModel
from services.data import get_nav, get_fund_direction
from services.metrics import max_drawdown, nav_percentile, trend_ma

router = APIRouter()

class HoldingItem(BaseModel):
    code: str
    cost: float = 0.0
    shares: float = 0.0
    name: str = ""

class BatchImportItem(BaseModel):
    code: str
    cost: float = 0.0
    dca_daily: float = 0.0
    name: str = ""

def classify_region(code: str, name: str = "") -> str:
    if "QDII" in name.upper() or "海外" in name or "全球" in name:
        return "海外"
    if "港股" in name or "恒生" in name or "香港" in name:
        return "港股"
    return "A股"

@router.post("/analyze")
def analyze(items: list[HoldingItem]):
    analyzed = [
        {"code": h.code, "cost": h.cost, "shares": h.shares, "name": h.name}
        for h in items
    ]
    return analyze_and_advise(analyzed)

def analyze_and_advise(items: list):
    out = []
    for h in items:
        code = h.get("code", "")
        name = h.get("name", "")
        df = get_nav(code)
        if df.empty:
            out.append({"code": code, "error": "无净值数据"})
            continue
        nav = df["nav"]
        cur = float(nav.iloc[-1])
        cost = h.get("cost", 0)
        ret = cur / cost - 1 if cost > 0 else 0.0
        mdd = max_drawdown(nav.tail(252))
        pct = nav_percentile(nav)
        tr = trend_ma(nav)
        region = classify_region(code, name)
        directions = get_fund_direction(code)

        if pct < 0.25 and tr == "向上":
            dca_advice = "📈 加大定投"
            dca_reason = f"估值低位(分位{pct:.0%})+趋势向上，是定投黄金期"
        elif pct < 0.25:
            dca_advice = "✅ 保持定投"
            dca_reason = f"估值低位(分位{pct:.0%})，虽然趋势{tr}，但定投性价比高"
        elif pct < 0.50:
            dca_advice = "✅ 保持定投"
            dca_reason = f"估值中性(分位{pct:.0%})，趋势{tr}，维持原节奏"
        elif pct < 0.75:
            dca_advice = "⚠️ 降低定投"
            dca_reason = f"估值偏高(分位{pct:.0%})，建议降低定投金额"
        elif tr == "向下":
            dca_advice = "⏸️ 暂停定投"
            dca_reason = f"估值高位(分位{pct:.0%})+趋势向下，暂停等待更好时机"
        else:
            dca_advice = "⚠️ 降低定投"
            dca_reason = f"估值高位(分位{pct:.0%})，降低定投等待回调"

        out.append({
            "code": code, "name": name,
            "current_nav": round(cur, 4),
            "return": round(ret, 4), "max_drawdown": round(mdd, 4),
            "percentile": round(pct, 4), "trend": tr,
            "dca_advice": dca_advice, "dca_reason": dca_reason,
            "region": region, "directions": directions,
        })
    return out

@router.post("/batch-import")
def batch_import(items: list[BatchImportItem]):
    from db import save_holding, conn as db_conn
    c = db_conn()
    c.execute("CREATE TABLE IF NOT EXISTS dca_plan(code TEXT PRIMARY KEY, daily_amount REAL, enabled INTEGER DEFAULT 1)")
    for h in items:
        region = classify_region(h.code, h.name)
        save_holding(h.code, h.cost, 0, h.name, region)
        c.execute("INSERT OR REPLACE INTO dca_plan VALUES(?,?,1)", (h.code, h.dca_daily))
    c.commit(); c.close()
    analyzed = [
        {"code": h.code, "cost": h.cost, "shares": 0, "name": h.name}
        for h in items
    ]
    return analyze_and_advise(analyzed)

@router.get("/list")
def list_holdings():
    from db import list_holdings as lh
    return lh()

@router.post("/save")
def save(item: HoldingItem):
    from db import save_holding
    region = classify_region(item.code, item.name)
    save_holding(item.code, item.cost, item.shares, item.name, region)
    return {"ok": True}

@router.delete("/del")
def remove(code: str):
    from db import del_holding
    del_holding(code)
    return {"ok": True}
