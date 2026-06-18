"""
重下失败的 3 个视频
"""
import csv, sys, re
from pathlib import Path
from playwright.sync_api import sync_playwright

def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\n\r]', "", s).strip()[:50] or "video"

with open("douyin_playable.csv", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

failed_indices = [10, 12, 31]  # 0-based indices
targets = [rows[i] for i in failed_indices]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context()
    api = ctx.request

    for idx, r in enumerate(targets, 1):
        title = r["视频标题"]
        url = r["播放链接"]
        name = safe_name(title)
        print(f"[{idx}/3] {name[:40]}…", end=" ")

        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)

        video_src = page.evaluate("""() => {
            const v = document.querySelector('video');
            if (v?.src) return v.src;
            const s = document.querySelector('video source');
            return s?.src || '';
        }""")
        page.close()

        if video_src:
            resp = api.get(video_src)
            if resp.ok:
                fp = Path("videos") / f"{failed_indices[idx-1]+1:03d}_{name}.mp4"
                fp.write_bytes(resp.body())
                print(f"ok {len(resp.body())//1024//1024}MB")
            else:
                print(f"http {resp.status}")
        else:
            print("no video src")

    browser.close()
