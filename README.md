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

## 配置

支持通过 `.env` 文件或环境变量配置。

```bash
cp .env.example .env
```

| 变量名 | 默认值 | 说明 |
|---|---|---|
| `INPUT_FILE` | `urls.txt` | 默认 URL 列表文件路径 |

也可直接导出环境变量：

```bash
export INPUT_FILE=urls.txt
```

---

## 使用方法

### 1. 准备 URL 列表

每行一个 URL，保存为文本文件，例如 `urls.txt`：

```
https://example.com
https://another-site.com
```

### 2. 爬取并生成原始数据

```bash
# 使用 .env 中的 INPUT_FILE 默认值
uv run python main.py

# 或显式指定参数
uv run python main.py --input urls.txt --output data/results.csv --raw-dir data/raw --cache data/domain_cache.json
```

每个 URL 会在 `data/raw/` 下生成一个独立的原始 CSV 文件，记录该页面加载的所有资源详情；同时汇总到 `data/results.csv`。

参数说明：

| 参数 | 默认值来源 | 说明 |
|---|---|---|
| `--input` | `INPUT_FILE` 环境变量 | URL 列表文件路径 |
| `--output` | `data/results.csv` | 汇总统计 CSV 路径 |
| `--raw-dir` | `data/raw` | 原始资源文件目录 |
| `--workers` | `4` | 并行爬取进程数 |

**断点续传**：重新运行会自动跳过已处理的 URL。

### 3. 重新统计（无需重新爬取）

如果只想修改分类或重新聚合，可以从已有原始文件重跑：

```bash
uv run python aggregate.py --raw-dir data/raw --output data/results.csv

# 强制重新调用 LLM 对所有域名重新分类
uv run python aggregate.py --raw-dir data/raw --output data/results.csv --reclassify
```

### 4. 数据清理

```bash
uv run python analysis/clean.py --input data/results.csv --output data/results_clean.csv
```

### 5. 画图

```bash
uv run python analysis/plot.py --input data/results_clean.csv --output-dir data/charts
```

生成的图表：
- `industry_pie.png` — 第三方域名行业类别占比饼图
- `resource_bar.png` — 各资源类型（JS/CSS/图片等）数量柱状图
- `url_heatmap.png` — 每个 URL 的行业域名数量热力图

---

## 输出格式

### 原始文件 `data/raw/<site>.csv` — 每行一个资源请求

| 列名 | 说明 |
|---|---|
| `resource_url` | 资源完整 URL |
| `resource_type` | 类型：script / stylesheet / image / media / font / xhr / other |
| `domain` | 资源所属域名 |
| `method` | HTTP 方法（GET / POST 等） |
| `status_code` | HTTP 响应状态码 |
| `content_type` | Content-Type 响应头 |
| `content_length_bytes` | 响应体大小（字节），-1 表示未知 |
| `is_third_party` | 是否为第三方域名 |
| `domain_category` | 域名行业分类（仅第三方）|

### 汇总文件 `data/results.csv` — 每行一个页面

| 列名 | 说明 |
|---|---|
| `url` | 原始 URL |
| `status` | `ok` / `timeout` / `error` |
| `total_resources` | 资源总数 |
| `res_script` ~ `res_other` | 各资源类型数量 |
| `cat_gambling` ~ `cat_other` | 各行业第三方域名数量 |
| `third_party_domains` | 所有第三方域名（逗号分隔） |

---

## 项目结构

```
├── src/
│   ├── run_crawl.py     # 爬取 pipeline CLI
│   ├── run_aggregate.py # 重新统计 CLI
│   ├── crawler.py       # Playwright 无头浏览器爬取
│   ├── classifier.py    # 规则匹配域名分类
│   ├── raw_io.py        # 原始资源文件读写
│   ├── reporter.py      # 统计聚合，生成汇总行
│   ├── config.py        # 配置加载（.env / 环境变量）
│   └── analysis/
│       ├── clean.py     # 数据清理脚本
│       └── plot.py      # 画图脚本
├── tests/
│   ├── test_classifier.py
│   └── test_reporter.py
├── data/
│   ├── raw/             # 每站原始资源 CSV（gitignore）
│   └── results.csv      # 汇总统计（gitignore）
├── .env.example
├── setup.sh
└── pyproject.toml
```

安装后通过 `uv run` 调用：

```bash
uv run crawl       # 爬取
uv run aggregate   # 重新统计
uv run clean       # 清理
uv run plot        # 画图
```
