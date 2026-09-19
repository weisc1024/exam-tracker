"""
RSS 抓取 + 30 天窗口判断 + 推送

主入口，由 GitHub Actions daily-fetch.yml 调用。

执行流程：
1. 并发抓取 26 个 RSSHub 源
2. 解析条目，过滤出含考试关键词的
3. 与 data/exams.json 中的人工维护项目做日期匹配
4. 计算 30 天窗口（报名时间 / 考试时间 - 今天 ≤ 30 天）
5. 与上次推送哈希比对去重
6. 调 push_feishu.py / push_wecom.py 双发推送
7. 写入 data/announcements.json 与 data/last_pushed.json
"""

from __future__ import annotations
import sys
import json
import hashlib
import logging
import concurrent.futures
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import feedparser
import requests

# 让脚本既能 python fetch_rss.py 也能 python -m scripts.fetch_rss 运行
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    SOURCES, build_feed_url, DATA_DIR,
    EXAMS_FILE, ANNOUNCEMENTS_FILE, LAST_PUSHED_FILE,
    WINDOW_DAYS, HTTP_TIMEOUT, USER_AGENT,
)

# 北京时区
CST = timezone(timedelta(hours=8))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("exam-tracker")


# ---------- 关键词词典（用于从公告标题筛考试） ----------


KEYWORDS = [
    # 职业资格
    "教师资格", "法律职业资格", "注册会计", "建造师", "造价工程师", "监理工程师",
    "注册安全工程师", "注册消防工程师", "注册计量师", "执业药师", "拍卖师",
    "专利代理师", "导游资格", "演出经纪", "护士执业", "执业兽医",
    "注册建筑师", "注册城乡规划师", "注册测绘师", "核安全", "验船师", "船员资格",
    "注册结构工程师", "注册土木工程师", "新闻记者", "广播电视播音",
    "精算师", "矿业权评估", "环境影响评价", "设备监理师",
    "翻译专业资格", "社会工作者", "经济专业", "会计专业", "资产评估",
    "审计专业", "税务师", "银行业专业", "证券期货", "文物保护",
    "统计专业", "出版专业", "认证人员",
    # 学历提升
    "高考", "成人高考", "研究生", "考研", "硕士", "博士",
    "自学考试", "自考", "教师资格考试", "NTCE",
    "四六级", "CET", "计算机等级", "NCRE", "PETS", "英语等级",
    "同等学力",
]


# ---------- 抓取函数 ----------


def fetch_one(source) -> List[Dict[str, Any]]:
    """抓取单个 RSS 源并解析条目"""
    url = build_feed_url(source.route)
    try:
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"✗ {source.id} 抓取失败: {e}")
        return []

    parsed = feedparser.parse(resp.content)
    items: List[Dict[str, Any]] = []
    for entry in parsed.entries[:30]:  # 每个源最多取 30 条
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        published = entry.get("published", "") or entry.get("updated", "")
        if not title or not link:
            continue
        items.append({
            "source_id": source.id,
            "source_title": source.title,
            "category": source.category,
            "title": title,
            "link": link,
            "published": published,
            "summary": entry.get("summary", "")[:300],
        })
    log.info(f"✓ {source.id} 抓到 {len(items)} 条")
    return items


def fetch_all() -> List[Dict[str, Any]]:
    """并发抓取所有源"""
    log.info(f"开始抓取 {len(SOURCES)} 个源")
    all_items: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, src): src for src in SOURCES}
        for fut in concurrent.futures.as_completed(futures):
            try:
                all_items.extend(fut.result())
            except Exception as e:
                log.error(f"并发抓取异常: {e}")
    log.info(f"总计 {len(all_items)} 条原始条目")
    return all_items


# ---------- 关键词过滤 ----------


def match_keywords(title: str) -> bool:
    """标题包含任一关键词则匹配"""
    return any(kw in title for kw in KEYWORDS)


