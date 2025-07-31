import pandas as pd
import os
from Indicator import apply_technical_indicators
import logging
import yfinance as yf
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
    ticker = f"{stock_id}.TW"
    result = {}
    # 1. 日線：1 年內每日收盤價
    result['daily'] = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
    # 2. 一分鐘線：近 7 天
    result['1m_7d'] = yf.Ticker(ticker).history(period="7d", interval="1m", auto_adjust=True)
    # 3. 多頻率分鐘線：5m/15m/30m/60m
    intervals = ["5m", "15m", "30m", "60m"]
    intraday = []
    for iv in intervals:
        df_iv = yf.Ticker(ticker).history(period="60d", interval=iv, auto_adjust=True)
        df_iv['Interval'] = iv  # 標記級別
        intraday.append(df_iv)
    # 合併為單一 DataFrame
    result['intraday'] = pd.concat(intraday)
    return result


def yfinance_data(stock_id, output_dir):

    # --------------------------------------------------
    # 二、取得 yfinance 價格資料 (日線與多時間框 K 線)
    # --------------------------------------------------
    
    # 1. 擷取 yfinance 價格資料
    price_data = get_yfinance_data(stock_id)
    for label, df in price_data.items():
        if df.empty:
            continue  # 若無資料則跳過

        if label == 'intraday':
            # --- MODIFICATION START ---
            # 對於 intraday 資料，需要按 Interval 分組計算指標，並保持期望的順序

            temp_processed_dfs = {} # 用字典暫存處理好的 DataFrame，以 interval 字串為鍵

            # 1. 先對每個 interval 的資料計算指標
            #    groupby 預設會對鍵進行排序 (所以 interval_value 的順序可能是 '15m', '30m', '5m', '60m')
            for interval_value, group_df in df.groupby('Interval'):
                group_df_ind = apply_technical_indicators(group_df.copy())
                temp_processed_dfs[interval_value] = group_df_ind
            
            # 2. 按照期望的順序重新組合
            processed_intraday_dfs_ordered = []
            # 這個順序應該和 get_yfinance_data 中定義的 intervals 順序一致
            desired_interval_order = ["5m", "15m", "30m", "60m"] 

            for iv_desired in desired_interval_order:
                if iv_desired in temp_processed_dfs: # 確保該 interval 的資料存在
                    processed_intraday_dfs_ordered.append(temp_processed_dfs[iv_desired])
            
            # 3. 合併順序正確的 DataFrame 列表
            if processed_intraday_dfs_ordered:
                df_ind = pd.concat(processed_intraday_dfs_ordered)
            else:
                # 如果沒有任何 intraday 資料被處理 (例如 temp_processed_dfs 為空或所有 desired_interval_order 都不在其中)
                # 則 df_ind 為空的 DataFrame，避免後續 to_csv 出錯
                df_ind = pd.DataFrame() 
            # --- MODIFICATION END ---
        else:
            # 對於 'daily' 和 '1m_7d'，它們本身就是單一時間頻率，可以直接計算
            df_ind = apply_technical_indicators(df.copy())

        # 輸出 CSV 檔，採用 UTF-8 編碼並加上 BOM
        if not df_ind.empty: # 確保 df_ind 不是空的才進行儲存
            file_name = f"yfinance_{stock_id}_{label}.csv"
            os.makedirs(output_dir, exist_ok=True)
            df_ind.to_csv(os.path.join(output_dir, file_name), encoding='utf-8-sig')
            
            logging.info(f"已輸出 {file_name} 共 {len(df_ind)} 筆資料")

        elif label == 'intraday' and not processed_intraday_dfs_ordered: # 針對 intraday 特殊情況給予提示
            logging.error(f"警告：沒有為 {label} ({stock_id}) 產生有效的資料進行輸出。")
#測試
if __name__ == "__main__":
    # 測試用的主程式
    stock_id = "3379"  # 台積電
    output_dir = "./data/test"
    yfinance_data(stock_id, output_dir)
    print("yfinance 資料擷取完成。")
