# 抖音视频爬虫 & 下载器

使用 Playwright + Edge 浏览器自动抓取抖音用户的所有视频，支持批量下载。

---

## 快速开始

```powershell
# 进入项目目录（换成自己实际的路径）
cd scraper-project

# 1️⃣ 登录（仅首次）
.\venv\Scripts\python.exe douyin_spider.py --login

# 2️⃣ 抓取视频
.\venv\Scripts\python.exe douyin_spider.py "https://www.douyin.com/user/用户ID"

# 3️⃣ 下载视频
.\venv\Scripts\python.exe douyin_download.py 结果.csv
```

---

## 脚本一：douyin_spider.py（抓取视频）

### 用法

```powershell
.\venv\Scripts\python.exe douyin_spider.py "用户主页URL" [选项]
```

### 参数

| 参数 | 说明 |
|---|---|
| `URL` | 抖音用户主页链接（必填） |
| `-n` / `--max-videos` | 最多抓取数，0=全部 |
| `-o` / `--output` | 输出 CSV 文件名 |
| `--login` | 登录模式 |
| `--no-headless` | 显示浏览器窗口 |
| `-c` / `--cookie` | 传入 Cookie 字符串 |

### CSV 输出列

| 列 | 说明 |
|---|---|
| 视频标题 | 视频文案 |
| 播放链接 | 抖音页面链接，点开即看 |
| 视频直链(可下载) | MP4 直链，用于下载 |
| 画质 | 高清 / 标清 |
| 视频ID | 抖音内部 ID |
| 作者 | 作者昵称 |

---

## 脚本二：douyin_download.py（下载视频）

### 用法

```powershell
.\venv\Scripts\python.exe douyin_download.py CSV文件 [选项]
```

### 参数

| 参数 | 说明 |
|---|---|
| `--ids` | 指定序号下载，如 `1,3,5-10` |
| `--list` | 只显示列表，不下载 |
| `--pick` | 交互选择模式 |
| `--manual-hd` | 手动选画质（见下方） |
| `-n` / `--max` | 最多下载数 |
| `-o` / `--output` | 保存目录（默认 `./videos`） |

### 手动选画质模式（`--manual-hd`）

视频默认可能是标清，此模式让你在浏览器中亲手点 HD 后再下载：

```powershell
.\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1-3 --manual-hd
```

操作：浏览器打开视频 → 鼠标点播放器的「HD」按钮 → 等待 5 秒自动下载。

---

## 常见问题

**Q: 报错 `No module named 'playwright'`**
始终用 `.\venv\Scripts\python.exe` 开头，不要用裸 `python`。

**Q: 提示「安全验证」**
先运行 `--login` 登录，或加 `--no-headless` 手动过验证。

**Q: 画质不够清晰**
下载时加 `--manual-hd` 手动选高清。

**Q: Excel 打开 CSV 乱码**
用 Excel → 数据 → 自文本/CSV → 编码选 UTF-8。

---

## 文件结构

```
scraper-project/
├── douyin_spider.py        # 爬虫
├── douyin_download.py       # 下载器
├── requirements.txt         # 依赖
├── user_data/               # 登录态（自动生成）
├── videos/                  # 下载的视频
└── venv/                    # 虚拟环境
```
