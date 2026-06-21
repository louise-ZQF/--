"""持仓管理：分析、导入、增删。"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class HoldItem(BaseModel):
    code: str
    name: str = ""


# ======================================================================
# Core Analyze Endpoint (parallel per-fund processing)
# ======================================================================


@router.post("/analyze")
def analyze(items: List[HoldItem]):
    """分析持仓：方向 + 主动/被动建议 + 集中度/相关性/风险/估值/改进建议。

    每只基金的处理通过 ThreadPoolExecutor 并行执行（max_workers=5），
    单只基金的网络请求失败不会导致整体崩溃，错误信息会暴露在对应基金的
    ``error`` 字段中。
    """
    from services.data import get_nav, get_all_funds, get_short_term_perf
    from services.metrics import (nav_percentile, trend_ma, rsi, max_drawdown,
                                   annual_volatility, sharpe_ratio, sortino_ratio, calmar_ratio)
    from services.direction import get_fund_direction
    from services.score import classify_region_by_name, region_label
    import pandas as pd

    # --- Fund name map (single network call, runs before parallel workers) ---
    try:
        all_funds = get_all_funds()
        name_map = {}
        for _, row in all_funds.iterrows():
            name_map[str(row.get("基金代码", ""))] = str(row.get("基金简称", ""))
    except Exception:
        name_map = {}

    passive_keywords = ["ETF", "指数", "联接", "纳斯达克", "标普",
                        "沪深300", "中证500", "创业板", "科创"]

    out = []
    nav_data = {}

    # --- Per-fund analysis worker (runs in thread pool) ---
    def process_one(h):
        """处理单只基金 — 在 ThreadPoolExecutor worker 线程中运行。

        所有网络调用 / 计算异常均被捕获并以 ``error`` 字段返回，
        绝不会向调用方抛出异常。
        """
        code = h.code
        name = name_map.get(code, h.name or code)
        region = classify_region_by_name(name)
        is_passive = any(kw in name for kw in passive_keywords)
        fund_type = "被动指数" if is_passive else "主动管理"

        try:
            df = get_nav(code)
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            try:
                direction = get_fund_direction(code)
            except Exception:
                direction = ["暂无数据"]
            return {
                "code": code,
                "name": name,
                "fund_type": fund_type,
                "region": region_label(region),
                "direction": direction,
                "error": "无净值数据",
                "risk": {},
            }

        nav = df["nav"]
        pct = nav_percentile(nav)
        tr = trend_ma(nav)
        r_val = rsi(nav)
        mdd = max_drawdown(nav.tail(252))
        ret_1m = float(nav.iloc[-1] / nav.iloc[-22] - 1) if len(nav) >= 22 else 0
        ret_3m = float(nav.iloc[-1] / nav.iloc[-66] - 1) if len(nav) >= 66 else 0

        # Enhanced risk metrics per fund
        rets = nav.pct_change().dropna()
        if len(rets) >= 5:
            ann_vol = annual_volatility(rets)
            sharpe = sharpe_ratio(rets)
            sortino = sortino_ratio(rets)
            calmar_val = calmar_ratio(nav)
            fund_mdd_full = max_drawdown(nav)
        else:
            ann_vol = sharpe = sortino = calmar_val = fund_mdd_full = 0.0

        # Passive vs Active recommendation
        if pct < 0.30:
            advice = "当前估值偏低，被动指数基金定投性价比高"
            passive_score = 85
        elif pct < 0.50:
            advice = "估值中性，被动+主动均可配置"
            passive_score = 65
        elif pct < 0.70:
            advice = "估值偏高，主动基金选股能力可能更有优势"
            passive_score = 40
        else:
            advice = "估值高位，建议精选主动基金或等回调再配置被动"
            passive_score = 20

        try:
            direction = get_fund_direction(code)
        except Exception:
            direction = ["暂无数据"]

        try:
            perf = get_short_term_perf(code)
        except Exception:
            perf = {}

        return {
            "code": code,
            "name": name,
            "fund_type": fund_type,
            "region": region_label(region),
            "direction": direction,
            "percentile": round(pct, 2),
            "rsi": round(r_val, 0),
            "trend": tr,
            "max_drawdown": round(mdd, 2),
            "ret_1m": round(ret_1m, 3),
            "ret_3m": round(ret_3m, 3),
            "passive_score": passive_score,
            "advice": advice,
            "perf": perf,
            "risk": {
                "annual_volatility": round(ann_vol, 4),
                "sharpe_ratio": round(sharpe, 4),
                "sortino_ratio": round(sortino, 4),
                "calmar_ratio": round(calmar_val, 4),
                "max_drawdown": round(fund_mdd_full, 4),
            },
        }

    # --- Launch parallel workers ---
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_one, h): h for h in items}
        for future in as_completed(futures):
            h = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                code = h.code
                name = name_map.get(code, h.name or code)
                result = {
                    "code": code,
                    "name": name,
                    "fund_type": "未知",
                    "region": "未知",
                    "direction": [],
                    "error": "处理异常: " + str(exc),
                    "risk": {},
                }
            out.append(result)

    # Collect nav_data for downstream helpers (correlation / risk).
    for o in out:
        code = o["code"]
        try:
            nav_data[code] = get_nav(code)
        except Exception:
            pass

    # Restore original input order
    code_order = {h.code: i for i, h in enumerate(items)}
    out.sort(key=lambda o: code_order.get(o["code"], 999))

    # --- Portfolio summary ---
    passive_count = sum(1 for o in out if o.get("fund_type") == "被动指数")
    active_count = len(out) - passive_count
    valid_out = [o for o in out if "error" not in o]
    avg_pct = sum(o.get("percentile", 0.5) for o in valid_out) / max(len(valid_out), 1)

    if avg_pct < 0.35:
        portfolio_advice = "整体估值偏低，建议增加被动指数配置，享受市场回升"
    elif avg_pct < 0.55:
        portfolio_advice = "估值中性，被动主动均衡配置"
    else:
        portfolio_advice = "整体估值偏高，建议适当降低被动比例，转向精选主动基金"

    # --- 5 analysis dimensions ---
    concentration = _analyze_concentration(items, name_map)
    correlation = _analyze_correlation(nav_data, items, name_map)
    valuation = _analyze_valuation(valid_out)
    risk_metrics = _portfolio_risk_metrics(nav_data, items)
    suggestions = _generate_suggestions(concentration, correlation, valuation, valid_out, name_map)

    return {
        "funds": out,
        "summary": {
            "total": len(out),
            "passive_count": passive_count,
            "active_count": active_count,
            "avg_percentile": round(avg_pct, 2),
            "portfolio_advice": portfolio_advice,
            "directions": list(set(
                d for o in out for d in o.get("direction", [])
            ))[:5],
        },
        "concentration": concentration,
        "correlation": correlation,
        "valuation_health": valuation,
        "risk_metrics": risk_metrics,
        "suggestions": suggestions,
    }


# ======================================================================
# Analysis Helper Functions
# ======================================================================


def _analyze_concentration(items: List[HoldItem], name_map: dict) -> dict:
    """集中度风险：聚合持仓计算前3/前5占比 + 行业方向重叠。"""
    from services.data import get_full_holdings
    from services.direction import _STOCK_SECTOR

    stock_agg = {}
    sector_funds = {}

    for h in items:
        code = h.code
        try:
            fh = get_full_holdings(code)
        except Exception:
            continue
        holdings = fh.get("持仓", [])
        for s in holdings:
            scode = str(s.get("代码", ""))
            sname = str(s.get("名称", ""))
            spct = float(s.get("占比", 0))
            sector = _STOCK_SECTOR.get(scode, "其他")

            key = scode if scode else sname
            if key not in stock_agg:
                stock_agg[key] = {"total_weight": 0.0, "funds": set(), "sector": sector, "name": sname}
            stock_agg[key]["total_weight"] += spct
            stock_agg[key]["funds"].add(code)

            if sector not in sector_funds:
                sector_funds[sector] = set()
            sector_funds[sector].add(code)

    if not stock_agg:
        return {"top3_pct": 0, "top5_pct": 0, "level": "未知", "overlap_warning": None}

    total = sum(d["total_weight"] for d in stock_agg.values()) or 1.0
    sorted_stocks = sorted(stock_agg.values(), key=lambda x: x["total_weight"], reverse=True)

    top3_pct = sum(s["total_weight"] for s in sorted_stocks[:3]) / total * 100
    top5_pct = sum(s["total_weight"] for s in sorted_stocks[:5]) / total * 100

    if top3_pct > 60:
        level = "高风险"
    elif top3_pct > 30:
        level = "中等"
    else:
        level = "分散"

    overlap_warning = None
    warnings = []
    for sector, fund_codes in sector_funds.items():
        if sector != "其他" and len(fund_codes) >= 2:
            fund_names = [name_map.get(c, c) for c in sorted(fund_codes)]
            warnings.append("{}方向重叠：{}均重仓该板块".format(sector, "、".join(fund_names[:3])))
    if warnings:
        overlap_warning = "；".join(warnings[:2])

    return {"top3_pct": round(top3_pct, 1), "top5_pct": round(top5_pct, 1),
            "level": level, "overlap_warning": overlap_warning}


def _analyze_correlation(nav_data: dict, items: List[HoldItem], name_map: dict) -> dict:
    """相关性分析：基于日收益率计算相关系数矩阵。"""
    import pandas as pd

    return_series = {}
    for h in items:
        code = h.code
        df = nav_data.get(code)
        if df is None or df.empty:
            continue
        nav = df.set_index("date")["nav"]
        rets = nav.pct_change().dropna()
        if len(rets) < 10:
            continue
        return_series[code] = rets

    if len(return_series) < 2:
        return {"avg_correlation": 0, "high_pairs": []}

    ret_df = pd.DataFrame(return_series).dropna()
    if ret_df.shape[1] < 2 or ret_df.shape[0] < 5:
        return {"avg_correlation": 0, "high_pairs": []}

    corr_matrix = ret_df.corr()
    codes = list(corr_matrix.columns)
    n = len(codes)

    triu_sum = 0.0
    triu_count = 0
    high_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            cv = float(corr_matrix.iloc[i, j])
            triu_sum += cv
            triu_count += 1
            if cv > 0.85:
                code_a, code_b = codes[i], codes[j]
                name_a = name_map.get(code_a, code_a)
                name_b = name_map.get(code_b, code_b)
                high_pairs.append({
                    "fund_a": code_a, "fund_b": code_b,
                    "correlation": round(cv, 2),
                    "warning": "{}与{}同涨同跌风险高".format(name_a, name_b),
                })

    avg_corr = triu_sum / triu_count if triu_count > 0 else 0.0
    return {"avg_correlation": round(avg_corr, 2), "high_pairs": high_pairs}


def _analyze_valuation(valid_out: list) -> dict:
    """估值健康度：平均净值分位综合评估。"""
    percentiles = [o.get("percentile") for o in valid_out if o.get("percentile") is not None]
    if not percentiles:
        return {"avg_percentile": 0, "level": "未知", "advice": ""}

    avg_pct = sum(percentiles) / len(percentiles)

    if avg_pct < 0.20:
        level, advice = "极度低估", "整体处于极度低估区间，布局性价比极高，建议分批建仓"
    elif avg_pct < 0.40:
        level, advice = "低估", "整体估值偏低，定投或分批买入的较好时机"
    elif avg_pct < 0.60:
        level, advice = "合理", "整体估值合理，维持现有配置即可"
    elif avg_pct < 0.80:
        level, advice = "偏高", "整体估值偏高，建议等待回调或定投建仓"
    else:
        level, advice = "高估", "整体估值处于高位，建议适当减仓，控制风险"

    return {"avg_percentile": round(avg_pct, 2), "level": level, "advice": advice}


def _portfolio_risk_metrics(nav_data: dict, items: List[HoldItem]) -> dict:
    """组合整体风险指标。"""
    import pandas as pd
    from services.metrics import max_drawdown, annual_volatility, sharpe_ratio

    nav_series = {}
    for h in items:
        code = h.code
        df = nav_data.get(code)
        if df is None or df.empty:
            continue
        nav_series[code] = df.set_index("date")["nav"]

    if len(nav_series) < 1:
        return {"portfolio_volatility": 0, "portfolio_sharpe": 0, "portfolio_max_drawdown": 0}

    nav_df = pd.DataFrame(nav_series).dropna()
    if nav_df.empty or nav_df.shape[1] < 1:
        return {"portfolio_volatility": 0, "portfolio_sharpe": 0, "portfolio_max_drawdown": 0}

    port_nav = nav_df.mean(axis=1)
    port_nav = port_nav / port_nav.iloc[0]
    rets = port_nav.pct_change().dropna()

    if len(rets) < 5:
        return {"portfolio_volatility": 0, "portfolio_sharpe": 0, "portfolio_max_drawdown": 0}

    return {
        "portfolio_volatility": round(annual_volatility(rets), 4),
        "portfolio_sharpe": round(sharpe_ratio(rets), 4),
        "portfolio_max_drawdown": round(max_drawdown(port_nav), 4),
    }


def _generate_suggestions(concentration: dict, correlation: dict, valuation: dict,
                          valid_out: list, name_map: dict) -> list:
    """生成3-5条具体改进建议。"""
    suggestions = []

    if concentration.get("level") == "高风险":
        suggestions.append("前3大持仓占比{}%，集中度过高，建议分散配置降低风险".format(concentration["top3_pct"]))
    elif concentration.get("level") == "中等":
        suggestions.append("前3大持仓占比{}%，集中度中等，可适当关注分散度".format(concentration["top3_pct"]))

    if concentration.get("overlap_warning"):
        suggestions.append(concentration["overlap_warning"])

    for pair in correlation.get("high_pairs", []):
        name_a = name_map.get(pair["fund_a"], pair["fund_a"])
        name_b = name_map.get(pair["fund_b"], pair["fund_b"])
        suggestions.append("{}({})与{}({})相关性{:.2f}，持仓高度重叠，建议只保留一只".format(
            pair["fund_a"], name_a, pair["fund_b"], name_b, pair["correlation"]))

    val = valuation.get("avg_percentile", 0.5)
    if val > 0.80:
        suggestions.append("组合整体处于高估值区间，建议适当降低仓位或等待回调")
    elif val < 0.20:
        suggestions.append("组合整体处于低估值区间，当前是较好的布局时机")

    worst_funds = sorted(
        [o for o in valid_out if o.get("risk", {}).get("sharpe_ratio", 0) is not None],
        key=lambda o: o.get("risk", {}).get("sharpe_ratio", 0) or 0,
    )
    if worst_funds:
        worst = worst_funds[0]
        sharpe_val = worst.get("risk", {}).get("sharpe_ratio", 0)
        if isinstance(sharpe_val, (int, float)) and sharpe_val < 0:
            suggestions.append("{}({})夏普比率{:.2f}，风险调整后收益不佳，建议关注".format(
                worst["code"], worst["name"], sharpe_val))

    all_directions = {}
    for o in valid_out:
        for d in o.get("direction", []):
            if d not in all_directions:
                all_directions[d] = []
            all_directions[d].append(o["name"])
    single_dir_dominance = [
        (d, funds) for d, funds in all_directions.items()
        if len(funds) >= len(valid_out) * 0.5 and len(funds) >= 2
    ]
    if single_dir_dominance and len(suggestions) < 5:
        dir_name, fund_names = single_dir_dominance[0]
        if dir_name not in ["均衡/其他", "暂无数据"]:
            suggestions.append("多只基金集中于{}方向，建议增加不同风格资产分散风险".format(dir_name))

    return suggestions[:5]


# ======================================================================
# Other Endpoints
# ======================================================================


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
    """批量导入：只存库，秒回。前端拿到响应后再调用 /analyze 端点进行分析。"""
    from db import save_holding
    codes = []
    for h in items:
        save_holding(h.code, h.name)
        codes.append(h.code)
    return {"ok": True, "codes": codes, "count": len(codes)}
