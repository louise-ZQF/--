from fastapi import APIRouter
from pydantic import BaseModel
from services.data import get_nav
from services.metrics import max_drawdown, nav_percentile, trend_ma

router = APIRouter()

class HoldingItem(BaseModel):
    code: str
    cost: float = 0.0
    shares: float = 0.0
    name: str = ""

@router.post("/analyze")
def analyze(items: list[HoldingItem]):
    out = []
    for h in items:
        df = get_nav(h.code)
        if df.empty:
            out.append({"code":h.code,"error":"未找到净值数据"})
            continue
        nav = df["nav"]
        cur = float(nav.iloc[-1])
        ret = cur / h.cost - 1 if h.cost > 0 else 0.0
        mdd = max_drawdown(nav.tail(252))
        pct = nav_percentile(nav)
        tr = trend_ma(nav)

        if pct < 0.30 and tr != "向下":
            advice, reason = "建议加大定投", f"净值处于近3年{pct:.0%}分位(偏低),趋势{tr},定投性价比高"
        elif pct > 0.70:
            advice, reason = "建议暂缓定投", f"净值处于{pct:.0%}分位(偏高),继续买入性价比下降"
        else:
            advice, reason = "正常定投", f"净值处于{pct:.0%}分位(中性),维持原节奏"

        out.append({
            "code": h.code, "name": h.name,
            "current_nav": round(cur, 4),
            "return": round(ret, 4), "max_drawdown": round(mdd, 4),
            "percentile": round(pct, 4), "trend": tr,
            "advice": advice, "reason": reason,
        })
    return out

@router.get("/list")
def list_holdings():
    from db import list_holdings as lh
    return lh()

@router.post("/save")
def save(item: HoldingItem):
    from db import save_holding
    save_holding(item.code, item.cost, item.shares, item.name)
    return {"ok": True}

@router.delete("/del")
def remove(code: str):
    from db import del_holding
    del_holding(code)
    return {"ok": True}
