# 股市資料自動擷取與分析工具

## 專案簡介

本工具用於自動化擷取台股個股的價格、財務與新聞資料，並計算常用技術指標，最終將各項原始與衍生資料整理成 CSV 檔案，同時壓縮成 Zip，方便後續分析或機器學習。專案整合 **yfinance**、**FinMind API**、及 **Bing／Google 新聞** 爬蟲，並提供簡易 GUI 介面快速選取或新增股票清單。

截至 *2025‑07‑31* 的功能與相依套件列於下方，後續可依需要擴充。

## 功能特色

- **圖形介面選股**：以 `tkinter` 建立簡易 GUI；可勾選既有股票或輸入新股票 (`代號_名稱`)。
- **價格資料抓取**：
  - `yfinance.py`：擷取每日線、一分鐘線（近七日）及多頻率分鐘線（5m／15m／30m／60m）。
  - 自動計算移動平均、RSI、MACD、布林通道、ATR、OBV、VWAP 等技術指標。
- **財務與法人資訊**：
  - `finmind.py` 透過 FinMind API 下載法人買賣、財報與每月營收等資料。
- **新聞爬蟲**：
  - `bing_new.py`、`google_new.py` 根據關鍵字（股票代號＋名稱）抓取最近新聞並擷取全文。
- **批次處理與壓縮**：每檔股票會在 `./data/<代號_名稱>` 下生成多個 CSV，最後自動壓縮為 `<代號_名稱>.zip`。
- **可自訂輸出路徑**：可在 `main.py` 中調整 `base_dir` 變數。

## 安裝與環境需求

- Python 3.10 以上
- 建議使用 *virtualenv* 或 *conda* 環境管理

### 安裝步驟

```bash
git clone <your-repo-url>
cd <repo-root>
pip install -r requirements.txt  # 或手動安裝下表相依套件
```

| 套件              | 版本建議          | 用途                  |
| --------------- | ------------- | ------------------- |
| pandas          | 2.x           | 資料處理                |
| numpy           | 1.26.x        | 數值計算                |
| yfinance        | 0.2.x         | 取得 Yahoo Finance 價格 |
| requests        | 2.x           | HTTP 請求             |
| beautifulsoup4  | 4.x           | HTML 解析             |
| newspaper3k     | 0.2.x         | 新聞全文擷取              |
| GoogleNews      | 1.x           | Google 新聞搜尋         |
| tqdm            | 4.x           | 進度條                 |
| lxml            | 4.x           | HTML 解析             |
| tk              | (隨 Python 附帶) | GUI                 |
| python-dateutil | 2.x           | 日期處理                |
| logging         | (標準庫)         | 日誌                  |

> **FinMind API Token**\
> 請自行至 [https://finmindtrade.com/](https://finmindtrade.com/) 註冊並在 `main.py` 的 `finmind_token` 變數填入。

## 快速開始

1. 確認 `stocks.txt` 位於 *主程式 (**`main.py`**) 的上一層*，格式一行一檔：
   ```
   2330_台積電
   2308_台達電
   ```
2. 執行主程式：
   ```bash
   python main.py
   ```
3. 在彈出的 GUI 中勾選／輸入股票後按 **確定**，程式將自動開始擷取並於右側 Console 顯示進度。

## 輸出結果

所有擷取資料會存放於 `./data/<代號_名稱>/` 下，完成後會額外產生對應的 Zip 壓縮檔，並在 `logs/process.log` 記錄詳細過程。

## 專案結構

```
.
├── main.py
├── bing_new.py
├── google_new.py
├── finmind.py
├── Indicator.py
├── yfinance.py
├── data/                 # 產出資料夾
├── logs/process.log      # 執行日誌
└── stocks.txt            # 股票清單
```


