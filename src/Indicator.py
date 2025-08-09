import numpy as np  # 數值運算套件
import pandas as pd  # 資料處理套件

# --------------------------------------------------
# 三、技術指標計算函式
#    - MA, RSI, MACD, HV, BB, ATR, OBV, VWAP, Divergence
# --------------------------------------------------
def calculate_rsi(series, period=14):
    """
    計算 RSI（相對強弱指標）
    :param series: 價格序列 (pandas Series)
    :param period: 週期
    :return: RSI 值 (0-100)
    """
    delta = series.diff()  # 計算價差
    gain = delta.where(delta > 0, 0.0)  # 上漲部分
    loss = -delta.where(delta < 0, 0.0)  # 下跌部分
    # 使用 Wilder’s EMA 平滑
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series, fast=12, slow=26, signal=9):
    """
    計算 MACD 線、訊號線與柱狀圖
    :param series: 價格序列
    :param fast: 短期 EMA 參數
    :param slow: 長期 EMA 參數
    :param signal: 訊號線 EMA 週期
    :return: (macd_line, signal_line, hist)
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow  # 快線減慢線
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line  # 柱狀圖
    return macd_line, signal_line, hist

def calculate_hv(series, window=20, trading_days=252):
    """
    計算歷史波動率（HV）
    :param series: 價格序列
    :param window: 滾動視窗
    :param trading_days: 年化交易天數
    :return: 波動率序列
    """
    log_ret = np.log(series / series.shift(1))  # 日對數報酬
    # 標準差 * 根號年交易天數
    return log_ret.rolling(window).std() * np.sqrt(trading_days)

def calculate_bollinger(series, window=20, num_std=2):
    """
    計算布林通道
    :param series: 價格序列
    :param window: 移動平均視窗
    :param num_std: 標準差倍數
    :return: (中軌, 上軌, 下軌)
    """
    ma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return ma, upper, lower

def calculate_atr(df, period=14):
    """
    計算平均真實區間（ATR）
    :param df: DataFrame，需含 High/Low/Close
    :param period: 視窗
    :return: ATR 序列
    """
    high = df.get('max', df.get('High'))  # 兼容欄位名稱
    low = df.get('min', df.get('Low'))
    prev_close = df.get('close', df.get('Close')).shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calculate_obv(df):
    """
    計算累積能量線（OBV）
    :param df: DataFrame，需含 Volume/Close
    :return: OBV 序列
    """
    vol = df.get('Trading_Volume', df.get('Volume'))
    price = df.get('close', df.get('Close'))
    obv = [0]
    for i in range(1, len(df)):
        if price.iat[i] > price.iat[i-1]:
            obv.append(obv[-1] + vol.iat[i])
        elif price.iat[i] < price.iat[i-1]:
            obv.append(obv[-1] - vol.iat[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

def calculate_vwap(df):
    """
    計算成交量加權平均價（VWAP）
    :param df: DataFrame, 需含 Volume/Close
    :return: VWAP 序列
    """
    vol = df.get('Trading_Volume', df.get('Volume'))
    price = df.get('close', df.get('Close'))
    cum_vp = (price * vol).cumsum()  # 價量累積
    cum_v = vol.cumsum()  # 量累積
    return cum_vp / cum_v

def detect_divergence(df, window=20):
    """
    簡易背離偵測：價格創新高、OBV 未跟進
    :param df: DataFrame
    :param window: 視窗
    :return: 背離訊號 (Boolean)
    """
    price = df.get('close', df.get('Close'))
    obv = calculate_obv(df)
    ph = price.rolling(window).max().shift(1)
    oh = obv.rolling(window).max().shift(1)
    # 價格突破前高且 OBV 未突破 = 背離
    return (price > ph) & (obv < oh)

def apply_technical_indicators(df):
    """
    一次套用所有技術指標並回傳新的 DataFrame
    :param df: 原始價格 DataFrame
    :return: 含指標欄位的 DataFrame
    """
    df = df.copy()
    price = df.get('close', df.get('Close'))
    # 移動平均
    df['MA_5'] = price.rolling(5).mean()    # 5 日移動平均
    df['MA_20'] = price.rolling(20).mean()  # 20 日移動平均
    df['MA_60'] = price.rolling(60).mean()  # 60 日移動平均
    # RSI
    df['RSI_14'] = calculate_rsi(price)
    # MACD
    macd_line, sig_line, hist = calculate_macd(price)
    df['MACD_Line'] = macd_line
    df['MACD_Signal'] = sig_line
    df['MACD_Hist'] = hist
    # 歷史波動率
    df['HV_20'] = calculate_hv(price)
    # 布林通道
    bb_mid, bb_up, bb_down = calculate_bollinger(price)
    df['BB_MID'] = bb_mid
    df['BB_UP'] = bb_up
    df['BB_DOWN'] = bb_down
    # ATR
    df['ATR_14'] = calculate_atr(df)
    # OBV & VWAP
    df['OBV'] = calculate_obv(df)
    df['VWAP'] = calculate_vwap(df)
    # 背離偵測
    df['Divergence_20'] = detect_divergence(df)
    return df