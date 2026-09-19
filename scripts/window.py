"""
30 天窗口判断（独立模块，便于单元测试）
"""

from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

CST = timezone(timedelta(hours=8))
WINDOW_DAYS = 30

DATE_REGEX = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")


def parse_date(s: str) -> Optional[datetime]:
    """解析 ISO 或常见日期格式"""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=CST)
        except ValueError:
            continue
    return None


def in_window(d: datetime, now: Optional[datetime] = None) -> bool:
    """日期是否在未来 30 天内（含今天）"""
    now = now or datetime.now(CST)
    if d.tzinfo is None:
        d = d.replace(tzinfo=CST)
    if d < now.replace(hour=0, minute=0, second=0, microsecond=0):
        return False
    return (d - now).days <= WINDOW_DAYS


def extract_dates(text: str) -> List[datetime]:
    """从文本中提取所有形如 2026-09-25 的日期"""
    results = []
    for m in DATE_REGEX.finditer(text or ""):
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=CST)
            results.append(d)
        except ValueError:
            continue
    return results


def urgency_level(days_left: int) -> str:
    """根据剩余天数返回紧急度"""
    if days_left <= 1:
        return "🔴 今天/明天"
    if days_left <= 3:
        return "🔴 3 天内"
    if days_left <= 7:
        return "🟡 一周内"
    if days_left <= 14:
        return "🟢 两周内"
    return "🟢 30 天内"


if __name__ == "__main__":
    # 自检
    import sys
    sys.path.insert(0, ".")
    print(parse_date("2026-09-25"))
    print(extract_dates("考试时间 2026-09-25 至 2026-09-26"))
    d = parse_date("2026-09-25")
    print(urgency_level((d - datetime.now(CST)).days))