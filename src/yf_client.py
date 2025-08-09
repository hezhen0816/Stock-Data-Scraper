import logging
import os

import pandas as pd
import yfinance as yf

from Indicator import apply_technical_indicators

# 保留原 yfinance_data 實作，僅搬移並確保不與外部套件命名衝突

def get_yfinance_data(stock_id):
    ticker_str = f"{stock_id}.TW"
    tkr = yf.Ticker(ticker_str)
    result = {}
    try:
        result['daily'] = tkr.history(period="1y", interval="1d", auto_adjust=True)
    except Exception as e:
        logging.error(f"yfinance daily 抓取失敗 {ticker_str}: {e}")
        result['daily'] = pd.DataFrame()
    try:
        result['1m_7d'] = tkr.history(period="7d", interval="1m", auto_adjust=True)
    except Exception as e:
        logging.error(f"yfinance 1m_7d 抓取失敗 {ticker_str}: {e}")
        result['1m_7d'] = pd.DataFrame()

    intervals = ["5m", "15m", "30m", "60m"]
    intraday = []
    for iv in intervals:
        try:
            df_iv = tkr.history(period="60d", interval=iv, auto_adjust=True)
            if not df_iv.empty:
                df_iv['Interval'] = iv
                intraday.append(df_iv)
        except Exception as e:
            logging.error(f"yfinance {iv} 抓取失敗 {ticker_str}: {e}")
    result['intraday'] = pd.concat(intraday) if intraday else pd.DataFrame()
    return result


def yfinance_data(stock_id, output_dir):
    # 調試資訊
    try:
        import yfinance as _yf_check
        logging.info(f"yfinance module file: {getattr(_yf_check, '__file__', None)}; has Ticker: {hasattr(_yf_check, 'Ticker')}")
    except Exception as _e:
        logging.warning(f"無法檢查 yfinance 模組: {_e}")
    price_data = get_yfinance_data(stock_id)
    for label, df in price_data.items():
        try:
            if df.empty:
                logging.info(f"{stock_id} {label} 無資料，跳過輸出")
                continue
            if label == 'intraday':
                temp_processed_dfs = {}
                for interval_value, group_df in df.groupby('Interval'):
                    group_df_ind = apply_technical_indicators(group_df.copy())
                    temp_processed_dfs[interval_value] = group_df_ind
                desired_interval_order = ["5m", "15m", "30m", "60m"]
                processed_intraday_dfs_ordered = [
                    temp_processed_dfs[iv] for iv in desired_interval_order if iv in temp_processed_dfs
                ]
                df_ind = pd.concat(processed_intraday_dfs_ordered) if processed_intraday_dfs_ordered else pd.DataFrame()
                if df_ind.empty:
                    logging.warning(f"{stock_id} intraday 無有效 interval，跳過輸出")
                    continue
            else:
                df_ind = apply_technical_indicators(df.copy())
            file_name = f"yfinance_{stock_id}_{label}.csv"
            os.makedirs(output_dir, exist_ok=True)
            df_ind.to_csv(os.path.join(output_dir, file_name), encoding='utf-8-sig')
            logging.info(f"已輸出 {file_name} 共 {len(df_ind)} 筆資料")
        except Exception as e:
            logging.error(f"yfinance 資料處理/輸出失敗 {stock_id} {label}: {e}")
