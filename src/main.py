from datetime import datetime, timedelta
import logging
import os
import shutil

from bing_new import bing_scrape_stock_news
from finmind import finmind_data
from tqdm import tqdm
from yfinance import yfinance_data

# 1. 建立 logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 2. 檔案 Handler：INFO 以上全部寫入 process.log
file_handler = logging.FileHandler('logs/process.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)  # 所有 INFO、WARNING、ERROR…都會寫入檔案
file_formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 3. 終端機 Handler：只顯示 INFO（不含 WARNING, ERROR）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # 只顯示 INFO
console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)

# 只讓 INFO 等級印到 console，其它不印
def filter_info(record):
    return record.levelno == logging.INFO

console_handler.addFilter(filter_info)

logger.addHandler(console_handler)


if __name__ == '__main__':
    # 1. 透過圖形介面輸入股票清單
    import tkinter as tk
    from tkinter import ttk
    from pathlib import Path

    # pathlib > os.path：可讀性高、跨平台一致
    BASE_DIR = Path(__file__).resolve().parent
    PARENT_DIR = BASE_DIR.parent
    STOCKS_PATH = PARENT_DIR / "stocks.txt"
    # 讀取紀錄
    default_stocks = []
    if os.path.exists(STOCKS_PATH):
        with open(STOCKS_PATH, "r", encoding="utf-8") as f:
            default_stocks = [line.strip() for line in f if line.strip()]

    root = tk.Tk()
    root.title("選擇股票")
    vars = []
    for item in default_stocks:
        var = tk.BooleanVar(value=True)  # 預設勾選
        chk = ttk.Checkbutton(root, text=item, variable=var)
        chk.pack(anchor="w")
        vars.append((var, item))
    entry = ttk.Entry(root)
    entry.pack()
    def on_ok():
        stocks = [item for var, item in vars if var.get()]
        new_item = entry.get().strip()
        if new_item:
            stocks.append(new_item)
        with open(STOCKS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(stocks))
        root.destroy()
        # 接續原本的資料處理流程
        base_dir = r".\data"
        one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        finmind_token = None

        for stock_str in tqdm(stocks, desc="股票處理進度"):
            stock_id, stock_name = stock_str.split("_", 1)
            tqdm.write(f"正在處理：{stock_id} {stock_name}")
            sub_dir = os.path.join(base_dir, f"{stock_id}_{stock_name}")
            os.makedirs(sub_dir, exist_ok=True)

            yfinance_data(
                stock_id=stock_id,
                output_dir=sub_dir,
            )
            finmind_data(
                stock_id=stock_id,
                output_dir=sub_dir,
                one_year_ago=one_year_ago,
                finmind_token=finmind_token
            )
            """
            google_scrape_stock_news(
                keyword=f"{stock_id} {stock_name}",
                period='7d',
                start_page=1,
                end_page=1,
                output_dir=sub_dir
            )
            """
            bing_scrape_stock_news(
                keyword=f"{stock_id} {stock_name}",
                max_pages=2,
                sleep_sec=2,
                output_dir=sub_dir
            )

            zip_name = f"{stock_id}_{stock_name}"
            zip_path = os.path.join(base_dir, zip_name)
            shutil.make_archive(zip_path, 'zip', sub_dir)
            logging.info(f"[Info] 完成壓縮：{zip_path}.zip")

        logging.info("全部股票處理完成")

    ttk.Button(root, text="確定", command=on_ok).pack()
    root.mainloop()
