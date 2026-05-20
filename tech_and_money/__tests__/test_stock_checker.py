from unittest.mock import patch, MagicMock
import tech_and_money.main.stock_checker as stock_checker

@patch.object(stock_checker.yf, 'Ticker')
def test_get_stock_data_success(mock_ticker):
    """
    株価情報が正常に取得できた場合のテスト
    """
    mock_stock_instance = MagicMock()
    
    # history() の戻り値 (DataFrameのモック)
    mock_hist = MagicMock()
    mock_hist.__len__.return_value = 5  # 2日以上のデータがある状態
    
    # hist['Close'].iloc[-1] などの列データとインデックスアクセスをモック化
    mock_close = MagicMock()
    # iloc[-1] が 1050 (現在値)、iloc[-2] が 1000 (前日終値)
    mock_close.iloc.__getitem__.side_effect = lambda idx: 1050.0 if idx == -1 else 1000.0
    mock_hist.__getitem__.return_value = mock_close
    
    mock_stock_instance.history.return_value = mock_hist
    mock_ticker.return_value = mock_stock_instance

    result = stock_checker.get_stock_data("9999")

    mock_ticker.assert_called_once_with("9999")
    assert "9999 の株価情報" in result
    assert "現在値: 1,050円" in result
    assert "前日比: +50円 (+5.00%)" in result

@patch.object(stock_checker.yf, 'Ticker')
def test_get_stock_data_insufficient_data(mock_ticker):
    """
    データが2日分取得できなかった場合（新規上場など）のテスト
    """
    mock_stock_instance = MagicMock()
    mock_hist = MagicMock()
    mock_hist.__len__.return_value = 1  # 2日未満
    
    mock_stock_instance.history.return_value = mock_hist
    mock_ticker.return_value = mock_stock_instance

    result = stock_checker.get_stock_data("9999")

    assert result == "データが取得できませんでした。"
