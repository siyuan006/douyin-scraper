"""
抖音视频下载器
从 CSV 读取视频列表，选择性下载（复用登录态）

用法:
    # 查看列表
    .\venv\Scripts\python.exe douyin_download.py douyin_playable.csv --list

    # 下载指定序号
    .\venv\Scripts\python.exe douyin_download.py douyin_playable.csv --ids 1,3,5-10

    # 交互选择
    .\venv\Scripts\python.exe douyin_download.py douyin_playable.csv --pick

    # ★ 手动选画质模式：浏览器可见，你亲手点 HD 后再下载
    .\venv\Scripts\python.exe douyin_download.py douyin_playable.csv --ids 1-5 --manual-hd

    # 全部下载
    .\venv\Scripts\python.exe douyin_download.py douyin_playable.csv
"""

import sys
import csv
import re
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path(__file__).parent / "user_data"


def parse_args():
    p = argparse.ArgumentParser(description="抖音视频下载器（选择性下载）")
    p.add_argument("csv", help="CSV 文件路径")
    p.add_argument("--max", "-n", type=int, default=0, help="最多下载数")
    p.add_argument("--output", "-o", type=str, default="./videos", help="保存目录")
    p.add_argument("--ids", type=str, default="",
                   help="按序号下载，如: 1,3,5-10,15")
    p.add_argument("--list", action="store_true", help="只显示列表，不下")
    p.add_argument("--pick", action="store_true", help="交互选择模式")
    p.add_argument("--manual-hd", action="store_true",
                   help="手动选画质：打开浏览器让你点 HD")
    p.add_argument("--hd", action="store_true",
                   help="批量高清：自动通过页面提取 HD 画质，无需手动操作")
    return p.parse_args()


def read_csv(path: str) -> list[dict]:
    with open(path, "rb") as f:
        raw = f.read(4)
    encoding = "utf-8-sig" if raw[:3] in (b"\xef\xbb\xbf",) or raw[:2] in (b"\xff\xfe",) else "utf-8"
    rows = []
    with open(path, newline="", encoding=encoding) as f:
        for row in csv.DictReader(f):
            title = row.get("视频标题") or ""
            vid = row.get("视频ID") or ""
            play_url = row.get("视频直链(可下载)") or ""       # CDN 直链
            page_url = row.get("播放链接") or ""               # douyin.com 页面
            if not page_url and vid:
                page_url = f"https://www.douyin.com/video/{vid}"
            if page_url:
                rows.append({"title": title, "page_url": page_url,
                             "play_url": play_url, "id": vid})
    return rows


def safe_name(s: str, max_len: int = 50) -> str:
    s = re.sub(r'[\\/:*?"<>|\n\r]', "", s).strip()
    return s[:max_len] or "video"


def parse_ids(s: str, total: int) -> list[int]:
    result = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            result.update(range(int(a.strip()), int(b.strip()) + 1))
        else:
            result.add(int(part))
    return sorted(i for i in result if 1 <= i <= total)


def show_list(videos: list[dict]):
    print(f"\n共 {len(videos)} 个视频")
    print("=" * 60)
    for i, v in enumerate(videos, 1):
        t = v["title"][:60].replace("\n", " ")
        print(f"  [{i:3d}] {t}")
    print("=" * 60)


def _try_hd_url(url: str) -> str:
    """尝试将视频 URL 转成高清版"""
    hd_url = url.replace("/playwm/", "/play/")
    hd_url = hd_url.replace("&ratio=720p", "&ratio=1080p")
    hd_url = hd_url.replace("&ratio=540p", "&ratio=1080p")
    hd_url = re.sub(r'&quality=\d+', '&quality=100', hd_url)
    return hd_url


def _capture_video_url(page) -> list[str]:
    """从页面提取所有可能的视频源地址"""
    urls = []

    # 方法1: video 标签 src
    src = page.evaluate("""() => {
        const v = document.querySelector('video');
        if (v?.src) return v.src;
        const s = document.querySelector('video source');
        return s?.src || '';
    }""")
    if src:
        urls.append(src)

    # 方法2: script 中的 play_addr 数据
    src = page.evaluate("""() => {
        const scripts = document.querySelectorAll('script');
        for (const sc of scripts) {
            const t = sc.textContent || '';
            let m;
            m = t.match(/play_addr_265["']?\s*:\s*\{[^}]*?url_list["']?\s*:\s*\[["']([^"']+)["']\]/);
            if (m) return m[1];
            m = t.match(/play_addr_h264["']?\s*:\s*\{[^}]*?url_list["']?\s*:\s*\[["']([^"']+)["']\]/);
            if (m) return m[1];
            m = t.match(/play_addr["']?\s*:\s*\{[^}]*?url_list["']?\s*:\s*\[["']([^"']+)["']\]/);
            if (m) return m[1];
        }
        return '';
    }""")
    if src:
        urls.append(src)

    # 方法3: 页面中所有 video/mp4 链接
    src = page.evaluate("""() => {
        const text = document.body.innerText + Array.from(document.querySelectorAll('script')).map(s=>s.textContent).join(' ');
        const m = text.match(/https?:[^"'\\s]+\.(mp4|m3u8)[^"'\\s]*/);
        return m ? m[0] : '';
    }""")
    if src:
        urls.append(src)

    return urls


