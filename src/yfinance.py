import logging
import os

import pandas as pd
import yfinance as yf

from Indicator import apply_technical_indicators
# --------------------------------------------------
# 一、yfinance 抓取函式
# --------------------------------------------------
def get_yfinance_data(stock_id):
    """
    使用 yfinance 擷取日線與不同分鐘級別資料
    :param stock_id: 台股代碼 (不含 .TW)
    :return: dict，包含 'daily', '1m_7d', 'intraday'
    - daily: 過去一年日線
    - 1m_7d: 過去七天的一分鐘線
    - intraday: 過去 60 天的 5m/15m/30m/60m
    """
    ticker_str = f"{stock_id}.TW"
    tkr = yf.Ticker(ticker_str)
    result = {}
    # 1. 日線：1 年內每日收盤價
    try:
        result['daily'] = tkr.history(period="1y", interval="1d", auto_adjust=True)
    except Exception as e:
        logging.error(f"yfinance daily 抓取失敗 {ticker_str}: {e}")
        result['daily'] = pd.DataFrame()
    # 2. 一分鐘線：近 7 天
    try:
        result['1m_7d'] = tkr.history(period="7d", interval="1m", auto_adjust=True)
    except Exception as e:
        logging.error(f"yfinance 1m_7d 抓取失敗 {ticker_str}: {e}")
        result['1m_7d'] = pd.DataFrame()
    # 3. 多頻率分鐘線：5m/15m/30m/60m
    intervals = ["5m", "15m", "30m", "60m"]
    intraday = []
    for iv in intervals:
        try:
            df_iv = tkr.history(period="60d", interval=iv, auto_adjust=True)
            if not df_iv.empty:
                df_iv['Interval'] = iv  # 標記級別
                intraday.append(df_iv)
        except Exception as e:
            logging.error(f"yfinance {iv} 抓取失敗 {ticker_str}: {e}")
    # 合併為單一 DataFrame
    result['intraday'] = pd.concat(intraday) if intraday else pd.DataFrame()
    return result


def yfinance_data(stock_id, output_dir):

    # --------------------------------------------------
    # 二、取得 yfinance 價格資料 (日線與多時間框 K 線)
    # --------------------------------------------------
    
    # 1. 擷取 yfinance 價格資料
    price_data = get_yfinance_data(stock_id)
    for label, df in price_data.items():
        try:
            if df.empty:
                logging.info(f"{stock_id} {label} 無資料，跳過輸出")
                continue  # 若無資料則跳過

            if label == 'intraday':
                # 對於 intraday 資料，需要按 Interval 分組計算指標，並保持期望的順序
                temp_processed_dfs = {}
                for interval_value, group_df in df.groupby('Interval'):
                    group_df_ind = apply_technical_indicators(group_df.copy())
                    temp_processed_dfs[interval_value] = group_df_ind

                desired_interval_order = ["5m", "15m", "30m", "60m"]
                processed_intraday_dfs_ordered = [
                    temp_processed_dfs[iv]
                    for iv in desired_interval_order
                    if iv in temp_processed_dfs
                ]
                df_ind = pd.concat(processed_intraday_dfs_ordered) if processed_intraday_dfs_ordered else pd.DataFrame()
                if df_ind.empty:
                    logging.warning(f"{stock_id} intraday 無有效 interval，跳過輸出")
                    continue
            else:
                # 對於 'daily' 和 '1m_7d'，它們本身就是單一時間頻率，可以直接計算
                df_ind = apply_technical_indicators(df.copy())

            # 輸出 CSV 檔，採用 UTF-8 編碼並加上 BOM
            file_name = f"yfinance_{stock_id}_{label}.csv"
            os.makedirs(output_dir, exist_ok=True)
            df_ind.to_csv(os.path.join(output_dir, file_name), encoding='utf-8-sig')
            logging.info(f"已輸出 {file_name} 共 {len(df_ind)} 筆資料")
        except Exception as e:
            logging.error(f"yfinance 資料處理/輸出失敗 {stock_id} {label}: {e}")
# 測試
if __name__ == "__main__":
    # 測試用的主程式
    stock_id = "3379"
    output_dir = "./data/test"
    yfinance_data(stock_id, output_dir)
    print("yfinance 資料擷取完成。")
