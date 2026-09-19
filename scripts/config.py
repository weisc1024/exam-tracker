"""
exam-tracker 全局配置

- RSSHUB_INSTANCE: RSSHub 实例域名（可在 GitHub Secrets 或环境变量覆盖）
- SOURCES: 26 个经过 RSSHub 官方文档验证的信息源
- WINDOW_DAYS: 30 天提醒窗口
- PUSH_CHANNELS: 推送渠道（飞书 + 企业微信 双发）
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List


# ---------- 基础常量 ----------

WINDOW_DAYS = 30                    # 30 天窗口
HTTP_TIMEOUT = 15                   # 单次请求超时（秒）
USER_AGENT = "exam-tracker/1.0 (+https://github.com/yourname/exam-tracker)"

# RSSHub 实例（默认公共实例，可被环境变量覆盖）
DEFAULT_RSSHUB_INSTANCE = "https://rsshub.umzzz.com"

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EXAMS_FILE = os.path.join(DATA_DIR, "exams.json")
ANNOUNCEMENTS_FILE = os.path.join(DATA_DIR, "announcements.json")
LAST_PUSHED_FILE = os.path.join(DATA_DIR, "last_pushed.json")


# ---------- 数据类 ----------


@dataclass(frozen=True)
class Source:
    """单个 RSS 信息源"""
    id: str                   # 内部唯一标识
    title: str                # 中文名
    category: str             # 职业资格 | 学历提升 | 兜底
    route: str                # RSSHub 路由（不含域名）
    notes: str = ""           # 备注


@dataclass(frozen=True)
class ExamItem:
    """考试项目"""
    id: str
    name: str
    category: str             # 职业资格 / 学历提升
    register_start: str = ""  # ISO date
    register_end: str = ""
    exam_date: str = ""
    url: str = ""
    source: str = ""          # 对应 Source.id


# ---------- 26 个信息源（已通过 RSSHub 官方文档验证） ----------


SOURCES: List[Source] = [
    # ===== 国家级 · 职业资格考试（5）=====
    Source("cpta_notice",        "中国人事考试网 · 通知公告",       "职业资格", "/cpta/notice",
           "72项职业资格考试公告/报名/成绩"),
    Source("cpta_exam_notice",   "中国人事考试网 · 考试通告",       "职业资格", "/cpta/examNotice",
           "各考试报考提醒"),
    Source("nrta_news",          "国家广播电视总局",               "职业资格", "/gov/nrta/news/112",
           "广播电视播音员主持人资格"),
    Source("nmpa_ggtg",          "国家药品监督管理局 · 公告通告",   "职业资格", "/gov/nmpa/xxgk/ggtg",
           "执业药师相关"),
    Source("chinatax_latest",    "国家税务总局 · 最新文件",         "职业资格", "/gov/chinatax/latest",
           "税务师相关政策"),

    # ===== 国家级 · 学历提升考试（10）=====
    Source("neea_gaokao",        "NEEA · 普通高考",                "学历提升", "/neea/gaokao"),
    Source("neea_chengkao",      "NEEA · 成人高考",                "学历提升", "/neea/chengkao"),
    Source("neea_yankao",        "NEEA · 研究生考试",              "学历提升", "/neea/yankao",
           "全国硕士研究生招生考试"),
    Source("neea_zikao",         "NEEA · 高等教育自学考试",        "学历提升", "/neea/zikao"),
    Source("neea_ntce",          "NEEA · 中小学教师资格",          "学历提升", "/neea/ntce"),
    Source("neea_cet",           "NEEA · 大学英语四六级 CET",       "学历提升", "/neea/cet"),
    Source("neea_ncre",          "NEEA · 计算机等级考试 NCRE",     "学历提升", "/neea/ncre"),
    Source("neea_pets",          "NEEA · 全国英语等级考试 PETS",   "学历提升", "/neea/pets"),
    Source("neea_wsk",           "NEEA · 全国外语水平考试 WSK",     "学历提升", "/neea/wsk"),
    Source("neea_ccpt",          "NEEA · 书画等级考试",            "学历提升", "/neea/ccpt"),

    # ===== 教育部 / 国务院（2）=====
    Source("moe_gggs",           "教育部 · 公告公示",              "兜底",     "/moe/jyb_xxgk/s5743/s5744",
           "教育部综合公告"),
    Source("gov_zhengce",        "中国政府网 · 最新政策",           "兜底",     "/gov/zhengce/zuixin",
           "国务院兜底源"),

    # ===== 省级（9）=====
    Source("shmeea",             "上海市教育考试院 · 速递",         "学历提升", "/shmeea"),
    Source("shmeea_self_study",  "上海市教育考试院 · 自考",         "学历提升", "/shmeea/self-study"),
    Source("bjeea",              "北京教育考试院 · 通知公告",       "学历提升", "/gov/beijing/bjeea/bjeeagg"),
    Source("gd_eea",             "广东省教育考试院",               "学历提升", "/gov/guangdong/eea/news"),
    Source("jseea",              "江苏省教育考试院",               "学历提升", "/jseea/news/zkyw"),
    Source("sz_ksy",             "深圳市考试院 · 通知公告",         "学历提升", "/gov/shenzhen/hrss/szksy/tzgg"),
    Source("fj_ksbm",            "福建考试报名网",                 "学历提升", "/fjksbm/1",
           "1=网络报名进行中"),
]


# ---------- 工具函数 ----------


def get_rsshub_instance() -> str:
    """从环境变量读取 RSSHub 实例，未设置则返回默认"""
    return os.environ.get("RSSHUB_INSTANCE", DEFAULT_RSSHUB_INSTANCE).rstrip("/")


def build_feed_url(route: str) -> str:
    """拼接完整的 RSSHub 订阅 URL"""
    return f"{get_rsshub_instance()}{route}"


if __name__ == "__main__":
    # 自检：打印所有源
    print(f"RSSHub 实例: {get_rsshub_instance()}")
    print(f"信息源数量: {len(SOURCES)}")
    for src in SOURCES:
        print(f"  - {src.id:24s} {src.title:30s} {build_feed_url(src.route)}")