"""
抖音用户视频爬虫 v4
====================
使用真实 Edge 浏览器 + 持久化登录态 + byted_acrawler 签名翻页

策略:
  1. 使用系统安装的 Edge 浏览器（非 Playwright 内置 Chromium）— 指纹更真实
  2. 持久化登录态避免触发验证码（user_data/ 目录）
  3. 拦截页面 API JSON 提取视频数据（非 DOM 解析）
  4. 利用 window.byted_acrawler 签名引擎进行 X-Bogus 签名翻页
  5. 自动滚动 + JS 翻页双模式，最大化获取视频数量

用法:
    python douyin_spider.py --login                            # 首次登录
    python douyin_spider.py "https://www.douyin.com/user/ID"   # 抓取视频
    python douyin_spider.py "https://www.douyin.com/user/ID" -n 500 -o results.csv
"""

import sys
import csv
import json
import time
import re
import argparse
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ── 配置 ─────────────────────────────────────────────────────────

USER_DATA_DIR = Path(__file__).parent / "user_data"
USER_DATA_DIR.mkdir(exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1440, "height": 900}
SCROLL_WAIT = 3.0
MAX_SCROLLS = 400
SAME_HEIGHT_LIMIT = 15


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="抖音用户视频爬虫 v4")
    p.add_argument("url", nargs="?", default="", help="抖音用户主页 URL")
    p.add_argument("--max-videos", "-n", type=int, default=0, help="最多抓取数（0=不限）")
    p.add_argument("--output", "-o", type=str, default="", help="CSV 输出路径")
    p.add_argument("--login", action="store_true", help="登录模式：打开浏览器登录抖音")
    p.add_argument("--headless", action="store_true", default=True, help="无头模式（默认）")
    p.add_argument("--no-headless", dest="headless", action="store_false", help="显示浏览器")
    p.add_argument("--cookie", "-c", type=str, default="", help="Cookie 字符串")
    return p.parse_args()


def make_output_path(name: str = "douyin_videos") -> Path:
    out = Path.cwd() / f"{name}.csv"
    cnt = 1
    while out.exists():
        out = Path.cwd() / f"{name}_{cnt}.csv"
        cnt += 1
    return out


# ══════════════════════════════════════════════════════════════════
# Stealth 补丁
# ══════════════════════════════════════════════════════════════════

STEALTH_SCRIPT = r"""
Object.defineProperty(navigator, 'webdriver', { get: () => false });
Object.defineProperty(navigator, 'plugins', {
    get: () => [1,2,3,4,5].map(() => ({ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' })),
});
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => [1,2,3,4].map(() => ({ type: 'application/pdf', suffixes: 'pdf' })),
});
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] });
if (!window.chrome?.runtime) {
    const rt = { connect:()=>({onMessage:{addListener:f=>f},postMessage:()=>({})}),
                 sendMessage:(m,cb)=>cb&&cb({}), onMessage:{addListener:f=>f},
                 getManifest:()=>({name:'',version:'0',manifest_version:3}),
                 id:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' };
    Object.defineProperty(window, 'chrome', { get:()=>({runtime:rt,loadTimes:()=>{}}) });
}
try { const gp = WebGLRenderingContext.prototype.getParameter;
    if (gp) { WebGLRenderingContext.prototype.getParameter = function(p) {
        if (p===37445) return 'Intel Inc.'; if (p===37446) return 'Intel Iris OpenGL Engine';
        return gp.call(this,p); }; }
} catch(e){}
try { if (navigator.permissions?.query) { const q=navigator.permissions.query;
    navigator.permissions.query = (p) => p.name==='notifications'
        ? Promise.resolve({state:'prompt'}) : q.call(navigator.permissions,p); }
} catch(e){}
try { if (navigator.getBattery) { navigator.getBattery = () =>
    Promise.resolve({charging:true,level:0.87,chargingTime:0,dischargingTime:Infinity}); }
} catch(e){}
"""


# ══════════════════════════════════════════════════════════════════
# API 数据提取
# ══════════════════════════════════════════════════════════════════

def extract_videos(data) -> list[dict] | None:
    """从 API JSON 响应提取视频列表"""
    try:
        if isinstance(data, str):
            data = json.loads(data)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    aweme_list = (data.get("aweme_list") or data.get("awemes")
                  or (data.get("data") or {}).get("aweme_list"))
    if not aweme_list or not isinstance(aweme_list, list):
        return None

    results = []
    for item in aweme_list:
        try:
            aid = str(item.get("aweme_id") or "")
            desc = (item.get("desc") or "").strip()
            if not aid:
                continue
            video_info = item.get("video") or {}

            # 尝试多种清晰度（download_addr 通常带音频，优先用）
            play_url = ""
            is_hd = False
            for quality_key in ["download_addr", "play_addr_h264", "play_addr", "play_addr_265"]:
                addr = video_info.get(quality_key) or {}
                url_list = addr.get("url_list", [])
                if url_list:
                    play_url = url_list[0]
                    is_hd = quality_key in ("play_addr_265", "play_addr_h264")
                    break

            results.append({
                "aweme_id": aid,
                "title": desc or "（无标题）",
                "url": f"https://www.douyin.com/video/{aid}",
                "play_url": play_url,
                "is_hd": is_hd,
                "author": (item.get("author") or {}).get("nickname", ""),
                "create_time": item.get("create_time", 0),
            })
        except Exception:
            continue
    return results if results else None


