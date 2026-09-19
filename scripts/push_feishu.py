"""
飞书机器人推送

环境变量 FEISHU_WEBHOOK: 飞书自定义机器人 Webhook URL
环境变量 FEISHU_SECRET (可选): 加签密钥

用法：
  python push_feishu.py            # 推送
  python push_feishu.py --dry-run  # 只打印，不推送
"""

from __future__ import annotations
import os
import sys
import json
import hashlib
import base64
import hmac
import time
from pathlib import Path
from typing import List, Dict, Any

import requests

sys.path.insert(0, str(Path(__file__).parent))
from window import urgency_level, CST
from datetime import datetime

WEBHOOK_ENV = "FEISHU_WEBHOOK"
SECRET_ENV = "FEISHU_SECRET"


def sign(secret: str, timestamp: str) -> str:
    """飞书加签算法"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def build_card(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构造飞书交互式卡片"""
    now = datetime.now(CST).strftime("%Y-%m-%d")
    lines = []
    for e in events[:30]:  # 防止超长
        icon = urgency_level(e["days_left"])
        url = e.get("url", "")
        title = e["exam_name"]
        if url:
            title = f"[{title}]({url})"
        line = f"- {icon} **{e['event_type']}** {e['date']} · {title}"
        lines.append(line)

    body_md = "\n".join(lines) if lines else "_今天无 30 天内考试事件_"

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📅 {now} 考试提醒",
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": body_md,
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "由 exam-tracker 自动推送，仅供参考，请以官方公告为准。",
                        }
                    ],
                },
            ],
        },
    }
    return card


def push(events: List[Dict[str, Any]]):
    webhook = os.environ.get(WEBHOOK_ENV, "").strip()
    if not webhook:
        print("ℹ 未配置 FEISHU_WEBHOOK，跳过飞书推送")
        return False

    if "--dry-run" in sys.argv:
        print(json.dumps(build_card(events), ensure_ascii=False, indent=2))
        return True

    timestamp = str(round(time.time()))
    card = build_card(events)
    body = {"timestamp": timestamp}
    body.update(card)

    secret = os.environ.get(SECRET_ENV, "").strip()
    if secret:
        body["sign"] = sign(secret, timestamp)

    try:
        resp = requests.post(webhook, json=body, timeout=10)
        data = resp.json()
        if data.get("StatusCode") == 0 or data.get("code") == 0:
            print(f"✓ 飞书推送成功 {len(events)} 条")
            return True
        print(f"✗ 飞书推送失败: {data}")
        return False
    except Exception as e:
        print(f"✗ 飞书推送异常: {e}")
        return False


if __name__ == "__main__":
    # 支持单独调用做测试
    sample = [
        {"exam_name": "一级造价工程师", "event_type": "报名截止",
         "date": "2026-09-25", "days_left": 6, "url": "https://example.com",
         "category": "职业资格"},
        {"exam_name": "法律职业资格（主观题）", "event_type": "报名截止",
         "date": "2026-09-30", "days_left": 11, "url": "",
         "category": "职业资格"},
    ]
    push(sample)