def download(videos: list[dict], out_dir: str, manual_hd: bool = False, hd: bool = False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    if manual_hd:
        mode = "手动选画质"
    elif hd:
        mode = "批量高清"
    else:
        mode = "自动"

    print(f"\n📥 下载 {len(videos)} 个 → {out}/（模式: {mode}）\n")

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            channel="msedge",
            headless=not manual_hd,  # 手动模式可见浏览器
            args=["--no-sandbox"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        api = ctx.request

        for idx, v in enumerate(videos, 1):
            name = safe_name(v["title"])
            print(f"[{idx}/{len(videos)}] {name[:40]}…", end=" ")
            downloaded = False

            if not manual_hd and not hd:
                # 方案一：直链下载（优先 HD）
                try:
                    for url_to_try in [v["play_url"], _try_hd_url(v["play_url"])]:
                        if not url_to_try or url_to_try == v["play_url"]:
                            continue
                        resp = api.get(url_to_try, headers={"Referer": "https://www.douyin.com/"})
                        size = int(resp.headers.get("content-length", 0))
                        if resp.ok and size > 50000:
                            fp = out / f"{name}.mp4"
                            fp.write_bytes(resp.body())
                            print(f"✅ {size//1024//1024}MB")
                            ok += 1
                            downloaded = True
                            break
                except Exception:
                    pass

                if downloaded:
                    continue

                # 方案二：直链下载（原始）
                try:
                    resp = api.get(v["play_url"], headers={"Referer": "https://www.douyin.com/"})
                    size = int(resp.headers.get("content-length", 0))
                    if resp.ok and size > 50000:
                        fp = out / f"{name}.mp4"
                        fp.write_bytes(resp.body())
                        print(f"✅ {size//1024//1024}MB")
                        ok += 1
                        continue
                except Exception:
                    pass

            # 方案三：打开页面提取视频源
            try:
                open_page_and_download = False
                if manual_hd or hd:
                    open_page_and_download = True
                elif not v.get("play_url"):
                    open_page_and_download = True

                if open_page_and_download:
                    page.goto(v["page_url"], wait_until="domcontentloaded", timeout=20000)

                    if manual_hd:
                        print(f"\n   👆 请在浏览器中点击播放器右下角的「HD」或「高清」画质")
                        print(f"      选好后按回车键继续下载下一个 …", end="")
                        input()
                    elif hd:
                        print("  ⏳ 提取高清视频 …", end=" ")
                        page.wait_for_timeout(5000)

                    # 用 Performance API 找视频请求
                    video_url = page.evaluate("""() => {
                        const entries = performance.getEntriesByType('resource');
                        for (const e of entries) {
                            if (e.initiatorType === 'video' || e.name.includes('.mp4')) {
                                return e.name;
                            }
                        }
                        // 也检查 video 标签
                        const v = document.querySelector('video');
                        if (v?.src) return v.src;
                        return '';
                    }""")

                    if not video_url:
                        video_url = page.evaluate("""() => {
                            const entries = performance.getEntriesByType('resource');
                            for (const e of entries) {
                                if (e.name.includes('video') && e.name.includes('douyin')) return e.name;
                            }
                            return '';
                        }""")

                    # 尝试下载
                    downloaded = False
                    for url in [video_url, v.get("play_url", "")]:
                        if not url:
                            continue
                        for try_url in [url, _try_hd_url(url)]:
                            try:
                                resp = api.get(try_url, headers={"Referer": "https://www.douyin.com/"})
                                size = int(resp.headers.get("content-length", 0))
                                if resp.ok and size > 50000:
                                    fp = out / f"{name}.mp4"
                                    fp.write_bytes(resp.body())
                                    print(f"✅ {size//1024//1024}MB")
                                    ok += 1
                                    downloaded = True
                                    break
                            except Exception:
                                pass
                        if downloaded:
                            break

                    if not downloaded:
                        print("❌ 无法获取视频源")
                        fail += 1

            except Exception as e:
                print(f" ❌ {e}")
                fail += 1

        ctx.close()

    print(f"\n📊 完成: 成功 {ok} / 失败 {fail}")


def main():
    args = parse_args()
    videos = read_csv(args.csv)
    if not videos:
        print("❌ CSV 中未找到视频")
        return

    if args.list:
        show_list(videos)
        return

    if args.pick:
        show_list(videos)
        inp = input("输入要下载的序号（逗号/横线），回车=全部: ").strip()
        selected = parse_ids(inp, len(videos)) if inp else list(range(1, len(videos) + 1))
        videos = [videos[i - 1] for i in selected]
    elif args.ids:
        selected = parse_ids(args.ids, len(videos))
        videos = [videos[i - 1] for i in selected]
    elif args.max > 0:
        videos = videos[:args.max]

    download(videos, args.output, args.manual_hd, args.hd)


if __name__ == "__main__":
    main()
