import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from urllib.parse import urlparse
from newspaper import Article
import os

def get_full_article_content(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logging.error(f"無法下載: {url} ({e})")
        return ""
    soup = BeautifulSoup(html, 'lxml')
    domain = urlparse(url).netloc.lower()
    content = []
    if 'stock.yahoo' in domain:
        tag = soup.find('article')
        selector = tag.find_all('p') if tag else []
    elif 'money.udn.com' in domain:
        body = soup.find('div', id='story_body_content')
        selector = body.find_all('p') if body else []
    else:
        selector = []
    for p in selector:
        text = p.get_text(strip=True)
        if text:
            content.append(text)
    if not content:
        try:
            article = Article(url, language='zh')
            article.download(input_html=html)
            article.parse()
            content = article.text.split('\n')
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
    for page in range(max_pages):
        offset = page * 10
        url = f"https://www.bing.com/news/search?q={keyword}&qft=interval%3d%228%22&first={offset+1}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to retrieve page {page+1}, status code: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "lxml")
        news_cards = soup.find_all("a", {"class": "title"})
        for a in news_cards:
            title = a.get_text(strip=True)
            link = a.get("href")
            content = get_full_article_content(link)
            publish_date = ""
            # 1. 從 a 元素往上一層找到父 div
            parent_div = a.find_parent("div")
            date = ""
            if parent_div:
                # 2. 在同一層 div 內找 <span aria-label>
                span = parent_div.find("span", attrs={"aria-label": True})
                if span:
                    date = span["aria-label"]
                    publish_date = parse_bing_date(date)

            results.append({
                'publish_date': publish_date,  # 新增標準化日期欄位
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
    #print(df)


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
