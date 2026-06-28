# Web Resource Classifier

测量特定领域网页上的软件资源并分类统计（赌博、游戏、广告等）。

以网页列表文件为输入，使用无头浏览器对每个站点进行多页 BFS 爬取，捕获所有网络资源（含懒加载和 iframe 资源），通过规则匹配对第三方域名进行行业分类，输出统计结果到 CSV 表格，并提供数据整理和画图脚本。

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
uv run crawl
```

每个站点在 `data/raw/` 下生成 `.csv.gz` 原始资源文件，同时汇总到 `data/results.csv`。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--input` | `urls.txt` | URL 列表文件路径 |
| `--output` | `data/results.csv` | 汇总统计 CSV 路径 |
| `--raw-dir` | `data/raw` | 原始资源文件目录 |
| `--workers` | 自适应 | 并行爬取进程数（默认：min(CPU数, 站点数, 8)） |
| `--page-workers` | `1` | 每站点并行页数（最大3） |
| `--max-pages` | `20` | 每站点最多爬取页面数 |
| `--depth` | `2` | BFS 链接跟踪深度（0=仅入口页） |
| `--no-stealth` | 关闭 | 禁用反检测策略 |

**断点续传**：重新运行会自动跳过已处理的 URL。

### 3. 数据处理

```bash
uv run process
```

依次执行：①从 `data/raw/` 重新聚合 → ②过滤清洗 → ③计算衍生指标，输出 `data/results_clean.csv`。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--raw-dir` | `data/raw` | 原始资源文件目录 |
| `--results` | `data/results.csv` | 聚合中间文件 |
| `--output` | `data/results_clean.csv` | 最终清洗文件 |
| `--urls-file` | `urls.txt` | 用于行业分类映射 |
| `--skip-aggregate` | 关闭 | 跳过聚合，仅重新清洗 |

新增衍生列：`site_category`（行业分类）、`script_ratio`、`tp_domain_count`、`tp_ratio`、`ad_intensity`、`image_ratio`。

### 4. 画图

```bash
uv run plot
```

从 `data/results_clean.csv` 生成全部 12 张图表，保存到 `data/charts/`。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--input` | `data/results_clean.csv` | 清洗后的数据文件 |
| `--raw-results` | `data/results.csv` | 含全部状态的原始汇总（用于成功率图） |
| `--output-dir` | `data/charts` | 图表输出目录 |

**概览图（3张）**
| 文件 | 说明 |
|---|---|
| `resource_category_donut.png` | 第三方域名行业类别占比环形图 |
| `resource_bar.png` | 各资源类型数量柱状图（附百分比） |
| `url_heatmap.png` | 各站点行业域名数量热力图 |

**行业对比图（5张）**
| 文件 | 说明 |
|---|---|
| `crawl_success_rate.png` | 各行业爬取成功率 |
| `resource_mix_by_industry.png` | 各行业资源类型构成 100% 堆叠图 |
| `tp_load_by_industry.png` | 各行业第三方域名加载量 |
| `script_ratio_boxplot.png` | 各行业脚本密度箱线图 |
| `resource_count_scatter.png` | 各行业站点资源数散点图 |

**第三方域名图（4张）**
| 文件 | 说明 |
|---|---|
| `top_tp_domains.png` | 最高频 25 个第三方域名 |
| `domain_presence_heatmap.png` | 前 20 个域名在各行业的覆盖率热力图 |
| `tp_bubble.png` | 资源数 vs 第三方域名数气泡图 |
| `domain_ubiquity_hist.png` | 第三方域名普遍性分布直方图 |

---

## 输出格式

### 原始文件 `data/raw/<site>.csv.gz` — 每行一个资源请求（gzip 压缩）

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
| `source_page` | 产生该资源的子页面 URL |
| `initiator` | 请求发起方类型（parser / script / other） |
| `from_iframe` | 若资源由 iframe 发起则为 iframe URL，否则为空 |

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
│   ├── test_crawler.py
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
