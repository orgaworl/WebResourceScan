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
# 使用 .env 中的 INPUT_FILE 默认值（BFS 深度2，每站最多20页）
uv run crawl

# 显式指定所有参数
uv run crawl --input urls.txt --output data/results.csv --raw-dir data/raw --workers 4 --max-pages 20 --depth 2
```

每个站点会在 `data/raw/` 下生成一个独立的原始 CSV 文件，记录该站所有子页面加载的全部资源详情；同时汇总到 `data/results.csv`。

参数说明：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--input` | `INPUT_FILE` 环境变量 | URL 列表文件路径 |
| `--output` | `data/results.csv` | 汇总统计 CSV 路径 |
| `--raw-dir` | `data/raw` | 原始资源文件目录 |
| `--workers` | 自适应 | 并行爬取进程数（默认：min(CPU数, 站点数, 8)） |
| `--page-workers` | `1` | 每站点并行页数（最大值自动限制为3） |
| `--max-pages` | `20` | 每个站点最多爬取页面数 |
| `--depth` | `2` | BFS 链接跟踪深度（0=仅入口页） |
| `--no-stealth` | 关闭 | 禁用反检测策略（速度更快） |

### 性能优化说明

- **二进制资源拦截**：image/media/font 类型请求只记录元数据，不下载响应体，显著减少带宽占用
- **分级超时**：首次尝试 8s 快速失败，失败后用完整超时重试，避免慢站阻塞并发队列
- **BFS 链接过滤**：自动跳过 login/logout/cart/checkout 等无价值路径，聚焦爬取预算
- **共享分类缓存**：所有 worker 进程共享域名分类结果，避免重复计算
- **自适应并发**：根据 CPU 核数和待处理站点数自动调整 worker 数量
- **压缩存储**：原始文件以 `.csv.gz` 格式存储，减少约 70-80% 磁盘空间
- **页面级断点续传**：每个子页面爬取成功后写入 checkpoint，重启后跳过已爬页面
- **站点内并行**：`--page-workers > 1` 时，每站点使用多个浏览器 context 并行爬取子页面

**断点续传**：重新运行会自动跳过已处理的 URL。

### 3. 重新统计（无需重新爬取）

如果只想更新分类或重新聚合，可从已有原始文件重跑：

```bash
uv run aggregate --raw-dir data/raw --output data/results.csv
```

### 4. 数据清理

```bash
uv run clean --input data/results.csv --output data/results_clean.csv
```

生成 `data/results_clean.csv`，新增以下列：

| 列名 | 说明 |
|---|---|
| `site_category` | 站点所属行业分类（gambling/gaming/crypto 等，来自 urls.txt） |
| `script_ratio` | 脚本密度：(res_script + res_xhr) / total_resources |
| `tp_domain_count` | 独立第三方域名数量 |
| `tp_ratio` | 第三方资源占比 |
| `ad_intensity` | 广告追踪强度：cat_ad / total_resources |
| `image_ratio` | 图片资源占比 |

### 5. 画图

```bash
# 概览图（3张）
uv run plot --input data/results_clean.csv --output-dir data/charts

# 行业对比图（5张）
uv run plot-industry --input data/results_clean.csv --raw-results data/results.csv --output-dir data/charts

# 第三方域名分析图（4张）
uv run plot-domains --input data/results_clean.csv --output-dir data/charts
```

生成的图表（共 12 张）：

**概览图** (`uv run plot`)
| 文件名 | 说明 |
|---|---|
| `resource_category_donut.png` | 第三方域名行业类别占比环形图 |
| `resource_bar.png` | 各资源类型（JS/CSS/图片等）数量柱状图，附百分比 |
| `url_heatmap.png` | 各站点的行业域名数量热力图（按 site_category 排序） |

**行业对比图** (`uv run plot-industry`)
| 文件名 | 说明 |
|---|---|
| `crawl_success_rate.png` | 各行业爬取成功率（颜色标注高/中/低成功率） |
| `resource_mix_by_industry.png` | 各行业资源类型构成 100% 堆叠横条图 |
| `tp_load_by_industry.png` | 各行业第三方域名分类加载量分组柱状图 |
| `script_ratio_boxplot.png` | 各行业脚本密度（script+XHR占比）箱线图 |
| `resource_count_scatter.png` | 各行业站点总资源数分布散点图（对数坐标） |

**第三方域名分析图** (`uv run plot-domains`)
| 文件名 | 说明 |
|---|---|
| `top_tp_domains.png` | 出现频次最高的 25 个第三方域名横条图 |
| `domain_presence_heatmap.png` | 前 20 个域名在各行业的覆盖率热力图 |
| `tp_bubble.png` | 资源数 vs. 第三方域名数气泡图（气泡大小=脚本密度） |
| `domain_ubiquity_hist.png` | 第三方域名"普遍性"分布直方图（幂律分布） |

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
