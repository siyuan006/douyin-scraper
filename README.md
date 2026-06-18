# 抖音视频爬虫 & 下载器

使用 Playwright + Edge/Chromium 浏览器自动抓取抖音用户的所有视频，支持批量下载 HD 画质。

---

## 🚀 快速开始（首次使用）

```bash
# 1. 克隆项目
git clone https://github.com/siyuan006/scraper-project.git
cd scraper-project

# 2. 创建虚拟环境
# Windows:
python -m venv venv
venv\Scripts\activate

# macOS / Linux:
python3 -m venv venv
source venv/bin/activate

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
playwright install chromium

# 也可以安装 Edge（如果系统有 Edge）：
# playwright install msedge
```

> **💡 提示**：后续每次使用前，先运行上面的 `activate` 命令进入虚拟环境。
> Windows PowerShell 用 `venv\Scripts\Activate.ps1`，CMD 用 `venv\Scripts\activate.bat`。

---

## 📋 完整流程

### 第 1 步：登录（仅首次需要）

```bash
python douyin_spider.py --login
```

会弹出浏览器 → 扫码或手机号登录抖音 → 关掉浏览器即可。
登录态自动保存到 `user_data/` 目录，后续不再需要登录。

### 第 2 步：抓取视频

```bash
python douyin_spider.py "https://www.douyin.com/user/用户ID"
```

自动翻页抓取该用户所有视频，生成 CSV 文件。

### 第 3 步：下载视频

```bash
# 自动模式（最快，标清）
python douyin_download.py 结果.csv

# 批量高清模式（推荐）
python douyin_download.py 结果.csv --hd

# 手动选画质模式
python douyin_download.py 结果.csv --ids 1-5 --manual-hd
```

---

## 📖 脚本用法

### douyin_spider.py（抓取视频）

| 参数 | 说明 |
|------|------|
| `URL` | 抖音用户主页链接（必填） |
| `-n` / `--max-videos` | 最多抓取数，`0`=全部 |
| `-o` / `--output` | 输出 CSV 文件名 |
| `--login` | 登录模式 |
| `--no-headless` | 显示浏览器窗口（调试用） |
| `-c` / `--cookie` | 传入 Cookie 字符串 |

**示例：**

```bash
# 抓取指定用户所有视频
python douyin_spider.py "https://www.douyin.com/user/MS4wLjABAAA..."

# 只抓前 50 条
python douyin_spider.py "URL" -n 50

# 指定输出文件名
python douyin_spider.py "URL" -o mydata.csv
```

#### CSV 输出列说明

| 列名 | 说明 |
|------|------|
| 视频标题 | 视频文案 |
| 播放链接 | 抖音页面链接，点开即看 |
| 视频直链(可下载) | MP4 直链，用于下载 |
| 画质 | 高清 / 标清 |
| 视频ID | 抖音内部 ID |
| 作者 | 作者昵称 |

---

### douyin_download.py（下载视频）

| 参数 | 说明 |
|------|------|
| `CSV文件` | 爬虫生成的 CSV 文件路径（必填） |
| `--ids` | 指定序号下载，如 `1,3,5-10` |
| `--list` | 只显示列表，不下载 |
| `--pick` | 交互选择模式 |
| `--hd` | 批量高清：自动打开页面提取 HD 画质 |
| `--manual-hd` | 手动选画质（见下方说明） |
| `-n` / `--max` | 最多下载数 |
| `-o` / `--output` | 保存目录（默认 `./videos`） |

**示例：**

```bash
# 查看列表
python douyin_download.py 结果.csv --list

# 下载第 1、3、5-10 条
python douyin_download.py 结果.csv --ids 1,3,5-10

# 下载前 5 条（高清）
python douyin_download.py 结果.csv --ids 1-5 --hd

# 交互选择
python douyin_download.py 结果.csv --pick
```

#### 手动选画质模式（`--manual-hd`）

视频默认可能是标清，此模式让你在浏览器中亲手点 HD 后再下载：

```bash
python douyin_download.py 结果.csv --ids 1-3 --manual-hd
```

操作：浏览器打开视频 → 鼠标点播放器的「HD」按钮 → 等待 5 秒自动下载。

---

### 下载模式对比

| 模式 | 命令 | 速度 | 画质 | 操作 |
|------|------|------|------|------|
| 自动 | 不加参数 | 最快 | 标清 | 全自动 |
| 批量高清 | `--hd` | 中等 | 高清 | 全自动 |
| 手动选画质 | `--manual-hd` | 较慢 | 最高 | 需手动操作 |

---

## ❓ 常见问题

**Q: 报错 `No module named 'playwright'`**
A: 没有激活虚拟环境或没装依赖。先 `source venv/bin/activate`（Windows: `venv\Scripts\activate`）再运行，或检查是否执行过 `pip install -r requirements.txt`。

**Q: 提示找不到浏览器 / `Executable doesn't exist`**
A: 运行 `playwright install chromium` 安装浏览器。如果要用 Edge，先确认系统已安装 Edge，然后运行 `playwright install msedge`。

**Q: 提示「安全验证」**
A: 先运行 `--login` 登录一次；或加 `--no-headless` 手动完成滑块验证。

**Q: 下载的视频没有声音**
A: 爬虫已优先使用带音频的视频地址。如果还是没声音，用 `--hd` 模式（打开页面提取的流通常带音频）。

**Q: 画质不够清晰**
A: 下载时加 `--hd` 参数。

**Q: Excel 打开 CSV 乱码**
A: 用 Excel → 数据 → 自文本/CSV → 编码选 UTF-8。

**Q: 如何抓取其他用户？**
A: 直接换 URL：`python douyin_spider.py "https://www.douyin.com/user/新用户ID" -o 新用户.csv`

**Q: 想只下载特定视频？**
A: 先 `--list` 看列表，再用 `--ids` 指定序号：`python douyin_download.py 结果.csv --ids 1,5,10-20`

---

## 📁 项目文件结构

```
scraper-project/
├── douyin_spider.py        # 爬虫脚本（抓取视频信息）
├── douyin_download.py      # 下载脚本（下载 MP4）
├── main.py                 # 简版示例入口（供参考）
├── _check_csv.py           # CSV 检查工具
├── _retry.py               # 重试工具
├── requirements.txt        # Python 依赖
├── README.md               # 本说明文件
├── user_data/              # 浏览器登录态（自动生成，不要删除）
├── videos/                 # 下载的视频（自动生成）
└── venv/                   # Python 虚拟环境（本地生成，不提交 Git）
```

---

## ⚡ 常用命令速查

```bash
# 登录
python douyin_spider.py --login

# 抓取
python douyin_spider.py "用户主页URL" -o data.csv

# 查看列表
python douyin_download.py data.csv --list

# 下载（高清）
python douyin_download.py data.csv --hd

# 下载指定序号
python douyin_download.py data.csv --ids 1-10 --hd

# 手动选画质
python douyin_download.py data.csv --ids 1 --manual-hd

# 全部下载
python douyin_download.py data.csv
```

---

## 🖥️ 跨平台说明

本项目支持 **Windows** / **macOS** / **Linux** 三大平台。

| 平台 | 虚拟环境激活 | 推荐浏览器 |
|------|-------------|-----------|
| Windows | `venv\Scripts\activate` | Edge（`playwright install msedge`） |
| macOS | `source venv/bin/activate` | Chromium（`playwright install chromium`） |
| Linux | `source venv/bin/activate` | Chromium（`playwright install chromium`） |

> Linux 服务器上运行可能需要安装系统依赖：
> ```bash
# playwright 系统依赖（仅 Linux）
playwright install-deps chromium
```
