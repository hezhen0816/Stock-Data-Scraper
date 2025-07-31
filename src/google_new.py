import os
import time
from urllib.parse import urlparse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from GoogleNews import GoogleNews
from newspaper import Article
import logging


def get_full_article_content(url, timeout=10):
    """
    下載並解析文章完整內文。根據網域選擇解析策略，並以 newspaper3k 作為備援。

    參數:
      url: 文章連結
      timeout: HTTP 請求超時秒數
    回傳:
      文章文字內容 (字串)
    """
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

    # 不同新聞站的 DOM 結構
    if 'stock.yahoo' in domain:
        tag = soup.find('article')
        selector = tag.find_all('p') if tag else []
    elif 'money.udn.com' in domain:
        body = soup.find('div', id='story_body_content')
        selector = body.find_all('p') if body else []
    else:
        selector = []

    # 優先使用 BeautifulSoup 擷取段落
    for p in selector:
        text = p.get_text(strip=True)
        if text:
            content.append(text)

    # 若未透過 BS4 擷取到，轉由 newspaper3k
    if not content:
        try:
            article = Article(url, language='zh')
            article.download(input_html=html)
            article.parse()
            content = article.text.split('\n')
        except Exception as e:
            logging.error(f"newspaper3k 解析失敗: {url} ({e})")

    # 回傳純文字，並去除過短段落
    filtered = [line for line in content if len(line) > 10]
    return '\n'.join(filtered).strip()


import re
from datetime import datetime, timedelta

def parse_news_date(date_str):
    date_str = date_str.strip()
    now = datetime.now()
    # 處理「x 天前」
    m = re.match(r'(\d+)\s*天前', date_str)
    if m:
        days = int(m.group(1))
        dt = now - timedelta(days=days)
        return dt.strftime('%Y-%m-%d')
    # 處理「x 小時前」
    m = re.match(r'(\d+)\s*小時前', date_str)
    if m:
        hours = int(m.group(1))
        dt = now - timedelta(hours=hours)
        return dt.strftime('%Y-%m-%d')
    # 處理「x 分鐘前」
    m = re.match(r'(\d+)\s*分鐘前', date_str)
    if m:
        mins = int(m.group(1))
        dt = now - timedelta(minutes=mins)
        return dt.strftime('%Y-%m-%d')
    # 處理 YYYY/MM/DD 或 YYYY-MM-DD 格式
    m = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
    if m:
        try:
            dt = datetime.strptime(date_str, '%Y/%m/%d')
        except ValueError:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    # 其他未能判讀的格式，直接傳回原值
    return date_str


def google_scrape_stock_news(
    keyword,
    period='7d',
    start_page=1,
    end_page=2,
    output_dir='output',
    output_file=None,
    sleep_interval=5
):
    """
    擷取指定股票新聞並輸出 CSV。

    參數:
      keyword: 搜尋關鍵字 (e.g. '2354 鴻準')
      period: 時間範圍 ('7d','1m')
      start_page: 起始頁數
      end_page: 結束頁數
      output_dir: 輸出資料夾
      output_file: 輸出檔名 (不含路徑)
      sleep_interval: 分頁請求間隔 (秒)
    """
    # 建立輸出資料夾
    os.makedirs(output_dir, exist_ok=True)

    news_api = GoogleNews(lang='zh-TW', region='TW')
    news_api.set_period(period)
    news_api.search(keyword)

    records = []
    logging.info(f"搜尋: '{keyword}' | 範圍: {period} | 頁 {start_page}~{end_page}")

    for page in range(start_page, end_page + 1):
        logging.info(f"擷取第 {page} 頁...")
        news_api.get_page(page)
        items = news_api.results()
        if not items:
            logging.info(f"第 {page} 頁無結果，提前結束。")
            break

        for item in items:
            title = item.get('title', '').strip()
            date = item.get('date', '').strip()
            link = item.get('link', '').strip()
            if not link:
                continue
            logging.info(f"下載內文: {title}")
            content = get_full_article_content(link)
            publish_date = parse_news_date(date)  # ← 這行是關鍵！
            records.append({
                'publish_date': publish_date,  # 新增標準化日期欄位
                'date': date,
                'title': title,
                'link': link,
                'content': content
            })


        time.sleep(sleep_interval)

    df = pd.DataFrame(records)

    # 決定輸出檔名
    if not output_file:
        safe = keyword.replace(' ', '_')
        output_file = f"{safe}_news.csv"
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, output_file), index=False, encoding='utf-8-sig')
    logging.info(f"共 {len(df)} 筆")