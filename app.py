from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import time
import os

app = Flask(__name__)

# إعدادات الأسهم
STOCKS_TO_MONITOR = {
    'نسيج': {'symbol': '1213', 'sector': 'المواد الأساسية'},
    'أيان للاستثمار': {'symbol': '2140', 'sector': 'البنوك والخدمات المالية'},
    'الكابلات السعودية': {'symbol': '2110', 'sector': 'الصناعة'},
    'ريدان الغذائية': {'symbol': '6012', 'sector': 'السلع الاستهلاكية الكمالية'},
    'صدر للخدمات اللوجستية': {'symbol': '1832', 'sector': 'الصناعة'},
}

SECTOR_LEADING_STOCKS = {
    'المواد الأساسية': {
        '2010': 0.40, '1211': 0.30, '2060': 0.20, '2001': 0.10
    },
    'البنوك والخدمات المالية': {
        '1120': 0.30, '1180': 0.25, '1060': 0.20, '1050': 0.15, '1150': 0.10
    },
    'الصناعة': {
        '2040': 0.30, '2240': 0.25, '2250': 0.25, '2290': 0.20
    },
    'السلع الاستهلاكية الكمالية': {
        '4190': 0.30, '4003': 0.30, '4008': 0.25, '1810': 0.15
    }
}

def get_stock_data(symbol):
    """جلب بيانات السهم"""
    try:
        yf_symbol = f"{symbol}.SR"
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="1y")
        if df.empty:
            return pd.DataFrame()
        df.index = df.index.tz_localize(None)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except:
        return pd.DataFrame()

def get_tasi_data():
    """جلب بيانات تاسي"""
    try:
        ticker = yf.Ticker("^TASI.SR")
        df = ticker.history(period="1y")
        if df.empty:
            return pd.DataFrame()
        df.index = df.index.tz_localize(None)
        return df[['Close']]
    except:
        return pd.DataFrame()

def get_sector_data(sector_name):
    """حساب مؤشر القطاع"""
    leading_stocks = SECTOR_LEADING_STOCKS.get(sector_name, {})
    if not leading_stocks:
        return pd.DataFrame()
    
    sector_dfs = []
    weights = []
    
    for symbol, weight in leading_stocks.items():
        df = get_stock_data(symbol)
        if not df.empty:
            sector_dfs.append(df['Close'].rename(symbol))
            weights.append(weight)
        time.sleep(0.2)
    
    if not sector_dfs:
        return pd.DataFrame()
    
    sector_df = pd.concat(sector_dfs, axis=1)
    weights = np.array(weights)
    weights = weights / weights.sum()
    
    sector_index = (sector_df * weights).sum(axis=1).to_frame(name='Close')
    return sector_index.dropna()

def calculate_indicators(df):
    """حساب المؤشرات الفنية"""
    if df.empty:
        return df
    
    df['MA20'] = df['Close'].rolling(window=20, min_periods=1).mean()
    df['MA50'] = df['Close'].rolling(window=50, min_periods=1).mean()
    df['MA100'] = df['Close'].rolling(window=100, min_periods=1).mean()
    df['MA200'] = df['Close'].rolling(window=200, min_periods=1).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=12, adjust=False, min_periods=1).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False, min_periods=1).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False, min_periods=1).mean()
    
    df['Middle_Band'] = df['Close'].rolling(window=20, min_periods=1).mean()
    df['Upper_Band'] = df['Middle_Band'] + (df['Close'].rolling(window=20, min_periods=1).std() * 2)
    df['Lower_Band'] = df['Middle_Band'] - (df['Close'].rolling(window=20, min_periods=1).std() * 2)
    
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    
    return df

def analyze_stock(stock_name, stock_symbol, stock_data, tasi_data, sector_data):
    """تحليل السهم"""
    if len(stock_data) < 200 or len(tasi_data) < 5 or len(sector_data) < 5:
        return None
    
    latest = stock_data.iloc[-1]
    
    conditions = {
        'tasi': tasi_data["Close"].iloc[-1] > tasi_data["Close"].iloc[-5:].mean(),
        'sector': sector_data["Close"].iloc[-1] > sector_data["Close"].iloc[-5:].mean(),
        'obv': latest["OBV"] > stock_data["OBV"].iloc[-10:-1].mean(),
        'volume': latest["Volume"] > (stock_data["Volume"].iloc[-21:-1].mean() * 2),
        'price_breakout': latest["Close"] > stock_data["High"].iloc[-11:-1].max(),
        'ma': latest["Close"] > latest["MA50"],
        'rsi': 50 < latest["RSI"] < 70,
        'macd': latest["MACD"] > latest["Signal_Line"] and latest["MACD"] > 0,
        'bollinger': latest["Close"] > latest["Upper_Band"]
    }
    
    met_conditions = sum(conditions.values())
    percentage = (met_conditions / 9) * 100
    
    return {
        'name': stock_name,
        'symbol': stock_symbol,
        'price': float(latest["Close"]),
        'volume': int(latest["Volume"]),
        'rsi': float(latest["RSI"]),
        'met_conditions': met_conditions,
        'percentage': percentage,
        'signal': met_conditions == 9,
        'conditions': conditions
    }

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/api/analyze')
def analyze():
    """API لتحليل الأسهم"""
    try:
        # جلب بيانات تاسي
        tasi_data = get_tasi_data()
        if tasi_data.empty:
            return jsonify({'error': 'فشل جلب بيانات تاسي'}), 500
        
        tasi_value = float(tasi_data['Close'].iloc[-1])
        
        results = []
        signals = []
        
        for name, details in STOCKS_TO_MONITOR.items():
            symbol = details['symbol']
            sector = details['sector']
            
            stock_data = get_stock_data(symbol)
            if stock_data.empty:
                continue
            
            stock_data = calculate_indicators(stock_data)
            sector_data = get_sector_data(sector)
            
            if sector_data.empty:
                continue
            
            analysis = analyze_stock(name, symbol, stock_data, tasi_data, sector_data)
            if analysis:
                results.append(analysis)
                if analysis['signal']:
                    signals.append(analysis)
        
        # ترتيب النتائج حسب النسبة
        results = sorted(results, key=lambda x: x['percentage'], reverse=True)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tasi': tasi_value,
            'signals': signals,
            'stocks': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
