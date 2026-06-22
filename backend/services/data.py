"""akshare 数据封装 + 统一缓存 + 天天基金 HTML 抓取 (FundCrawler 模式)"""
import re
import urllib.request
import json
from typing import Optional
import akshare as ak
import pandas as pd
from cache import cached

# ── 天天基金 HTML 抓取工具 (FundCrawler 模式) ──────────────────

_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_REFERER = "http://fund.eastmoney.com/"
_NUMBER_RE = r'-?(\d+?(,\d+)*?(\.\d+)?)'


def _fetch_html(url: str, timeout: int = 8) -> Optional[str]:
    """抓取 HTML 页面，失败返回 None。"""
    try:
        req = urllib.request.Request(url, headers={
            "Referer": _REFERER, "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


@cached(ttl=86400)
def get_fund_direction(code: str) -> list:
    """获取基金投资方向（基于持仓关键词，复用 get_full_holdings 缓存）。"""
    try:
        holdings_data = get_full_holdings(code)
        holdings = holdings_data.get("持仓", [])
        if not holdings:
            return ["暂无数据"]
        names = " ".join(h.get("名称", "") for h in holdings[:10])
        tags = {
            "CPO/光模块": ["中际旭创","新易盛","天孚通信","光库科技","源杰科技"],
            "AI算力": ["寒武纪","海光信息","浪潮信息","中科曙光","工业富联"],
            "半导体": ["中芯国际","北方华创","韦尔股份","兆易创新","卓胜微"],
            "新能源": ["宁德时代","比亚迪","隆基绿能","阳光电源","亿纬锂能"],
            "消费": ["贵州茅台","五粮液","伊利股份","海天味业","美的集团"],
            "医药": ["药明康德","恒瑞医药","迈瑞医疗","片仔癀","百济神州"],
            "金融": ["中国平安","招商银行","工商银行","中信证券","东方财富"],
            "互联网": ["腾讯","美团","阿里巴巴","京东","拼多多","百度"],
            "美股科技": ["苹果","微软","英伟达","谷歌","亚马逊","Meta","特斯拉"],
        }
        directions = []
        for direction, keywords in tags.items():
            if any(kw in names for kw in keywords):
                directions.append(direction)
        return directions if directions else ["均衡/其他"]
    except Exception:
        return ["暂无数据"]

@cached(ttl=3600)
def get_nav(code: str) -> pd.DataFrame:
    """获取基金单位净值走势。"""
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        cols = ["date","nav","acc_nav","growth"][:len(df.columns)]
        df.columns = cols
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        return df.dropna(subset=["nav"])
    except Exception:
        return pd.DataFrame(columns=["date","nav"])

@cached(ttl=86400)
def get_rank() -> pd.DataFrame:
    """基金业绩排行。"""
    try:
        return ak.fund_open_fund_rank_em(symbol="全部")
    except Exception:
        return pd.DataFrame()

# 分类排名缓存
_CAT_RANK_CACHE = {}
_CAT_RANK_CACHE_TIME = {}

def _get_category_rank(category: str):
    """获取某分类的排名数据（缓存1小时）。"""
    import time
    now = time.time()
    if category in _CAT_RANK_CACHE and (now - _CAT_RANK_CACHE_TIME.get(category, 0)) < 3600:
        return _CAT_RANK_CACHE[category]
    try:
        df = ak.fund_open_fund_rank_em(symbol=category)
        _CAT_RANK_CACHE[category] = df
        _CAT_RANK_CACHE_TIME[category] = now
        return df
    except Exception:
        return pd.DataFrame()


@cached(ttl=3600)
def get_short_term_perf(code: str) -> dict:
    """获取短期行情：日增长率、近1周、近1月、同类排名（分类内排名）。

    排名策略：
    1) 优先将 fund_type（如"混合型-偏股"）直接作为 akshare symbol
    2) 若 akshare 不支持子分类，退回到宽泛分类
    3) 退回时按"近1月"收益率排序计算 rank_pct，使排名有意义
    """
    overview = get_fund_overview(code)
    fund_type = overview.get("fund_type", "")

    # Step 1: 尝试直接用 fund_type 作为 akshare symbol（如"混合型-偏股"）
    df = _get_category_rank(fund_type) if fund_type else pd.DataFrame()
    category = fund_type

    # Step 2: 退回 — 映射到 akshare 支持的宽泛分类
    if df.empty:
        _CATEGORY_MAP = [
            (["QDII"], "QDII"),
            (["FOF"], "FOF"),
            (["货币"], "货币型"),
            (["债券"], "债券型"),
            (["指数"], "指数型"),
            (["股票"], "股票型"),
            (["混合"], "混合型"),
        ]
        category = ""
        for keywords, sym in _CATEGORY_MAP:
            if any(kw in fund_type for kw in keywords):
                category = sym
                break
        if category:
            df = _get_category_rank(category)

    if df.empty:
        # 不拉全市场，只返回收益数据不包含排名
        try:
            all_df = get_rank()
            match = all_df[all_df["基金代码"].astype(str) == str(code)]
            if not match.empty:
                row = match.iloc[0]
                return {
                    "rank": 0, "daily": str(row.get("日增长率", "")),
                    "week_1": str(row.get("近1周", "")), "month_1": str(row.get("近1月", "")),
                    "month_3": str(row.get("近3月", "")), "nav": str(row.get("单位净值", "")),
                    "total_funds": 0, "category": "未知", "rank_pct": 0,
                }
        except:
            pass
        return {}

    try:
        match = df[df["基金代码"].astype(str) == str(code)]
        if match.empty:
            return {}
        row = match.iloc[0]

        # 若直接用 fund_type 成功，"序号"就是子分类内排名
        if category == fund_type:
            rank = int(row.get("序号", 0))
            total = int(len(df))
            rank_pct = round(rank / max(total, 1) * 100, 1)
        else:
            # 退回：按"近1月"收益率排序计算排名（比"序号"更有意义）
            sort_col = "近1月"
            if sort_col not in df.columns:
                sort_col = "日增长率"
            df_sorted = df.copy()
            df_sorted[sort_col] = pd.to_numeric(df_sorted[sort_col], errors="coerce")
            df_sorted = df_sorted.sort_values(sort_col, ascending=False).reset_index(drop=True)
            positions = df_sorted[df_sorted["基金代码"].astype(str) == str(code)].index.tolist()
            rank = positions[0] + 1 if positions else 0
            total = int(len(df_sorted))
            rank_pct = round(rank / max(total, 1) * 100, 1)

        return {
            "rank": rank,
            "daily": str(row.get("日增长率", "")),
            "week_1": str(row.get("近1周", "")),
            "month_1": str(row.get("近1月", "")),
            "month_3": str(row.get("近3月", "")),
            "nav": str(row.get("单位净值", "")),
            "total_funds": total,
            "category": category,
            "rank_pct": rank_pct,
        }
    except Exception:
        return {}

@cached(ttl=86400)
def get_all_funds() -> pd.DataFrame:
    """全市场基金列表。"""
    try:
        return ak.fund_name_em()
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_fund_name(code: str) -> str:
    """获取基金名称（多源回退）。"""
    # Source 1: akshare
    try:
        df = get_all_funds()
        if not df.empty:
            match = df[df["基金代码"].astype(str) == str(code)]
            if not match.empty:
                return str(match.iloc[0]["基金简称"])
    except: pass

    # Source 2: pingzhongdata JS
    try:
        import urllib.request, re
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        req = urllib.request.Request(url, headers={"Referer":"http://fund.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8","replace")
        m = re.search(r'fS_name\s*=\s*"([^"]+)"', text)
        if m: return m.group(1)
    except: pass

    # Source 3: realtime API
    try:
        import urllib.request, re, json
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={"Referer":"http://fund.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8","replace")
        m = re.search(r'jsonpgz\((\{.*\})\)', text)
        if m:
            data = json.loads(m.group(1))
            return data.get("name", code)
    except: pass

    return code

@cached(ttl=86400)
def get_fund_info(code: str) -> dict:
    """基金基本信息(雪球)。"""
    try:
        return ak.fund_individual_basic_info_xq(symbol=code)
    except Exception:
        return {}

@cached(ttl=86400)
def get_manager() -> pd.DataFrame:
    """基金经理信息。"""
    try:
        return ak.fund_manager_em()
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_index_daily(code: str) -> pd.DataFrame:
    """指数日线。code='sh000300'=沪深300"""
    try:
        return ak.stock_zh_index_daily(symbol=code)
    except Exception:
        return pd.DataFrame()


def classify_market(stock_code: str, stock_name: str) -> str:
    """分层规则判断股票所属市场。"""
    import re
    code = str(stock_code).strip().upper()
    name = str(stock_name)
    if code.isdigit():
        if len(code) == 6: return "A股"
        if len(code) == 5: return "港股"
    if re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", code): return "美股"
    US_NAMES = {"苹果","微软","英伟达","谷歌","亚马逊","Meta","特斯拉","台积电","博通",
                "Apple","Microsoft","NVIDIA","Amazon","Tesla","Netflix","AMD"}
    if any(k in name for k in US_NAMES): return "美股"
    OVERSEAS_KW = {"越南":"越南","印度":"印度","日经":"日本","日本":"日本",
                   "德国":"德国","纳斯达克":"美股","标普":"美股","恒生":"港股"}
    for kw, region in OVERSEAS_KW.items():
        if kw in name: return region
    if name.endswith("-W") or name.endswith("-S") or "-SW" in name: return "港股"
    return "其他"

@cached(ttl=86400)
def get_full_holdings(code: str) -> dict:
    """获取基金全部持仓 + 地域分布比例。"""
    try:
        from datetime import datetime
        current_year = datetime.now().year
        df = None
        for y in (current_year, current_year - 1):
            try:
                df = ak.fund_portfolio_hold_em(symbol=code, date=str(y))
                if df is not None and not df.empty:
                    break
            except Exception:
                continue
        if df is None or df.empty:
            return {"holdings": [], "region_breakdown": {}}

        # 取最新季度数据
        latest_quarter = df["季度"].iloc[0]
        latest = df[df["季度"] == latest_quarter].copy()

        holdings = []
        region_pct = {"A股": 0.0, "港股": 0.0, "美股": 0.0, "日本": 0.0, "越南": 0.0, "印度": 0.0, "德国": 0.0, "其他": 0.0}

        for _, row in latest.iterrows():
            stock_code = str(row.get("股票代码", ""))
            stock_name = str(row.get("股票名称", ""))
            pct = float(row.get("占净值比例", 0))

            # 判断市场
            market = classify_market(stock_code, stock_name)

            holdings.append({
                "代码": stock_code,
                "名称": stock_name,
                "占比": round(pct, 2),
                "市场": market,
            })
            region_pct[market] += pct

        # 四舍五入
        for k in region_pct:
            region_pct[k] = round(region_pct[k], 2)

        return {
            "季度": latest_quarter,
            "持仓": holdings,
            "地域分布": region_pct,
            "总占比": round(sum(r["占比"] for r in holdings), 2),
        }
    except Exception:
        return {"持仓": [], "地域分布": {}, "总占比": 0, "季度": ""}


# ── FundCrawler 模式：天天基金 HTML 页面抓取 ────────────────────

@cached(ttl=86400)
def get_fund_overview(code: str) -> dict:
    """基金基本概况（天天基金 jbgk 页面 HTML 抓取）。
    返回：fund_type, fund_size(亿), fund_company, fund_value, 三项费率
    基于 Jerry1014/FundCrawler 的 tiantian.py 解析模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/jbgk_{code}.html")
    if not html:
        return {}

    result = {}

    # 基金类型
    if m := re.search(r'基金类型</th><td>(.*?)</td></tr><tr><th>发行日期', html):
        result["fund_type"] = m.group(1)

    # 资产规模（亿）
    if m := re.search(fr'(?:净\s*)?资产规模</th><td>(---|{_NUMBER_RE}亿)', html):
        raw = m.group(1)
        if raw != '---':
            result["fund_size"] = raw[:-1].replace(',', '')

    # 基金管理人
    if m := re.search(r'基金管理人</th><td><a.*?">(.+?)</a></td><th>基金托管人', html):
        result["fund_company"] = m.group(1)

    # 单位净值
    if m := re.search(fr'单位净值.*?：[\s\S]*?({_NUMBER_RE})\s', html):
        result["fund_value"] = m.group(1)

    # 管理费率
    if m := re.search(fr'管理费率</th><td>(({_NUMBER_RE})%|---|<a)', html):
        val = m.group(1)
        if val != '<a':
            result["management_fee"] = '--' if val == '---' else val

    # 托管费率
    if m := re.search(fr'托管费率</th><td>(({_NUMBER_RE})%|---)', html):
        val = m.group(1)
        result["custody_fee"] = '--' if val == '---' else val

    # 销售服务费率
    if m := re.search(fr'销售服务费率</th><td>(({_NUMBER_RE})%|---)', html):
        val = m.group(1)
        result["sales_service_fee"] = '--' if val == '---' else val

    return result


@cached(ttl=86400)
def get_fund_manager_info(code: str) -> dict:
    """基金经理信息（天天基金 jjjl 页面 HTML 抓取）。
    基于 Jerry1014/FundCrawler 的 tiantian.py parse_manager 模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/jjjl_{code}.html")
    if not html:
        return {}

    result = {}
    if m := re.search(r'现任基金经理简介[\s\S]+?姓名：[\s\S]+?<a.+?>(.+?)</a>', html):
        result["manager_name"] = m.group(1)
    if m := re.search(r'现任基金经理简介[\s\S]+?上任日期：[\s\S]+?>(.+?)</p>', html):
        result["appointment_date"] = m.group(1)

    return result


@cached(ttl=86400)
def get_fund_risk_data(code: str) -> dict:
    """基金风险数据（天天基金 tsdata 页面 HTML 抓取）。
    返回：近3年标准差、近3年夏普比率
    基于 Jerry1014/FundCrawler 的 tiantian.py parse_tsdata 模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/tsdata_{code}.html")
    if not html:
        return {}

    result = {}
    # 近3年标准差（定位"标准差"行 → 第3个td）
    if m := re.search(
        r'<td>标准差</td><td[^>]*>.*?</td><td[^>]*>.*?</td><td[^>]*>(.*?)</td>', html
    ):
        val = m.group(1)
        result["stddev_3y"] = val if val and val != '--' else None

    # 近3年夏普比率
    if m := re.search(
        r'<td>夏普比率</td><td[^>]*>.*?</td><td[^>]*>.*?</td><td[^>]*>(.*?)</td>', html
    ):
        val = m.group(1)
        result["sharpe_3y"] = val if val and val != '--' else None

    return result


@cached(ttl=86400)
def get_fund_enriched(code: str) -> dict:
    """聚合多源基金数据：akshare + 天天基金 HTML + pingzhongdata。
    从 FundCrawler 模式整合：基本信息 + 基金经理 + 风险指标。
    """
    result = {"code": code}

    # akshare 基本信息
    try:
        info = get_fund_info(code) or {}
        result["name"] = info.get("基金简称", "")
    except Exception:
        pass

    # FundCrawler 模式：天天基金 HTML
    overview = get_fund_overview(code)
    manager = get_fund_manager_info(code)
    risk = get_fund_risk_data(code)

    result.update({f"tt_{k}": v for k, v in overview.items()})
    result.update({f"tt_{k}": v for k, v in manager.items()})
    result.update({f"tt_{k}": v for k, v in risk.items()})

    return result
