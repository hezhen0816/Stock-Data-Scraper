from datetime import datetime, timedelta
import logging
import os
import shutil
from pathlib import Path
import argparse
import traceback

from bing_new import bing_scrape_stock_news
from finmind import finmind_data
from tqdm import tqdm
from yf_client import yfinance_data


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # 避免重複加入 handler
    if logger.handlers:
        return logger
    # 確保資料夾存在
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # 檔案 Handler：INFO 以上寫入
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    # 終端機 Handler：顯示 INFO 與以上（包含 WARNING/ERROR）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    return logger


def parse_stocks_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    stocks: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            # 僅接受含有 "_" 的格式，例如 2317_鴻海
            if "_" in s:
                stocks.append(s)
    return stocks


def run_pipeline(stocks: list[str], data_dir: Path, finmind_token: str | None, max_pages: int, sleep_sec: int, zip_output: bool = True):
    data_dir.mkdir(parents=True, exist_ok=True)
    one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

    for stock_str in tqdm(stocks, desc="股票處理進度"):
        try:
            if "_" not in stock_str:
                logging.info(f"跳過不合法的股票格式: {stock_str}")
                continue
            stock_id, stock_name = stock_str.split("_", 1)
            tqdm.write(f"正在處理：{stock_id} {stock_name}")
            sub_dir = data_dir / f"{stock_id}_{stock_name}"
            sub_dir.mkdir(parents=True, exist_ok=True)

            # yfinance
            yfinance_data(stock_id=stock_id, output_dir=str(sub_dir))
            # FinMind
            finmind_data(stock_id=stock_id, output_dir=str(sub_dir), one_year_ago=one_year_ago, finmind_token=finmind_token)
            # Bing 新聞
            bing_scrape_stock_news(keyword=f"{stock_id} {stock_name}", max_pages=max_pages, sleep_sec=sleep_sec, output_dir=str(sub_dir))

            if zip_output:
                zip_name = f"{stock_id}_{stock_name}"
                zip_path = data_dir / zip_name
                shutil.make_archive(str(zip_path), 'zip', str(sub_dir))
                logging.info(f"[Info] 完成壓縮：{zip_path}.zip")
        except Exception as e:
            logging.error(f"處理 {stock_str} 失敗: {e}")
            logging.error(traceback.format_exc())


if __name__ == '__main__':
    BASE_DIR = Path(__file__).resolve().parent
    PARENT_DIR = BASE_DIR.parent
    DATA_DIR = PARENT_DIR / "data"
    # 使用既有的 Logs 目錄，若不存在則建立
    LOG_DIR = PARENT_DIR / "Logs"
    logger = setup_logger(LOG_DIR / "process.log")

    parser = argparse.ArgumentParser(description="股票資料抓取與整理")
    parser.add_argument("--gui", action="store_true", help="使用 GUI 勾選股票清單（預設啟用）")
    parser.add_argument("--headless", action="store_true", help="不顯示 GUI，直接執行")
    parser.add_argument("--stocks", type=str, default=None, help="以逗號分隔的清單，如 2317_鴻海,00922_國泰台灣領袖50")
    parser.add_argument("--stocks-file", type=str, default=str(PARENT_DIR / "stocks.txt"), help="stocks.txt 路徑")
    parser.add_argument("--finmind-token", type=str, default=None, help="FinMind API Token")
    parser.add_argument("--max-pages", type=int, default=2, help="Bing 新聞最大頁數")
    parser.add_argument("--sleep-sec", type=int, default=2, help="抓取間隔秒數")
    parser.add_argument("--no-zip", action="store_true", help="不要壓縮輸出資料夾")
    args = parser.parse_args()

    # 預設 GUI；除非明確指定 --headless
    if not args.headless:
        import tkinter as tk
        from tkinter import ttk

        STOCKS_PATH = Path(args.stocks_file)
        default_stocks = parse_stocks_file(STOCKS_PATH)
        # 若 --stocks 有提供，也加入預設列表
        if args.stocks:
            extra = [s.strip() for s in args.stocks.split(",") if s.strip()]
            # 去除重複，保留順序
            seen = set(default_stocks)
            merged = default_stocks[:]
            for s in extra:
                if s not in seen:
                    merged.append(s)
                    seen.add(s)
            default_stocks = merged

        root = tk.Tk()
        root.title("選擇股票")
        vars_ = []
        for item in default_stocks:
            var = tk.BooleanVar(value=True)  # 預設勾選
            chk = ttk.Checkbutton(root, text=item, variable=var)
            chk.pack(anchor="w")
            vars_.append((var, item))
        entry = ttk.Entry(root)
        entry.pack()

        def on_ok():
            # 勾選的清單
            stocks = [item for var, item in vars_ if var.get()]
            # 支援多筆輸入，以逗號/空白分隔；自動轉換「代碼 名稱」為「代碼_名稱」
            new_text = entry.get().strip()
            if new_text:
                raw_items = [p for p in [x.strip() for x in new_text.replace("\n", ",").split(",")] if p]
                normalized = []
                for s in raw_items:
                    if "_" in s:
                        normalized.append(s)
                    else:
                        parts = s.split()
                        if len(parts) >= 2:
                            normalized.append(parts[0] + "_" + "".join(parts[1:]))
                        else:
                            # 無法判讀的格式，原樣保留
                            normalized.append(s)
                stocks.extend(normalized)
            STOCKS_PATH.write_text("\n".join(stocks), encoding="utf-8")
            root.destroy()
            run_pipeline(stocks=stocks, data_dir=DATA_DIR, finmind_token=args.finmind_token, max_pages=args.max_pages, sleep_sec=args.sleep_sec, zip_output=not args.no_zip)
            logging.info("全部股票處理完成")

        ttk.Button(root, text="確定", command=on_ok).pack()
        root.mainloop()
    else:
        # Headless 模式
        stocks: list[str] = []
        if args.stocks:
            stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
        else:
            stocks = parse_stocks_file(Path(args.stocks_file))

        if not stocks:
            logging.info("未找到任何股票，請使用 --stocks 或提供 stocks.txt")
        else:
            run_pipeline(stocks=stocks, data_dir=DATA_DIR, finmind_token=args.finmind_token, max_pages=args.max_pages, sleep_sec=args.sleep_sec, zip_output=not args.no_zip)
            logging.info("全部股票處理完成")
