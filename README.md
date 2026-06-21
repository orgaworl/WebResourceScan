# Web Resource Classifier

测量特定领域网页上的软件资源并分类统计（赌博、游戏、广告等）。

以网页列表文件为输入，使用无头浏览器捕获每个页面加载的所有网络资源，通过 LLM 对第三方域名进行行业分类，输出统计结果到 CSV 表格，并提供数据整理和画图脚本。

---

## 安装

需要 Python 3.12+，使用 [uv](https://github.com/astral-sh/uv) 管理依赖。

```bash
# 一键初始化（安装依赖 + 下载 Chromium）
bash setup.sh
```

或手动：

```bash
uv sync
uv run playwright install chromium
```

设置 Anthropic API Key（用于域名分类）：

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

---

## 使用方法

### 1. 准备 URL 列表

每行一个 URL，保存为文本文件，例如 `urls.txt`：

```
https://example.com
https://another-site.com
```

### 2. 运行爬取与分类

```bash
uv run python main.py --input urls.txt --output data/results.csv --cache data/domain_cache.json
```

参数说明：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--input` | （必填） | URL 列表文件路径 |
| `--output` | `data/results.csv` | 输出 CSV 文件路径 |
| `--cache` | `data/domain_cache.json` | 域名分类缓存文件（自动创建，跨次运行复用） |

**断点续传**：若中途中断，重新运行同一命令会自动跳过已处理的 URL。

### 3. 数据清理

过滤掉爬取失败的行，填充空值：

```bash
uv run python analysis/clean.py --input data/results.csv --output data/results_clean.csv
```

### 4. 画图

生成三张统计图（保存为 PNG）：

```bash
uv run python analysis/plot.py --input data/results_clean.csv --output-dir data/charts
```

生成的图表：
- `industry_pie.png` — 第三方域名行业类别占比饼图
- `resource_bar.png` — 各资源类型（JS/CSS/图片等）数量柱状图
- `url_heatmap.png` — 每个 URL 的行业域名数量热力图

---

## 输出格式

`results.csv` 每行对应一个 URL，列含义如下：

| 列名 | 说明 |
|---|---|
| `url` | 原始 URL |
| `status` | `ok` / `timeout` / `error` |
| `total_resources` | 页面加载的资源总数 |
| `res_script` | JS 脚本数量 |
| `res_stylesheet` | CSS 数量 |
| `res_image` | 图片数量 |
| `res_media` | 音视频数量 |
| `res_font` | 字体数量 |
| `res_xhr` | XHR/Fetch 请求数量 |
| `res_other` | 其他资源数量 |
| `cat_gambling` | 赌博类第三方域名数量 |
| `cat_gaming` | 游戏类第三方域名数量 |
| `cat_ad` | 广告/追踪类域名数量 |
| `cat_payment` | 支付类域名数量 |
| `cat_cdn` | CDN/基础设施类域名数量 |
| `cat_other` | 其他/未知类域名数量 |
| `third_party_domains` | 所有第三方域名（逗号分隔） |

---

## 项目结构

```
├── main.py              # 主入口 CLI
├── crawler.py           # Playwright 无头浏览器爬取
├── classifier.py        # LLM 域名分类（带本地缓存）
├── reporter.py          # 统计聚合，生成 CSV 行
├── analysis/
│   ├── clean.py         # 数据清理脚本
│   └── plot.py          # 画图脚本
├── data/                # 输出数据目录（gitignore）
├── setup.sh             # 环境初始化脚本
└── pyproject.toml       # 项目依赖
```