# ══════════════════════════════════════════════════════════════════
# 登录模式
# ══════════════════════════════════════════════════════════════════

def login_mode():
    print("=" * 60)
    print("  登录模式")
    print("  浏览器已打开，请在页面中登录抖音")
    print("  登录后关闭浏览器窗口，登录态自动保存到 user_data/")
    print("=" * 60)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(USER_DATA_DIR), channel="msedge", headless=False,
            viewport=VIEWPORT, user_agent=USER_AGENT,
            locale="zh-CN", timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled"],
        )
        p = ctx.pages[0] if ctx.pages else ctx.new_page()
        p.add_init_script(STEALTH_SCRIPT)
        p.goto("https://www.douyin.com", wait_until="networkidle")
        print("\n👆 登录完成后关闭浏览器窗口即可")
        try:
            while ctx.pages and ctx.pages[0]:
                ctx.pages[0].wait_for_timeout(5000)
        except Exception:
            pass
        ctx.close()
        print("✅ 登录态已保存到:", USER_DATA_DIR)


# ══════════════════════════════════════════════════════════════════
# 核心爬虫
# ══════════════════════════════════════════════════════════════════

def scrape_douyin(url: str, max_videos: int = 0,
                  headless: bool = True, cookie_str: str = "") -> list[dict]:
    """
    打开用户主页 → 拦截 API → 滚动 → byted_acrawler 签名翻页
    """
    all_videos: list[dict] = []
    seen_ids: set[str] = set()
    api_called = False
    empty_api_count = 0
    sec_uid = ""
    m = re.search(r"user/([A-Za-z0-9_\-]+)", url)
    if m:
        sec_uid = m.group(1)

    print(f"📁 用户数据目录: {USER_DATA_DIR}")

    with sync_playwright() as pw:
        # ── 持久化浏览器上下文 ──
        ctx = pw.chromium.launch_persistent_context(
            str(USER_DATA_DIR), channel="msedge",
            headless=headless, viewport=VIEWPORT,
            user_agent=USER_AGENT, locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled",
                   "--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.add_init_script(STEALTH_SCRIPT)

        # Cookie
        if cookie_str:
            domain = urlparse(url).hostname or "douyin.com"
            for item in cookie_str.split(";"):
                if "=" not in item:
                    continue
                n, v = item.strip().split("=", 1)
                try:
                    ctx.add_cookies([{"name": n, "value": v,
                                      "domain": f".{domain}", "path": "/"}])
                except Exception:
                    pass

        # 登录态检查
        logged_in = any(k in c["name"].lower() for c in ctx.cookies()
                        for k in ("sessionid", "sid_guard", "sid"))
        print("✅ 已检测到登录态" if logged_in else "ℹ️  未登录，抓取公开视频")

        # ── API 拦截器 ──
        first_api_url = [None]  # 容器：存放第一条 post API URL

        def on_response(response):
            nonlocal empty_api_count, api_called
            url = response.url
            if "/aweme/v1/web/aweme/post" not in url:
                return
            # 记录第一条
            if first_api_url[0] is None:
                first_api_url[0] = url
            api_called = True
            try:
                data = response.json()
            except Exception:
                return
            videos = extract_videos(data)
            if not videos:
                return
            new = 0
            for v in videos:
                if v["aweme_id"] not in seen_ids:
                    seen_ids.add(v["aweme_id"])
                    all_videos.append(v)
                    new += 1
            if new > 0:
                empty_api_count = 0
                print(f"  📡 新增 {new:3d} 条（累计 {len(all_videos):4d}）", flush=True)
            else:
                empty_api_count += 1

        page.on("response", on_response)

        # ── 打开页面 ──
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except PlaywrightTimeout:
            print("⚠️  页面加载超时")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass
        time.sleep(3)

        # ── 若未触发 API，刷新重试 ──
        if not api_called:
            print("🔄 刷新页面 …")
            try:
                page.reload(wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                pass
            time.sleep(3)

        # ── 自动滚动 ──
        if len(all_videos) > 0:
            print(f"\n📜 开始滚动（当前 {len(all_videos)} 条）")

        scroll_count = last_height = same_height = 0
        while True:
            if max_videos > 0 and len(all_videos) >= max_videos:
                print(f"\n✅ 已达数量上限 ({max_videos})")
                break
            if scroll_count >= MAX_SCROLLS:
                break
            if same_height >= SAME_HEIGHT_LIMIT:
                print("\n🔚 页面高度不变")
                break
            if empty_api_count >= 3 and api_called:
                break

            scroll_count += 1
            page.evaluate("window.scrollBy(0, document.documentElement.clientHeight * 1.5)")
            time.sleep(SCROLL_WAIT)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeout:
                pass
            ch = page.evaluate("document.documentElement.scrollHeight")
            same_height = same_height + 1 if ch == last_height else 0
            last_height = ch

        # ── 利用拦截到的 API URL 直接翻页 ──
        if first_api_url[0] and sec_uid:
            print(f"\n🔄 利用已签名的 API URL 翻页（替换 max_cursor）…")
            api_url_template = first_api_url[0]
            # 提取当前 max_cursor
            mc_match = re.search(r'max_cursor=(\d+)', api_url_template)
            if mc_match:
                old_cursor = mc_match.group(1)
                fetch_count = 0
                cursor_val = old_cursor
                consecutive_empty = 0

                while fetch_count < 80:
                    if max_videos > 0 and len(all_videos) >= max_videos:
                        print(f"\n✅ 已达数量上限 ({max_videos})")
                        break
                    if consecutive_empty >= 6:
                        print("\n🔚 连续无新数据")
                        break

                    fetch_count += 1
                    # 替换 max_cursor 为新值
                    fetch_url = api_url_template.replace(
                        f'max_cursor={old_cursor}', f'max_cursor={cursor_val}')

                    result = page.evaluate("""async (url) => {
                        try {
                            const r = await fetch(url, {credentials:'include',
                                headers:{'Accept':'application/json'}});
                            const t = await r.text();
                            return t;
                        } catch(e) { return 'ERR:'+e.message; }
                    }""", fetch_url)

                    if not result or result.startswith("ERR:"):
                        print(f"  ⚠️  翻页{fetch_count}: {(result or '')[:80]}")
                        break

                    try:
                        data = json.loads(result)
                        s, hm, nc = data.get("status_code"), data.get("has_more"), data.get("max_cursor")
                        al = len(data.get("aweme_list") or [])
                        print(f"  📊 {fetch_count:2d}: status={s} has_more={hm} cursor={nc} items={al}", end="")
                    except json.JSONDecodeError:
                        print(f"  ⚠️  翻页{fetch_count}: JSON 解析失败")
                        break

                    has_more = bool(data.get("has_more", 0))
                    new_cursor = str(data.get("max_cursor") or "")
                    page_videos = extract_videos(data)
                    new_count = 0
                    if page_videos:
                        for v in page_videos:
                            if v["aweme_id"] not in seen_ids:
                                seen_ids.add(v["aweme_id"])
                                all_videos.append(v)
                                new_count += 1
                        if new_count > 0:
                            consecutive_empty = 0
                            print(f" +{new_count:3d}（累计 {len(all_videos):4d}）", flush=True)
                        else:
                            consecutive_empty += 1
                            print(f"（无新增）")
                    else:
                        consecutive_empty += 1
                        print(f"（空数据）")

                    if not has_more:
                        print("  🔚 has_more=0，无更多视频")
                        break
                    if new_cursor and new_cursor != cursor_val:
                        cursor_val = new_cursor
                    elif consecutive_empty >= 3:
                        break

        ctx.close()

    return all_videos


# ══════════════════════════════════════════════════════════════════
# CSV 输出
# ══════════════════════════════════════════════════════════════════

def save_csv(videos: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["序号", "视频标题", "播放链接", "视频直链(可下载)", "画质", "视频ID", "作者"])
        for i, v in enumerate(videos, 1):
            quality = "高清" if v.get("is_hd") else "标清"
            w.writerow([i, v["title"], v["url"], v.get("play_url", ""), quality,
                        v.get("aweme_id", ""), v.get("author", "")])
    print(f"\n💾 已保存 {len(videos)} 条 → {path}")


# ══════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    if args.login:
        login_mode()
        return

    url = args.url.strip().rstrip("/")
    if not url:
        print("❌ 请提供用户 URL，或使用 --login 先登录")
        print("   用法: python douyin_spider.py <用户主页URL>")
        print("   首次使用: python douyin_spider.py --login")
        sys.exit(1)
    if "douyin.com" not in url:
        print("❌ URL 格式不正确，需包含 douyin.com")
        sys.exit(1)

    out_path = (Path(args.output).with_suffix(".csv") if args.output
                else make_output_path(f"douyin_{url.split('/')[-1].split('?')[0][:12]}"))

    print("=" * 60)
    print("  抖音用户视频爬虫 v4")
    print("  策略: Edge + 登录态 + byted_acrawler 签名翻页")
    print("=" * 60)

    try:
        videos = scrape_douyin(url, args.max_videos, args.headless, args.cookie)
    except Exception:
        traceback.print_exc()
        print("\n❌ 爬取出错")
        sys.exit(1)

    if not videos:
        print("\n⚠️  未获取到视频")
        print("   建议: python douyin_spider.py --login 先登录")
        print("   或: python douyin_spider.py <URL> --no-headless 手动过验证")
        sys.exit(1)

    if args.max_videos > 0 and len(videos) > args.max_videos:
        videos = videos[:args.max_videos]

    save_csv(videos, out_path)
    print(f"\n🎉 完成！共 {len(videos)} 条视频")


if __name__ == "__main__":
    main()
