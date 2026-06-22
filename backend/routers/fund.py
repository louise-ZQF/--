"""基金统一持仓接口。"""
import logging
from fastapi import APIRouter, Query
from services.data import get_full_holdings, get_fund_name

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/holdings")
def fund_holdings(code: str = Query(..., description="6位基金代码")):
    """获取基金统一持仓数据，含前十大重仓、地区配置、季度标签。"""
    try:
        raw = get_full_holdings(code)
        holdings = raw.get("持仓", [])
        region = raw.get("地域分布", {})
        quarter_raw = raw.get("季度", "")
        quarter_display = ""
        if quarter_raw:
            try:
                quarter_display = f"{quarter_raw[:4]}年{quarter_raw[4:6]}季度股票投资明细"
            except Exception:
                quarter_display = str(quarter_raw)
        top_holdings = [
            {"code": h.get("代码", ""), "name": h.get("名称", ""),
             "pct": h.get("占比", 0), "market": h.get("市场", "其他")}
            for h in holdings[:10]
        ]
        region_allocation = {k: v for k, v in region.items() if v > 0}
        total_pct = raw.get("总占比", 0)
        fund_name = get_fund_name(code)
        return {
            "code": code, "name": fund_name, "quarter": quarter_display,
            "top_holdings": top_holdings, "region_allocation": region_allocation,
            "total_pct": total_pct, "disclaimer": "基于披露的前十大重仓，合计可能小于100%",
        }
    except Exception as e:
        logger.exception("获取持仓失败 %s", code)
        return {
            "code": code, "name": "", "quarter": "", "top_holdings": [],
            "region_allocation": {}, "total_pct": 0,
            "disclaimer": "基于披露的前十大重仓，合计可能小于100%", "error": str(e),
        }
