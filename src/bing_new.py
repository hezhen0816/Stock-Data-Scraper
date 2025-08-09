import logging
import os
import time
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from newspaper import Article

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

def _sleep_backoff(attempt: int, base: float = 1.0, factor: float = 1.6, jitter: float = 0.2):
    delay = base * (factor ** max(0, attempt - 1))
    time.sleep(delay + jitter)

FALLBACK_REFERER = "https://www.bing.com/news/"

def _sanitize_header_value(val: str) -> str:
    try:
        val.encode('latin-1')
        return val
    except Exception:
        return FALLBACK_REFERER

def _fetch_with_retry(session: requests.Session, url: str, max_retries: int = 3, timeout: int = 15, referer: str | None = None):
    for attempt in range(1, max_retries + 1):
        try:
            headers = {}
            if referer:
                headers["Referer"] = _sanitize_header_value(referer)
            resp = session.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt >= max_retries:
                raise
            logging.warning(f"請求失敗，第 {attempt} 次重試：{url}，原因：{e}")
            _sleep_backoff(attempt)

def get_full_article_content(url, session: requests.Session, timeout=15, search_referer: str | None = None):
    try:
        resp = _fetch_with_retry(session, url, max_retries=3, timeout=timeout, referer=search_referer)
        html = resp.text
    except Exception as e:
        logging.error(f"無法下載: {url} ({e})")
        return ""
    soup = BeautifulSoup(html, 'lxml')
    domain = urlparse(url).netloc.lower()
    content: list[str] = []

    # 站點特化選擇器
    selector_nodes = []
    if 'stock.yahoo' in domain or 'tw.stock.yahoo' in domain:
        tag = soup.find('article')
        selector_nodes = tag.find_all('p') if tag else []
    elif 'money.udn.com' in domain or 'udn.com' in domain:
        body = soup.find('div', id='story_body_content') or soup.find('section', id='article-body')
        selector_nodes = body.find_all('p') if body else []
    elif 'ctee.com.tw' in domain:
        body = soup.select_one('#newsContent') or soup.select_one('.article-main') or soup.select_one('.article_content')
        selector_nodes = body.find_all('p') if body else []
    elif 'chinatimes.com' in domain:
        body = soup.select_one('div.article-body') or soup.select_one('#article-body')
        selector_nodes = body.find_all('p') if body else []
    elif 'moneydj.com' in domain:
        body = soup.select_one('#divMain') or soup.select_one('.article') or soup.select_one('#news')
        selector_nodes = body.find_all('p') if body else []
    elif 'ltn.com.tw' in domain:
        body = soup.select_one('div.text') or soup.select_one('#newstext')
        selector_nodes = body.find_all('p') if body else []
    elif 'cnyes.com' in domain:
        body = soup.select_one('article') or soup.select_one('div._2E8yJ9') or soup.select_one('div.article')
        selector_nodes = body.find_all('p') if body else []
    else:
        body = (
            soup.find('article') or
            soup.select_one('div.article') or
            soup.select_one('div.article-content') or
            soup.select_one('div.story')
        )
        selector_nodes = body.find_all('p') if body else []

    for p in selector_nodes:
        text = p.get_text(strip=True)
        if text:
            content.append(text)
    if not content:
        try:
            article = Article(url, language='zh')
            article.download(input_html=html)
            article.parse()
            content = [line.strip() for line in article.text.split('\n') if line.strip()]
        except Exception as e:
            logging.error(f"newspaper3k 解析失敗: {url} ({e})")
    filtered = [line for line in content if len(line) > 10]
    return '\n'.join(filtered).strip()

def parse_bing_date(date_text):
    import re
    from datetime import datetime, timedelta
    date_text = date_text.strip()
    now = datetime.now()
    # 「x 小時前」
    m = re.match(r"(\d+)\s*小時前", date_text)
    if m:
        dt = now - timedelta(hours=int(m.group(1)))
        return dt.strftime("%Y-%m-%d")
    # 「x 分鐘前」
    m = re.match(r"(\d+)\s*分鐘前", date_text)
    if m:
        dt = now - timedelta(minutes=int(m.group(1)))
        return dt.strftime("%Y-%m-%d")
    # 「x 天前」
    m = re.match(r"(\d+)\s*天前", date_text)
    if m:
        dt = now - timedelta(days=int(m.group(1)))
        return dt.strftime("%Y-%m-%d")
    # 2025年5月21日 形式
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_text)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return dt.strftime("%Y-%m-%d")
    # 其他格式直接回傳原始
    return date_text

def bing_scrape_stock_news(keyword, output_dir, max_pages=2, sleep_sec=2):
    results = []
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    search_base = FALLBACK_REFERER
    session.headers.setdefault("Referer", search_base)

    for page in range(max_pages):
        offset = page * 10
        url = f"https://www.bing.com/news/search?q={keyword}&qft=interval%3d%228%22&first={offset+1}"
        try:
            resp = _fetch_with_retry(session, url, max_retries=3, timeout=15, referer=search_base)
        except Exception as e:
            logging.error(f"Bing 第 {page+1} 頁下載失敗: {e}")
            time.sleep(sleep_sec)
            continue
        soup = BeautifulSoup(resp.text, "lxml")
        news_cards = soup.find_all("a", {"class": "title"})
        for a in news_cards:
            title = a.get_text(strip=True)
            link = a.get("href")
            if not link:
                continue
            content = get_full_article_content(link, session=session, timeout=15, search_referer=search_base)
            time.sleep(0.4)
            publish_date = ""
            parent_div = a.find_parent("div")
            date = ""
            if parent_div:
                span = parent_div.find("span", attrs={"aria-label": True})
                if span:
                    date = span["aria-label"]
                    publish_date = parse_bing_date(date)

            results.append({
                'publish_date': publish_date,
                'date': date,
                "title": title,
                "link": link,
                'content': content
            })
        time.sleep(sleep_sec)

    df = pd.DataFrame(results)

    safe = keyword.replace(' ', '_')
    output_file = f"{safe}_news.csv"
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, output_file), index=False, encoding='utf-8-sig')
    logging.info(f"共 {len(df)} 筆")
    # print(df)


if __name__ == "__main__":
    # 指定搜尋關鍵字
    keyword = "2308 台達電"
    # 指定輸出目錄
    output_dir = r"C:\Users\hezhe\OneDrive\桌面"  # 你可以改成你想存的路徑
    # 呼叫函式
    bing_scrape_stock_news(
        keyword=keyword,
        output_dir=output_dir,
        max_pages=5,
        sleep_sec=2
    )
    print("Bing 新聞爬蟲執行完成")
