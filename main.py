"""
爬虫项目入口
依赖: playwright, beautifulsoup4
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


async def fetch_page(url: str) -> str:
    """使用 Playwright 获取页面 HTML"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        html = await page.content()
        await browser.close()
        return html


def parse_html(html: str) -> list[dict]:
    """使用 BeautifulSoup 解析 HTML 提取链接"""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        links.append({
            "text": a_tag.get_text(strip=True),
            "href": a_tag["href"],
        })
    return links


async def main():
    url = "https://example.com"
    print(f"Fetching: {url}")

    html = await fetch_page(url)
    links = parse_html(html)

    print(f"\nFound {len(links)} links:")
    for link in links[:10]:
        print(f"  - {link['text'] or '(no text)'}: {link['href']}")


if __name__ == "__main__":
    asyncio.run(main())
