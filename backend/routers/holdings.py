from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class HoldItem(BaseModel):
    code: str
    name: str = ""

@router.post("/analyze")
def analyze(items: List[HoldItem]):
    """分析持仓：方向 + 主动/被动建议。"""
    from services.data import get_nav, get_all_funds
    from services.metrics import nav_percentile, trend_ma, rsi, max_drawdown
    from services.direction import get_fund_direction
    from services.score import classify_region_by_name, region_label

    # Get fund names
    try:
        all_funds = get_all_funds()
        name_map = {}
        for _, row in all_funds.iterrows():
            name_map[str(row.get("基金代码",""))] = str(row.get("基金简称",""))
    except: name_map = {}

    # Classify active vs passive
    passive_keywords = ["ETF","指数","联接","纳斯达克","标普","沪深300","中证500","创业板","科创"]

    out = []
    for h in items:
        code = h.code
        name = name_map.get(code, h.name or code)
        region = classify_region_by_name(name)

        # Active vs Passive
        is_passive = any(kw in name for kw in passive_keywords)
        fund_type = "被动指数" if is_passive else "主动管理"

        # Get nav for analysis
        df = get_nav(code)
        if df.empty:
            out.append({"code":code,"name":name,"fund_type":fund_type,"region":region_label(region),
                       "direction":get_fund_direction(code),"error":"无净值数据"})
            continue

        nav = df["nav"]
        pct = nav_percentile(nav)
        tr = trend_ma(nav)
        r = rsi(nav)
        mdd = max_drawdown(nav.tail(252))
        ret_1m = float(nav.iloc[-1]/nav.iloc[-22]-1) if len(nav)>=22 else 0
        ret_3m = float(nav.iloc[-1]/nav.iloc[-66]-1) if len(nav)>=66 else 0

        # Passive vs Active recommendation based on market conditions
        if pct < 0.30:
            advice = "📈 当前估值偏低，被动指数基金定投性价比高"
            passive_score = 85
        elif pct < 0.50:
            advice = "✅ 估值中性，被动+主动均可配置"
            passive_score = 65
        elif pct < 0.70:
            advice = "⚠️ 估值偏高，主动基金选股能力可能更有优势"
            passive_score = 40
        else:
            advice = "🔴 估值高位，建议精选主动基金或等回调再配置被动"
            passive_score = 20

        out.append({
            "code": code, "name": name,
            "fund_type": fund_type, "region": region_label(region),
            "direction": get_fund_direction(code),
            "percentile": round(pct, 2), "rsi": round(r, 0),
            "trend": tr, "max_drawdown": round(mdd, 2),
            "ret_1m": round(ret_1m, 3), "ret_3m": round(ret_3m, 3),
            "passive_score": passive_score,
            "advice": advice,
        })

    # Portfolio-level summary
    passive_count = sum(1 for o in out if o.get("fund_type")=="被动指数")
    active_count = len(out) - passive_count
    avg_pct = sum(o.get("percentile",0.5) for o in out) / max(len(out),1)

    if avg_pct < 0.35:
        portfolio_advice = "📈 整体估值偏低，建议增加被动指数配置，享受市场回升"
    elif avg_pct < 0.55:
        portfolio_advice = "✅ 估值中性，被动主动均衡配置"
    else:
        portfolio_advice = "⚠️ 整体估值偏高，建议适当降低被动比例，转向精选主动基金"

    return {
        "funds": out,
        "summary": {
            "total": len(out), "passive_count": passive_count, "active_count": active_count,
            "avg_percentile": round(avg_pct, 2),
            "portfolio_advice": portfolio_advice,
            "directions": list(set(d for o in out for d in o.get("direction",[])))[:5],
        }
    }

@router.get("/list")
def list_holdings():
    from db import list_holdings as lh
    return lh()

class SaveItem(BaseModel):
    code: str
    name: str = ""

@router.post("/save")
def save(item: SaveItem):
    from db import save_holding
    save_holding(item.code, item.name)
    return {"ok": True}

@router.delete("/del")
def remove(code: str):
    from db import del_holding
    del_holding(code)
    return {"ok": True}

@router.post("/batch-import")
def batch_import(items: List[SaveItem]):
    """批量导入：只填代码即可。"""
    from db import save_holding, list_holdings
    for h in items:
        save_holding(h.code, h.name)
    # Auto-analyze
    return analyze([HoldItem(code=h.code, name=h.name) for h in items])
