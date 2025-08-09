import logging
import os

import pandas as pd  # 資料處理套件
import requests  # HTTP 請求套件，用於呼叫 API
# --------------------------------------------------
# 一、FinMind API 抓取函式
# --------------------------------------------------
def get_finmind_data(dataset, data_id=None, start_date=None, token=None):
    """
    使用 FinMind API 擷取指定資料集
    :param dataset: 資料集名稱
    :param data_id: 資料 ID（如股票代碼）
    :param start_date: 起始日期，格式 'YYYY-MM-DD'
    :param token: API Token
    :return: pandas DataFrame，
            若含 date 欄位，自動轉為時間索引
    """
    # 組成參數字典
    params = {"dataset": dataset, "data_id": data_id, "start_date": start_date, "token": token}
    # 發送 GET 請求
    resp = requests.get("https://api.finmindtrade.com/api/v4/data", params)
    if resp.status_code == 200:
        data = resp.json().get("data", [])  # 取回 data
        df = pd.DataFrame(data)
        # 若包含 date 欄位，轉為時間索引
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        return df
    else:
        # 印出錯誤並回傳空 DataFrame
        logging.error(f"FinMind API 錯誤 {resp.status_code}: {resp.text}")
        return pd.DataFrame()


def finmind_data(stock_id, one_year_ago, finmind_token, output_dir):
# --------------------------------------------------
# 二、取得 FinMind API 資料(法人、財務、新聞資料)
# --------------------------------------------------  

    finmind_datasets = [
        {"dataset": "TaiwanStockPER", "data_id": stock_id, "start_date": one_year_ago},
        {"dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": stock_id, "start_date": one_year_ago},
        {"dataset": "TaiwanStockMarginPurchaseShortSale", "data_id": stock_id, "start_date": one_year_ago},
        {"dataset": "TaiwanStockMonthRevenue", "data_id": stock_id, "start_date": one_year_ago},
        {"dataset": "TaiwanStockFinancialStatements", "data_id": stock_id, "start_date": one_year_ago},
        {"dataset": "TaiwanStockTotalReturnIndex", "data_id": "TAIEX", "start_date": one_year_ago}
    ]
    for item in finmind_datasets:
        df_fm = get_finmind_data(
            item['dataset'],
            data_id=item.get('data_id'),
            start_date=item.get('start_date'),
            token=finmind_token
        )
        if df_fm.empty:
            continue
        # 輸出 FinMind 資料
    file_name = f"FinMind_{item['dataset']}_{item.get('data_id', '')}.csv"
    os.makedirs(output_dir, exist_ok=True)
    df_fm.to_csv(os.path.join(output_dir, file_name), encoding='utf-8-sig')
    logging.info(f"已輸出 {file_name} 共 {len(df_fm)} 筆資料")



