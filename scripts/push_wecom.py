"""
企业微信机器人推送

环境变量 WECOM_WEBHOOK: 企业微信自定义机器人 Webhook URL

用法：
  python push_wecom.py             # 推送
  python push_wecom.py --dry-run   # 只打印
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

import requests

sys.path.insert(0, str(Path(__file__).parent))
from window import urgency_level, CST
from datetime import datetime

WEBHOOK_ENV = "WECOM_WEBHOOK"


def build_markdown(events: List[Dict[str, Any]]) -> str:
    """构造企业微信 Markdown 消息"""
    now = datetime.now(CST).strftime("%Y-%m-%d")

    # 分组：职业资格 vs 学历提升
    zi = [e for e in events if e.get("category") == "职业资格"]
    xue = [e for e in events if e.get("category") == "学历提升"]
    other = [e for e in events if e.get("category") not in ("职业资格", "学历提升")]

    sections = [f"### 📅 {now} 考试提醒（30 天窗口）"]

    if zi:
        sections.append("\n#### 🔵 职业资格")
        for e in zi[:20]:
            icon = urgency_level(e["days_left"])
            sections.append(
                f"- {icon} **{e['event_type']}** {e['date']} · {e['exam_name']}"
            )
    if xue:
        sections.append("\n#### 🟢 学历提升")
        for e in xue[:20]:
            icon = urgency_level(e["days_left"])
            sections.append(
                f"- {icon} **{e['event_type']}** {e['date']} · {e['exam_name']}"
            )
    if other:
        sections.append("\n#### ⚪ 其他")
        for e in other[:10]:
            icon = urgency_level(e["days_left"])
            sections.append(
                f"- {icon} **{e['event_type']}** {e['date']} · {e['exam_name']}"
            )

    if not events:
        sections.append("\n_今天无 30 天内考试事件_")

    sections.append("\n\n> 自动推送，仅供参考，以官方公告为准")
    return "\n".join(sections)


def push(events: List[Dict[str, Any]]):
    webhook = os.environ.get(WEBHOOK_ENV, "").strip()
    if not webhook:
        print("ℹ 未配置 WECOM_WEBHOOK，跳过企微推送")
        return False

    md = build_markdown(events)
    body = {
        "msgtype": "markdown",
        "markdown": {"content": md},
    }

    if "--dry-run" in sys.argv:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return True

    try:
        resp = requests.post(webhook, json=body, timeout=10)
        data = resp.json()
        if data.get("errcode") == 0:
            print(f"✓ 企微推送成功 {len(events)} 条")
            return True
        print(f"✗ 企微推送失败: {data}")
        return False
    except Exception as e:
        print(f"✗ 企微推送异常: {e}")
        return False


if __name__ == "__main__":
    sample = [
        {"exam_name": "全国硕士研究生招生考试", "event_type": "预报名开始",
         "date": "2025-09-30", "days_left": 5, "url": "",
         "category": "学历提升"},
        {"exam_name": "中级注册安全工程师", "event_type": "考试日",
         "date": "2026-10-24", "days_left": 25, "url": "",
         "category": "职业资格"},
    ]
    push(sample)