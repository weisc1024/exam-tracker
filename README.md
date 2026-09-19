# exam-tracker

国家职业资格考试 & 学历提升考试 · 30 天窗口提醒系统

每天 06:30（北京时间）自动：
1. 从 RSSHub 拉取 24 个官方信息源
2. 解析后写入 `data/announcements.json`
3. 计算 30 天窗口（报名时间 / 考试时间 ≤ 30 天）
4. 推送到飞书机器人 + 企业微信机器人
5. 自动部署 HTML 工作台到 GitHub Pages

---

## 在线预览

部署后访问 `https://<你的用户名>.github.io/exam-tracker/` 即可看到工作台：

- 📅 今日日期 + 30 天窗口内事件统计
- 🔴🟡🟢 按紧急度分组（≤3 天 / 一周内 / 两周内 / 30 天内）
- 🔍 全文搜索 + 月份筛选 + 事件类型筛选
- 📑 全部 / 职业资格 / 学历提升 三标签页
- 🌓 自动适配深色模式

---

## 目录结构

```
exam-tracker/
├── .github/workflows/
│   ├── daily-fetch.yml      # 每日 06:30 抓取 + 推送
│   └── pages.yml            # 抓取完成后自动部署 Pages
├── scripts/
│   ├── config.py             # 24 个 RSSHub 源配置
│   ├── fetch_rss.py          # 主抓取脚本（并发 + 关键词）
│   ├── window.py             # 30 天窗口判断
│   ├── push_feishu.py        # 飞书机器人推送
│   └── push_wecom.py         # 企业微信机器人推送
├── data/
│   ├── exams.json            # 39 个考试项目（人工维护）
│   ├── announcements.json    # 最近公告（自动维护）
│   └── last_pushed.json      # 推送哈希（去重用）
├── web/
│   └── index.html            # HTML 工作台（前端）
└── README.md
```

---

## 快速开始

### 1. fork 或 clone 本仓库

### 2. 配置 GitHub Secrets

进入仓库 `Settings → Secrets and variables → Actions`，新建以下 Secrets：

| Secret 名称 | 必填 | 说明 |
|---|---|---|
| `RSSHUB_INSTANCE` | ⬜ | RSSHub 实例域名（默认 `https://rsshub.umzzz.com`） |
| `FEISHU_WEBHOOK` | ⬜ | 飞书机器人 Webhook（留空则不推飞书） |
| `FEISHU_SECRET` | ⬜ | 飞书加签密钥（可选） |
| `WECOM_WEBHOOK` | ⬜ | 企业微信机器人 Webhook（留空则不推企微） |

### 3. 启用 GitHub Pages

进入仓库 `Settings → Pages`：
- Source 选 **GitHub Actions**
- 保存即可，无需选分支

### 4. 启用 Actions

进入仓库 `Actions` 标签 → 启用 workflows：
- 先手动跑一次 **"每日抓取考试公告"**（试抓 + 更新 exams.json）
- 完成后会自动触发 **"部署 HTML 工作台到 GitHub Pages"**
- 1-2 分钟后访问 `https://<你的用户名>.github.io/exam-tracker/`

---

## 推送内容示例

### 飞书卡片

```
📅 9 月 19 日考试提醒

🔴 报名截止 ≤7 天
- 一级造价工程师 · 广东考区 · 报名截止 9 月 25 日
- 法律职业资格（主观题） · 报名截止 9 月 30 日

🟡 考试日 ≤7 天
- 注册测绘师 · 9 月 5-6 日 · [准考证打印入口]

🟢 报名开启 ≤7 天
- 中级注册安全工程师 · 8 月 4 日开始 · [查看详情]
```

### 企业微信 Markdown

```
### 🎓 学历提升提醒
**2026 考研**：预报名 9-30 ~ 10-13 | 正式报名截止 10-27
**2026 成人高考**：考试 10 月 | 录取查询 12 月

[完整时间表](https://你的域名/)
```

---

## 本地调试

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export RSSHUB_INSTANCE="https://rsshub.umzzz.com"
export FEISHU_WEBHOOK="https://open.feishu.cn/..."
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/..."

# 跑一次抓取
python scripts/fetch_rss.py

# 测试推送（不实际发送）
python scripts/push_feishu.py --dry-run
python scripts/push_wecom.py --dry-run

# 本地预览 HTML 工作台
cd web && python3 -m http.server 8000
# 浏览器打开 http://localhost:8000
```

---

## 信息源清单

详见 [`scripts/config.py`](scripts/config.py)，包含 24 个经 RSSHub 官方文档验证的源：

- **国家级职业资格**：中国人事考试网、广电总局、药监局、税务总局
- **国家级学历提升**：NEEA（高考、考研、自考、成考、教师资格、CET、NCRE、PETS、WSK、书画、同等学力）
- **教育部 / 国务院**：教育部公告、中国政府网最新政策
- **省级考试机构**：上海、北京、广东、江苏、深圳、福建

---

## 维护节奏

- **每日 06:30**：自动抓取 + 推送 + 重新部署 Pages
- **每月 1 日**：检查 RSSHub 路由是否需要更新
- **每年 12 月**：人工校对 `data/exams.json` 下一年考试日期
- **每年 1 月**：更新 README 与推送文案

---

## License

MIT