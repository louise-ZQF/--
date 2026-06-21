"""基金投资方向识别：从天天基金抓取持仓 + QDII名称推断。"""
import re
import urllib.request
from typing import List

# Stock code → sector mapping
_STOCK_SECTOR = {
    "300502":"CPO/光通信","300308":"CPO/光通信","300394":"CPO/光通信","300620":"CPO/光通信",
    "688498":"CPO/光通信","002281":"CPO/光通信","300570":"CPO/光通信","688205":"CPO/光通信",
    "688256":"AI算力/芯片","688041":"AI算力/芯片","603019":"AI算力/芯片","000977":"AI算力/芯片",
    "002230":"AI算力/芯片","688111":"AI算力/芯片","300474":"AI算力/芯片","002384":"AI算力/芯片",
    "688981":"半导体","002371":"半导体","603501":"半导体","688012":"半导体","688396":"半导体",
    "300782":"半导体","603986":"半导体","688008":"半导体",
    "300750":"新能源/储能","601012":"新能源/储能","300274":"新能源/储能","688390":"新能源/储能",
    "300014":"新能源/储能","002459":"新能源/储能","688599":"新能源/储能","301377":"新能源/储能",
    "600519":"消费/白酒","000858":"消费/白酒","600887":"消费/白酒","000568":"消费/白酒",
    "603259":"医药/创新药","600276":"医药/创新药","300760":"医药/创新药","300015":"医药/创新药",
    "601318":"金融/银行","600036":"金融/银行","600030":"金融/银行","300059":"金融/银行",
    "002594":"汽车/新能源","601633":"汽车/新能源","000625":"汽车/新能源","601238":"汽车/新能源",
    "600760":"军工/航天","600893":"军工/航天","002013":"军工/航天","600372":"军工/航天",
    "300124":"机器人/自动化","002747":"机器人/自动化","688017":"机器人/自动化",
    "688169":"机器人/自动化","300024":"机器人/自动化",
    "600487":"通信/5G","601869":"通信/5G","600522":"通信/5G","000063":"通信/5G",
    "002415":"互联网/安防","300033":"互联网/金融","002236":"互联网/安防",
}

_QDII_DIRECTION = [
    (["纳斯达克","NASDAQ","纳指"], "纳斯达克100"),
    (["标普","S&P","SP500","标普500"], "标普500"),
    (["道琼斯","道指"], "道琼斯"),
    (["费城半导体","SOX"], "费城半导体/芯片"),
    (["全球科技","科技互联"], "全球科技股"),
    (["全球成长","全球精选","全球产业","全球优质"], "全球成长股"),
    (["新兴市场","新兴"], "新兴市场"),
    (["高端制造","先进制造","智能制造"], "高端制造"),
    (["全球医疗","医药","健康"], "全球医疗"),
    (["全球消费"], "全球消费"),
    (["房地产","REIT"], "全球REITs"),
    (["越南"], "越南市场"),
    (["印度"], "印度市场"),
    (["日本","日经"], "日本股票"),
    (["黄金","贵金属"], "黄金/贵金属"),
    (["原油","油气","能源"], "能源/油气"),
    (["债券","纯债","国债"], "债券"),
]


def get_fund_direction(code: str) -> List[str]:
    """获取基金投资方向标签。"""
    stock_codes, fund_name = _scrape_stock_codes(code)
    directions = []
    seen = set()

    for sc in stock_codes:
        sector = _STOCK_SECTOR.get(sc)
        if sector and sector not in seen:
            directions.append(sector)
            seen.add(sector)

    # QDII fallback: use fund name
    if not directions and fund_name:
        name_upper = fund_name.upper()
        for keywords, tag in _QDII_DIRECTION:
            if any(kw in name_upper for kw in keywords):
                if tag not in seen:
                    directions.append(tag)
                    seen.add(tag)

    return directions[:3] if directions else ["均衡/其他"]


def _scrape_stock_codes(code: str):
    """从天天基金 pingzhongdata 抓取前十大重仓股代码 + 基金名。"""
    try:
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        req = urllib.request.Request(url, headers={
            "Referer": "http://fund.eastmoney.com/",
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="replace")

        m = re.search(r'stockCodes\s*=\s*\[(.*?)\]', text)
        codes = []
        if m:
            raw = m.group(1).replace('"', '').strip()
            for item in raw.split(","):
                item = item.strip().strip('"')
                if len(item) >= 7:
                    codes.append(item[:-1])  # Remove exchange suffix
                elif len(item) == 6:
                    codes.append(item)

        name_m = re.search(r'fS_name\s*=\s*"([^"]+)"', text)
        fund_name = name_m.group(1) if name_m else ""
        return codes[:10], fund_name
    except Exception:
        return [], ""
