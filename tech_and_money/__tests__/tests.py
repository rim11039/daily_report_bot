import pytest
from unittest.mock import patch, MagicMock
import tech_and_money.main.main as main_module

@patch.object(main_module, 'STOCK_CODE', '9999')
@patch.object(main_module, 'USER_ID', 'dummy_user_id')
@patch.object(main_module, 'CHANNEL_ACCESS_TOKEN', 'dummy_token')
@patch.object(main_module, 'get_stock_data')
@patch.object(main_module, 'get_qiita_trend')
@patch.object(main_module, 'LineBotApi')
def test_main_success(mock_line_bot_api, mock_qiita, mock_stock):
    """
    main関数が正常に動作し、LINE APIが正しく呼び出されることをテスト
    """
    # モックの戻り値を設定
    mock_stock.return_value = "📊 5579 の株価情報\n現在値: 1,000円\n前日比: +10円 (+1.00%)"
    mock_qiita.return_value = "📚 今週のQiita注目記事\n1. Test Article (LGTM: 100)\nhttps://qiita.com/test"
    
    # LineBotApiのインスタンスをモック化
    mock_line_instance = MagicMock()
    mock_line_bot_api.return_value = mock_line_instance

    # main関数の実行
    main_module.main()

    # 各関数が呼ばれたかチェック
    mock_stock.assert_called_once_with('9999')
    mock_qiita.assert_called_once()
    
    # LINE APIの初期化に正しいトークンが使われたかチェック
    mock_line_bot_api.assert_called_once_with('dummy_token')

    # LINE送信メソッドが正しい引数で呼ばれたかチェック
    mock_line_instance.push_message.assert_called_once()
    args, _ = mock_line_instance.push_message.call_args
    
    # 送信先ユーザーIDの確認
    assert args[0] == 'dummy_user_id'

    # 送信メッセージの内容を確認
    sent_message = args[1].text
    assert "☀️ おはようございます！" in sent_message
    assert "5579 の株価情報" in sent_message
    assert "Qiita注目記事" in sent_message

@patch.object(main_module, 'STOCK_CODE', '9999')
@patch.object(main_module, 'USER_ID', 'dummy_user_id')
@patch.object(main_module, 'CHANNEL_ACCESS_TOKEN', 'dummy_token')
@patch.object(main_module, 'get_stock_data')
@patch.object(main_module, 'get_qiita_trend')
@patch.object(main_module, 'LineBotApi')
def test_main_line_error(mock_line_bot_api, mock_qiita, mock_stock):
    """
    LINE APIでエラーが発生しても、プログラムがクラッシュしないことをテスト
    """
    from linebot.exceptions import LineBotApiError

    # モックの戻り値を設定
    mock_stock.return_value = "Stock Data"
    mock_qiita.return_value = "Qiita Data"
    
    # LineBotApiが例外を投げるように設定
    mock_line_instance = MagicMock()
    mock_line_instance.push_message.side_effect = LineBotApiError(status_code=400)
    mock_line_bot_api.return_value = mock_line_instance

    # main関数の実行（例外がキャッチされ、クラッシュしないことを確認）
    try:
        main_module.main()
    except Exception as e:
        pytest.fail(f"main() raised {type(e).__name__} unexpectedly!")

    # LINE送信メソッドが呼ばれたことは確認
    mock_line_instance.push_message.assert_called_once()
