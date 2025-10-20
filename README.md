# SSRN Crawler

异步 Playwright 爬虫，支持断点续跑（JSON checkpoint）。

## 快速开始
```bash
# 安装依赖
pip install -e .
playwright install chromium

# 放置 cookies.json（登录后导出）
# 运行
ssrn-crawler