def filter_relevant(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤出与考试相关的条目"""
    return [it for it in items if match_keywords(it["title"])]


# ---------- 日期解析 ----------


def parse_iso_date(s: str):
    """解析 YYYY-MM-DD 或类似格式"""
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=CST)
        except (ValueError, TypeError):
            pass
    return None


def extract_dates_from_text(text: str) -> List[datetime]:
    """从文本中提取所有形如 2026-09-25 的日期"""
    import re
    results: List[datetime] = []
    for m in re.finditer(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text):
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=CST)
            results.append(d)
        except ValueError:
            continue
    return results


# ---------- 30 天窗口判断 ----------


def in_window(d: datetime, now: datetime) -> bool:
    """判断日期是否在 30 天窗口内（已过的不算）"""
    if d < now:
        return False
    return (d - now).days <= WINDOW_DAYS


def pick_window_events(items: List[Dict[str, Any]], exams: List[Dict[str, Any]]
                        ) -> List[Dict[str, Any]]:
    """
    从公告 + exams.json 中挑出 30 天内的事件
    返回统一结构的事件列表
    """
    now = datetime.now(CST)
    events: List[Dict[str, Any]] = []

    # 1. 从人工维护的 exams.json 取
    for ex in exams:
        for field, kind in (("register_start", "报名开始"),
                            ("register_end", "报名截止"),
                            ("exam_date", "考试日")):
            d = parse_iso_date(ex.get(field, ""))
            if d and in_window(d, now):
                events.append({
                    "exam_id": ex.get("id"),
                    "exam_name": ex.get("name"),
                    "category": ex.get("category", "其他"),
                    "event_type": kind,
                    "date": d.strftime("%Y-%m-%d"),
                    "days_left": (d - now).days,
                    "url": ex.get("url", ""),
                    "source": "exams.json",
                })

    # 2. 从公告条目中抓日期（兜底）
    seen_keys = {(e["exam_name"], e["event_type"], e["date"]) for e in events}
    for it in items:
        # 找最近的相关考试名
        exam_name = ""
        for kw in KEYWORDS:
            if kw in it["title"]:
                exam_name = kw
                break
        if not exam_name:
            continue
        for d in extract_dates_from_text(it["title"] + " " + it.get("summary", "")):
            if not in_window(d, now):
                continue
            key = (exam_name, "公告提及", d.strftime("%Y-%m-%d"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            events.append({
                "exam_id": "",
                "exam_name": exam_name,
                "category": it.get("category", "其他"),
                "event_type": "公告提及",
                "date": d.strftime("%Y-%m-%d"),
                "days_left": (d - now).days,
                "url": it["link"],
                "source": it["source_id"],
            })

    events.sort(key=lambda e: (e["days_left"], e["exam_name"]))
    return events


# ---------- 去重推送 ----------


def load_last_pushed() -> set:
    if not Path(LAST_PUSHED_FILE).exists():
        return set()
    try:
        return set(json.loads(Path(LAST_PUSHED_FILE).read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def save_last_pushed(hashes: set):
    Path(LAST_PUSHED_FILE).write_text(json.dumps(sorted(hashes), ensure_ascii=False, indent=2))


def event_hash(e: Dict[str, Any]) -> str:
    """事件唯一哈希"""
    s = f"{e['exam_name']}|{e['event_type']}|{e['date']}|{e['url']}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def filter_unpushed(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤已推送过的"""
    last = load_last_pushed()
    fresh = [e for e in events if event_hash(e) not in last]
    log.info(f"事件 {len(events)} 条，去重后 {len(fresh)} 条新事件")
    return fresh


# ---------- 数据持久化 ----------


def load_exams() -> List[Dict[str, Any]]:
    if not Path(EXAMS_FILE).exists():
        return []
    try:
        return json.loads(Path(EXAMS_FILE).read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_announcements(items: List[Dict[str, Any]]):
    payload = {
        "updated_at": datetime.now(CST).isoformat(),
        "count": len(items),
        "items": items,
    }
    Path(ANNOUNCEMENTS_FILE).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
    )


# ---------- 推送 ----------


def push_events(events: List[Dict[str, Any]]):
    """调飞书 + 企微 双发"""
    if not events:
        log.info("无新事件，跳过推送")
        return
    # 延迟导入避免本地无 requests 时影响其它功能
    from push_feishu import push as push_feishu
    from push_wecom import push as push_wecom

    try:
        push_feishu(events)
    except Exception as e:
        log.exception(f"飞书推送失败: {e}")

    try:
        push_wecom(events)
    except Exception as e:
        log.exception(f"企微推送失败: {e}")

    # 记录已推送
    last = load_last_pushed()
    for e in events:
        last.add(event_hash(e))
    save_last_pushed(last)


# ---------- 主入口 ----------


def main():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    raw_items = fetch_all()
    relevant = filter_relevant(raw_items)
    save_announcements(relevant)

    exams = load_exams()
    events = pick_window_events(relevant, exams)
    log.info(f"30天窗口内事件: {len(events)} 条")

    fresh = filter_unpushed(events)
    push_events(fresh)

    log.info("✓ 本次任务完成")


if __name__ == "__main__":
    main()