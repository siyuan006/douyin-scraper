抖音视频爬虫 & 下载器 - 使用说明书
=====================================

使用 Playwright + Edge 浏览器自动抓取抖音用户的所有视频，支持批量下载 HD 画质。


一、环境准备
============

  项目位置: 解压/克隆到的目录（如 D:\scraper-project）

  每次运行都要用 .\venv\Scripts\python.exe 开头，不要直接用 python。


二、完整流程
============

  cd scraper-project

  ----- 第 1 步：登录（仅首次需要）-----
  .\venv\Scripts\python.exe douyin_spider.py --login

  会弹出 Edge 浏览器 -> 扫码或手机号登录抖音 -> 关掉浏览器
  登录态自动保存到 user_data/ 目录，后续不再需要登录


  ----- 第 2 步：抓取视频 -----
  .\venv\Scripts\python.exe douyin_spider.py "https://www.douyin.com/user/用户ID"

  自动翻页抓取该用户所有视频，生成 CSV 文件。
  抓取结果包含：视频标题、播放链接、视频直链、画质、作者等。


  ----- 第 3 步：下载视频 -----
  三种模式：

  ① 自动模式（最快）
     .\venv\Scripts\python.exe douyin_download.py 结果.csv
     直接使用 CSV 中的视频地址下载，速度最快

  ② 批量高清模式（推荐）
     .\venv\Scripts\python.exe douyin_download.py 结果.csv --hd
     自动打开每个视频页面提取高清源，画质最好

  ③ 手动选画质模式
     .\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1-5 --manual-hd
     浏览器可见，让你亲手点击播放器的「HD」画质，选好后按回车下载


三、爬虫脚本：douyin_spider.py
===============================

  作用：打开用户主页，自动滚动 + API 翻页，抓取所有视频信息

  必填参数：
    URL         抖音用户主页链接
                例如: https://www.douyin.com/user/MS4wLjABAAAAGiYclY2PlZY9y...

  可选参数：
    -n / --max-videos  最多抓取数（0=全部）
    -o / --output      输出 CSV 文件名
    --login            登录模式
    --no-headless      显示浏览器窗口（调试用）
    -c / --cookie      传入 Cookie 字符串

  示例：
    抓取指定用户所有视频：
    .\venv\Scripts\python.exe douyin_spider.py "https://www.douyin.com/user/MS4wLjABAAAAGiYclY2PlZY9yfTv1PyP1bcvsCCx1u52s3enWB5KPvKQIeKNW4ti7Gp_j8-jN5Kv"

    只抓前 50 条：
    .\venv\Scripts\python.exe douyin_spider.py "URL" -n 50

    指定文件名：
    .\venv\Scripts\python.exe douyin_spider.py "URL" -o mydata.csv


四、下载脚本：douyin_download.py
===============================

  作用：从 CSV 读取视频列表，选择性下载 MP4 文件

  必填参数：
    CSV文件     爬虫生成的 CSV 文件路径

  可选参数：
    --ids       指定序号下载，如 1,3,5-10,15
    --list      只显示视频列表，不下载
    --pick      交互选择模式（先看列表，再手动输序号）
    --hd        批量高清：自动打开页面提取 HD 画质
    --manual-hd 手动选画质：打开浏览器让你点 HD，按回车下载
    -n / --max  最多下载数
    -o / --output 保存目录（默认 ./videos）

  示例：
    查看列表：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --list

    下载第 1、3、5-10 条：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1,3,5-10

    下载前 5 条（高清）：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1-5 --hd

    全部高清下载：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --hd

    交互选择：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --pick

    手动选画质：
    .\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1-3 --manual-hd


五、下载模式对比
================

  模式        命令                    速度  画质  操作
  ------------------------------------------------
  自动        不加参数               最快  标清  全自动
  批量高清    --hd                   中等  高清  全自动
  手动选画质  --manual-hd            较慢  最高  需要操作


六、常见问题
============

  Q: 报错 "No module named 'playwright'"
  A: 必须用 .\venv\Scripts\python.exe 开头，不要直接用 python

  Q: 提示「安全验证」
  A: 先运行 --login 登录一次；或加 --no-headless 手动完成滑块验证

  Q: 下载的视频没有声音
  A: 爬虫已优先使用带音频的视频地址。
     如果还是没声音，用 --hd 模式（打开页面提取的流通常带音频）

  Q: 画质不够清晰
  A: 下载时加 --hd 参数

  Q: Excel 打开 CSV 乱码
  A: 用 Excel -> 数据 -> 自文本/CSV -> 编码选 UTF-8

  Q: 如何抓取其他用户？
  A: 直接换 URL：
     .\venv\Scripts\python.exe douyin_spider.py "https://www.douyin.com/user/新用户ID" -o 新用户.csv

  Q: 想只下载特定视频？
  A: 先 --list 看列表，再用 --ids 指定序号：
     .\venv\Scripts\python.exe douyin_download.py 结果.csv --ids 1,5,10-20


七、项目文件结构
================

  scraper-project/
    douyin_spider.py      爬虫脚本（抓取视频信息）
    douyin_download.py    下载脚本（下载 MP4）
    requirements.txt      Python 依赖
    README.txt            本说明书
    user_data/            浏览器登录态（自动生成，不要删除）
    videos/               下载的视频（自动生成）
    结果.csv              抓取结果


八、常用命令速查
================

  登录：
    .\venv\Scripts\python.exe douyin_spider.py --login

  抓取：
    .\venv\Scripts\python.exe douyin_spider.py "用户主页URL" -o data.csv

  查看列表：
    .\venv\Scripts\python.exe douyin_download.py data.csv --list

  下载（高清）：
    .\venv\Scripts\python.exe douyin_download.py data.csv --hd

  下载指定序号：
    .\venv\Scripts\python.exe douyin_download.py data.csv --ids 1-10 --hd

  手动选画质：
    .\venv\Scripts\python.exe douyin_download.py data.csv --ids 1 --manual-hd

  全部下载：
    .\venv\Scripts\python.exe douyin_download.py data.csv
