"""持仓管理：分析、导入、增删。"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


import math

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0.0
    return obj


def _safe(default, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.exception("分析维度 %s 失败，回退默认值", getattr(fn, "__name__", fn))
        return default


class HoldItem(BaseModel):
    code: str
    name: str = ""


@router.post("/analyze")
def analyze(items: List[HoldItem]):
    from services.data import get_nav, get_all_funds, get_short_term_perf
    from services.metrics import (nav_percentile, trend_ma, rsi, max_drawdown,
                                   annual_volatility, sharpe_ratio, sortino_ratio, calmar_ratio)
    from services.direction import get_fund_direction
    from services.score import classify_region_by_name, region_label
    import pandas as pd

    try:
        all_funds = get_all_funds()
        name_map = {}
        for _, row in all_funds.iterrows():
            name_map[str(row.get("基金代码", ""))] = str(row.get("基金简称", ""))
    except Exception:
        name_map = {}

    passive_keywords = ["ETF", "指数", "联接", "纳斯达克", "标普", "沪深300", "中证500", "创业板", "科创"]
    out = []
    nav_data = {}

    def process_one(h):
        code = h.code
        name = name_map.get(code, h.name or code)
        region = classify_region_by_name(name)
        is_passive = any(kw in name for kw in passive_keywords)
        fund_type = "被动指数" if is_passive else "主动管理"
        try: df = get_nav(code)
        except Exception: df = pd.DataFrame()
        if df.empty:
            try: direction = get_fund_direction(code)
            except Exception: direction = ["暂无数据"]
            return {"code":code, "name":name, "fund_type":fund_type, "region":region_label(region), "direction":direction, "error":"无净值数据", "risk":{}}
        nav = df["nav"]
        pct = nav_percentile(nav)
        tr = trend_ma(nav)
        r_val = rsi(nav)
        mdd = max_drawdown(nav.tail(252))
        ret_1m = float(nav.iloc[-1] / nav.iloc[-22] - 1) if len(nav) >= 22 else 0
        ret_3m = float(nav.iloc[-1] / nav.iloc[-66] - 1) if len(nav) >= 66 else 0
        rets = nav.pct_change().dropna()
        if len(rets) >= 5:
            ann_vol = annual_volatility(rets); sharpe = sharpe_ratio(rets)
            sortino = sortino_ratio(rets); calmar_val = calmar_ratio(nav)
            fund_mdd_full = max_drawdown(nav)
        else:
            ann_vol = sharpe = sortino = calmar_val = fund_mdd_full = 0.0
        if pct < 0.30: advice = "当前估值偏低，被动指数基金定投性价比高"; passive_score = 85
        elif pct < 0.50: advice = "估值中性，被动+主动均可配置"; passive_score = 65
        elif pct < 0.70: advice = "估值偏高，主动基金选股能力可能更有优势"; passive_score = 40
        else: advice = "估值高位，建议精选主动基金或等回调再配置被动"; passive_score = 20
        try: direction = get_fund_direction(code)
        except Exception: direction = ["暂无数据"]
        try: perf = get_short_term_perf(code)
        except Exception: perf = {}
        return {"code":code, "name":name, "fund_type":fund_type, "region":region_label(region), "direction":direction,
                "percentile":round(pct,2), "rsi":round(r_val,0), "trend":tr, "max_drawdown":round(mdd,2),
                "ret_1m":round(ret_1m,3), "ret_3m":round(ret_3m,3), "passive_score":passive_score, "advice":advice, "perf":perf,
                "risk":{"annual_volatility":round(ann_vol,4), "sharpe_ratio":round(sharpe,4), "sortino_ratio":round(sortino,4), "calmar_ratio":round(calmar_val,4), "max_drawdown":round(fund_mdd_full,4)}}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_one, h): h for h in items}
        for future in as_completed(futures):
            h = futures[future]
            try: result = future.result()
            except Exception as exc:
                code = h.code; name = name_map.get(code, h.name or code)
                result = {"code":code, "name":name, "fund_type":"未知", "region":"未知", "direction":[], "error":"处理异常: "+str(exc), "risk":{}}
            out.append(result)

    for o in out:
        try: nav_data[o["code"]] = get_nav(o["code"])
        except Exception: pass

    code_order = {h.code: i for i, h in enumerate(items)}
    out.sort(key=lambda o: code_order.get(o["code"], 999))

    passive_count = sum(1 for o in out if o.get("fund_type") == "被动指数")
    active_count = len(out) - passive_count
    valid_out = [o for o in out if "error" not in o]
    avg_pct = sum(o.get("percentile", 0.5) for o in valid_out) / max(len(valid_out), 1)
    if avg_pct < 0.35: portfolio_advice = "整体估值偏低，建议增加被动指数配置，享受市场回升"
    elif avg_pct < 0.55: portfolio_advice = "估值中性，被动主动均衡配置"
    else: portfolio_advice = "整体估值偏高，建议适当降低被动比例，转向精选主动基金"

    empty_conc = {"top3_pct": 0, "top5_pct": 0, "level": "未知", "overlap_warning": None}
    concentration = _safe(empty_conc, _analyze_concentration, items, name_map)
    empty_val = {"avg_percentile": 0, "level": "未知", "advice": ""}
    valuation = _safe(empty_val, _analyze_valuation, valid_out)
    empty_risk = {"portfolio_volatility": 0, "portfolio_sharpe": 0, "portfolio_max_drawdown": 0}
    risk_metrics = _safe(empty_risk, _portfolio_risk_metrics, nav_data, items)
    empty_asset = {"allocation": {"股票":0,"债券":0,"现金":0,"其他":0}, "fund_count":0, "advice":""}
    asset_allocation = _safe(empty_asset, _analyze_asset_allocation, items, name_map)
    empty_region = {"allocation": {}, "fund_count": 0}
    region_allocation = _safe(empty_region, _analyze_region_allocation, items, name_map)
    empty_sector = {"top5": [], "fund_count": 0}
    sector_allocation = _safe(empty_sector, _analyze_sector_allocation, items, name_map)
    actions = _safe([], _generate_actions, asset_allocation, region_allocation, sector_allocation, concentration, valuation, valid_out, name_map)
    empty_grade = {"grade":"低", "portfolio_volatility":0, "max_drawdown":0, "top3_concentration":0}
    risk_grade = _safe(empty_grade, _analyze_risk_grade, risk_metrics, valid_out, concentration)

    out = _sanitize(out); concentration = _sanitize(concentration); valuation = _sanitize(valuation)
    risk_metrics = _sanitize(risk_metrics); asset_allocation = _sanitize(asset_allocation)
    region_allocation = _sanitize(region_allocation); sector_allocation = _sanitize(sector_allocation)
    actions = _sanitize(actions); risk_grade = _sanitize(risk_grade)

    failed_count = sum(1 for o in out if o.get("error"))
    return {
        "funds": out,
        "summary": {"total": len(out), "analyzed_count": len(out)-failed_count, "failed_count": failed_count,
                    "passive_count": passive_count, "active_count": active_count,
                    "avg_percentile": round(avg_pct,2), "portfolio_advice": portfolio_advice,
                    "directions": list(set(d for o in out for d in o.get("direction",[])))[:5]},
        "concentration": concentration, "valuation_health": valuation, "risk_metrics": risk_metrics,
        "asset_allocation": asset_allocation, "region_allocation": region_allocation,
        "sector_allocation": sector_allocation, "actions": actions, "risk_grade": risk_grade,
    }


def _analyze_concentration(items, name_map):
    from services.data import get_full_holdings
    from services.direction import _STOCK_SECTOR
    stock_agg = {}; sector_funds = {}
    for h in items:
        code = h.code
        try: fh = get_full_holdings(code)
        except Exception: continue
        holdings = fh.get("持仓", [])
        for s in holdings:
            scode = str(s.get("代码","")); sname = str(s.get("名称","")); spct = float(s.get("占比",0))
            sector = _STOCK_SECTOR.get(scode, "其他")
            key = scode if scode else sname
            if key not in stock_agg: stock_agg[key] = {"total_weight":0.0, "funds":set(), "sector":sector, "name":sname}
            stock_agg[key]["total_weight"] += spct; stock_agg[key]["funds"].add(code)
            if sector not in sector_funds: sector_funds[sector] = set()
            sector_funds[sector].add(code)
    if not stock_agg: return {"top3_pct":0, "top5_pct":0, "level":"未知", "overlap_warning":None}
    total = sum(d["total_weight"] for d in stock_agg.values()) or 1.0
    sorted_stocks = sorted(stock_agg.values(), key=lambda x: x["total_weight"], reverse=True)
    top3_pct = sum(s["total_weight"] for s in sorted_stocks[:3]) / total * 100
    top5_pct = sum(s["total_weight"] for s in sorted_stocks[:5]) / total * 100
    level = "高风险" if top3_pct>60 else ("中等" if top3_pct>30 else "分散")
    overlap_warning = None; warnings = []
    for sector, fund_codes in sector_funds.items():
        if sector != "其他" and len(fund_codes) >= 2:
            fund_names = [name_map.get(c,c) for c in sorted(fund_codes)]
            warnings.append("{}方向重叠：{}均重仓该板块".format(sector, "、".join(fund_names[:3])))
    if warnings: overlap_warning = "；".join(warnings[:2])
    return {"top3_pct":round(top3_pct,1), "top5_pct":round(top5_pct,1), "level":level, "overlap_warning":overlap_warning}


def _analyze_valuation(valid_out):
    percentiles = [o.get("percentile") for o in valid_out if o.get("percentile") is not None]
    if not percentiles: return {"avg_percentile":0, "level":"未知", "advice":""}
    avg_pct = sum(percentiles) / len(percentiles)
    if avg_pct < 0.20: level, advice = "极度低估", "整体处于极度低估区间，布局性价比极高，建议分批建仓"
    elif avg_pct < 0.40: level, advice = "低估", "整体估值偏低，定投或分批买入的较好时机"
    elif avg_pct < 0.60: level, advice = "合理", "整体估值合理，维持现有配置即可"
    elif avg_pct < 0.80: level, advice = "偏高", "整体估值偏高，建议等待回调或定投建仓"
    else: level, advice = "高估", "整体估值处于高位，建议适当减仓，控制风险"
    return {"avg_percentile":round(avg_pct,2), "level":level, "advice":advice}


def _portfolio_risk_metrics(nav_data, items):
    import pandas as pd
    from services.metrics import max_drawdown, annual_volatility, sharpe_ratio
    nav_series = {}
    for h in items:
        df = nav_data.get(h.code)
        if df is None or df.empty: continue
        nav = df.set_index("date")["nav"]; nav = nav[~nav.index.duplicated(keep="last")]
        nav_series[h.code] = nav
    if len(nav_series) < 1: return {"portfolio_volatility":0, "portfolio_sharpe":0, "portfolio_max_drawdown":0}
    nav_df = pd.DataFrame(nav_series).dropna()
    if nav_df.empty or nav_df.shape[1] < 1: return {"portfolio_volatility":0, "portfolio_sharpe":0, "portfolio_max_drawdown":0}
    nav_df = nav_df / nav_df.iloc[0]; port_nav = nav_df.mean(axis=1); rets = port_nav.pct_change().dropna()
    if len(rets) < 5: return {"portfolio_volatility":0, "portfolio_sharpe":0, "portfolio_max_drawdown":0}
    return {"portfolio_volatility":round(annual_volatility(rets),4), "portfolio_sharpe":round(sharpe_ratio(rets),4), "portfolio_max_drawdown":round(max_drawdown(port_nav),4)}


def _asset_advice(allocation):
    stock = allocation.get("股票", 0)
    if stock > 90: return "权益占比极高，建议增加债券和现金配置"
    elif stock > 75: return "权益占比较高，建议配置10-20%债券平衡风险"
    elif stock < 30: return "权益占比较低，进攻性不足，可考虑增加权益配置"
    else: return "资产配置较为均衡"


def _analyze_asset_allocation(items, name_map):
    from datetime import datetime
    import akshare as ak
    year = str(datetime.now().year)
    result = {"股票":0,"债券":0,"现金":0,"其他":0}; count = 0
    for h in items:
        try:
            df = ak.fund_portfolio_asset_allocation_em(symbol=h.code, date=year)
            if df is not None and not df.empty:
                row = df.iloc[0]
                result["股票"] += float(row.get("股票占净值比例",0) or 0)
                result["债券"] += float(row.get("债券占净值比例",0) or 0)
                result["现金"] += float(row.get("现金占净值比例",0) or 0)
                result["其他"] += float(row.get("其他占净值比例",0) or 0)
                count += 1
        except Exception:
            pass
    if count > 0:
        for k in result: result[k] = round(result[k]/count, 1)
    else:
        # Fallback: infer from fund type keywords
        stock_count = 0; bond_count = 0
        for h in items:
            name = name_map.get(h.code, "")
            if any(kw in name for kw in ["债券","纯债","国债","信用债","可转债","债基"]):
                result["债券"] += 90; result["股票"] += 5; result["现金"] += 3; result["其他"] += 2
                bond_count += 1
            elif any(kw in name for kw in ["货币","现金"]):
                result["现金"] += 95; result["债券"] += 5
                bond_count += 1
            else:
                # Stock/equity/hybrid/QDII → assume ~90% equity
                result["股票"] += 90; result["现金"] += 7; result["其他"] += 3
                stock_count += 1
            count += 1
        if count > 0:
            for k in result: result[k] = round(result[k]/count, 1)
    return {"allocation":result, "fund_count":count, "advice":_asset_advice(result)}


def _analyze_region_allocation(items, name_map):
    from services.data import get_full_holdings
    result = {}; count = 0
    for h in items:
        try:
            fh = get_full_holdings(h.code)
            region_dist = fh.get("地域分布", {})
            if region_dist:
                for k, v in region_dist.items():
                    if v > 0: result[k] = result.get(k, 0) + v
                count += 1
        except Exception: pass
    if count > 0:
        for k in result: result[k] = round(result[k]/count, 1)
    return {"allocation": dict(sorted(result.items(), key=lambda x: x[1], reverse=True)), "fund_count": count}


def _analyze_sector_allocation(items, name_map):
    from datetime import datetime
    import akshare as ak
    year = str(datetime.now().year)
    result = {}; count = 0
    for h in items:
        try:
            df = ak.fund_portfolio_industry_allocation_em(symbol=h.code, date=year)
            if df is not None and not df.empty:
                name_col = pct_col = None
                for col in df.columns:
                    if "行业" in str(col): name_col = col
                    if "比例" in str(col) or "占比" in str(col): pct_col = col
                if name_col and pct_col:
                    for _, row in df.iterrows():
                        sn = str(row.get(name_col, "")); pct = float(row.get(pct_col, 0) or 0)
                        if sn and sn != "nan": result[sn] = result.get(sn, 0) + pct
                    count += 1
        except Exception: pass
    if count > 0:
        for k in result: result[k] = round(result[k]/count, 1)
    top5 = [{"行业": k, "占比": v} for k, v in sorted(result.items(), key=lambda x: x[1], reverse=True)[:5]]
    return {"top5": top5, "fund_count": count}


def _analyze_risk_grade(portfolio_risk, valid_out, concentration):
    vol = portfolio_risk.get("portfolio_volatility", 0)
    mdd = portfolio_risk.get("portfolio_max_drawdown", 0)
    top3 = concentration.get("top3_pct", 0)
    if vol > 0.25 or mdd < -0.4: grade = "高"
    elif vol > 0.15 or mdd < -0.2: grade = "中"
    else: grade = "低"
    return {"grade": grade, "portfolio_volatility": vol, "max_drawdown": mdd, "top3_concentration": top3}


def _generate_actions(asset_allocation, region_allocation, sector_allocation, concentration, valuation, valid_out, name_map):
    actions = []
    alloc = asset_allocation.get("allocation", {})
    stock_pct = alloc.get("股票", 0)
    if stock_pct > 85:
        actions.append({"action":"新增类别","target":"债券基金(如中长期纯债)","reason":"权益占比{}%，建议配置10-20%债券降低波动".format(stock_pct)})
    elif stock_pct > 75:
        actions.append({"action":"新增类别","target":"债券基金","reason":"权益占比{}%，可配置10%左右债券平衡风险".format(stock_pct)})

    region_alloc = region_allocation.get("allocation", {})
    for rn, pct in region_alloc.items():
        if pct > 60:
            actions.append({"action":"新增类别","target":"非{}市场指数基金".format(rn),"reason":"{}占比{}%，高度集中单一市场".format(rn, pct)})
            break

    for s in sector_allocation.get("top5", []):
        if s.get("占比", 0) > 50:
            actions.append({"action":"新增类别","target":"不同行业基金","reason":"{}行业占比{}%，注意板块轮动风险".format(s["行业"], s["占比"])})
            break

    for o in valid_out:
        pct = o.get("percentile", 0)
        if isinstance(pct, (int, float)) and pct > 0.80 and len(actions) < 6:
            actions.append({"action":"减持","target":"{}(估值分位{}%)".format(o["name"], round(pct*100)),"reason":"估值高位，建议减仓或换到低估值替代"})

    if concentration.get("level") == "高风险" and len(actions) < 6:
        actions.append({"action":"减持","target":"前3大重仓股","reason":"前3大持仓占比{}%，集中度过高".format(concentration.get("top3_pct",0))})
    if concentration.get("overlap_warning") and len(actions) < 6:
        actions.append({"action":"替换","target":"重叠持仓基金","reason":concentration["overlap_warning"]})

    avg_pct = valuation.get("avg_percentile", 0.5)
    if avg_pct > 0.80 and len(actions) < 6:
        actions.append({"action":"减持","target":"整体组合","reason":"组合整体估值偏高，建议适当降低仓位或等待回调"})
    elif avg_pct < 0.20 and len(actions) < 6:
        actions.append({"action":"加仓","target":"整体组合","reason":"组合整体处于低估值区间，当前是较好的布局时机"})
    return actions[:6]


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
    from db import save_holding
    codes = []
    for h in items:
        save_holding(h.code, h.name)
        codes.append(h.code)
    return {"ok": True, "codes": codes, "count": len(codes)}
