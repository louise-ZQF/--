import pandas as pd
from services.data import get_rank, get_nav
from services.metrics import max_drawdown, nav_percentile

def screen_4433():
    df = get_rank()
    if df.empty:
        return []
    cols = {"近1年":"y1","近2年":"y2","近3年":"y3","今年来":"ytd","近6月":"m6","近3月":"m3"}
    for raw, key in cols.items():
        if raw in df.columns:
            df[key] = pd.to_numeric(df[raw], errors="coerce")
    def top(series, frac):
        return series >= series.quantile(1 - frac)
    try:
        mask = (top(df["y1"],0.25) & top(df["y2"],0.25) & top(df["y3"],0.25) &
                top(df["ytd"],0.25) & top(df["m6"],1/3) & top(df["m3"],1/3))
        keep = ["基金代码","基金简称","y1","y2","y3","m6","m3"]
        keep = [c for c in keep if c in df.columns]
        return df[mask][keep].head(50).to_dict(orient="records")
    except Exception:
        return []

def score_fund(code: str) -> dict:
    df = get_nav(code)
    if df.empty:
        return {"code": code, "error": "无净值数据"}
    nav = df["nav"]
    pct = nav_percentile(nav)
    mdd = max_drawdown(nav.tail(252))
    s_elastic = round((1 - pct) * 20, 1)
    s_dd = round(max(0, (1 + mdd / 0.5)) * 15, 1)
    total = round(40 + s_elastic + s_dd, 1)
    rating = "契合" if total >= 70 else ("中性" if total >= 50 else "不契合")
    return {"code":code,"score":total,"rating":rating,
            "detail":{"低位弹性":s_elastic,"回撤控制":s_dd,"净值分位":round(pct,2),"最大回撤":round(mdd,2)}}

def classify_region_by_name(name: str, code: str = "") -> str:
    """根据基金名称分类地区。"""
    n = name.upper()
    if any(kw in n for kw in ["QDII", "海外", "全球", "纳斯达克", "标普", "道琼斯", "费城"]):
        if "港股" in name or "恒生" in name or "香港" in name:
            return "hk"
        if "日本" in name or "日经" in name or "东京" in name:
            return "jp"
        if "韩国" in name or "韩国" in name:
            return "kr"
        return "us"
    if "港股" in name or "恒生" in name or "香港" in name:
        return "hk"
    return "cn"

def region_label(region: str) -> str:
    return {"cn":"A股","hk":"港股","us":"美股","jp":"日本","kr":"韩国","overseas":"海外","all":"全部"}.get(region, region)

def screen_4433_by_region(region: str = "all"):
    """按地区筛选：先分地区，再在各地区内做4433。"""
    from services.data import get_rank
    df = get_rank()
    if df is None or df.empty:
        return []

    # 先给每只基金打上地区标签
    names = df["基金简称"] if "基金简称" in df.columns else df.get("name", [])
    df["_region"] = [classify_region_by_name(str(n)) for n in names]
    df["_region_label"] = [region_label(r) for r in df["_region"]]

    # 按地区过滤
    if region == "china":
        df = df.copy()[ df["_region"].isin(["cn", "hk"])]
    elif region == "overseas":
        df = df.copy()[ df["_region"].isin(["us", "jp", "kr", "hk"])]
    elif region != "all":
        df = df.copy()[ df["_region"] == region]

    if df.empty:
        return []

    # 在地区内部做 4433 筛选
    cols = {"近1年": "y1", "近2年": "y2", "近3年": "y3", "今年来": "ytd", "近6月": "m6", "近3月": "m3"}
    for raw, key in cols.items():
        if raw in df.columns:
            df[key] = pd.to_numeric(df[raw], errors="coerce")

    def top(series, frac):
        return series >= series.quantile(1 - frac)

    try:
        mask = (top(df["y1"], 0.25) & top(df["y2"], 0.25) & top(df["y3"], 0.25) &
                top(df["ytd"], 0.25) & top(df["m6"], 1 / 3) & top(df["m3"], 1 / 3))
        keep = ["基金代码", "基金简称", "y1", "y2", "y3", "m6", "m3", "_region", "_region_label"]
        keep = [c for c in keep if c in df.columns]
        result = df[mask][keep].head(50).to_dict(orient="records")
        # Rename _region fields
        for r in result:
            r["region"] = r.pop("_region", "")
            r["region_label"] = r.pop("_region_label", "")
        return result
    except Exception:
        return []

from services.direction import get_fund_direction


def _old_get_fund_direction(code: str) -> list:
    """获取基金投资方向标签。"""
    try:
        import akshare as ak
        holdings = ak.fund_portfolio_hold_em(symbol=code, date="2025")
        if holdings is None or holdings.empty:
            return ["暂无持仓数据"]
        names = " ".join(holdings["股票名称"].astype(str).tolist()[:15])
        tags = {
            "CPO/光通信": ["中际旭创","新易盛","天孚通信","光库科技","源杰科技","光迅科技","华工科技"],
            "AI算力/芯片": ["寒武纪","海光信息","浪潮信息","中科曙光","工业富联","景嘉微","芯原股份"],
            "半导体": ["中芯国际","北方华创","韦尔股份","兆易创新","卓胜微","圣邦股份","斯达半导"],
            "新能源/储能": ["宁德时代","比亚迪","隆基绿能","阳光电源","亿纬锂能","国轩高科","赣锋锂业"],
            "消费/白酒": ["贵州茅台","五粮液","伊利股份","海天味业","美的集团","格力电器","泸州老窖"],
            "医药/创新药": ["药明康德","恒瑞医药","迈瑞医疗","片仔癀","百济神州","康龙化成","泰格医药"],
            "金融/银行": ["中国平安","招商银行","工商银行","中信证券","东方财富","建设银行","兴业银行"],
            "互联网/平台": ["腾讯","美团","阿里巴巴","京东","拼多多","百度","网易","快手","B站"],
            "美股科技七巨头": ["苹果","微软","英伟达","谷歌","亚马逊","Meta","特斯拉","NVIDIA","Apple","Microsoft"],
            "汽车/自动驾驶": ["比亚迪","长城汽车","吉利汽车","小鹏汽车","理想汽车","蔚来"],
            "机器人/自动化": ["汇川技术","埃斯顿","绿的谐波","拓普集团","三花智控"],
            "军工/航天": ["中航沈飞","航发动力","中国船舶","中航光电","航天电器"],
        }
        directions = []
        for d, keywords in tags.items():
            if any(kw.lower() in names.lower() for kw in keywords):
                directions.append(d)
        return directions[:3] if directions else ["均衡配置"]
    except Exception:
        return ["暂无数据"]
