import yfinance as yf

def get_stock_data(ticker_symbol):
    """
    指定された銘柄の現在値と前日比を取得する
    """
    # yfinance用にシンボルを調整 東証の場合は .T、名証は .M、福証は .F など
    symbol = ticker_symbol
    
    # データ取得（期間は1日分あれば十分ですが、前日比計算用に数日分取ります）
    stock = yf.Ticker(symbol)
    hist = stock.history(period="5d")
    
    if len(hist) < 2:
        return "データが取得できませんでした。"

    # 最新の終値（または現在値）と、その前日の終値
    current_price = hist['Close'].iloc[-1]
    prev_close = hist['Close'].iloc[-2]
    
    # 前日比の計算
    diff = current_price - prev_close
    diff_percent = (diff / prev_close) * 100
    
    # 表示用に整形 (例: ▲ 150円 (+5.2%))
    sign = "+" if diff > 0 else ""
    
    result = (
        f"📊 {ticker_symbol} の株価情報\n"
        f"現在値: {int(current_price):,}円\n"
        f"前日比: {sign}{int(diff)}円 ({sign}{diff_percent:.2f}%)"
    )
    
    return result

# --- 動作確認用 ---
if __name__ == "__main__":
    # 株式会社GSI (5579)
    print(get_stock_data("5579"))