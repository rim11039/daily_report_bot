from unittest.mock import patch, MagicMock
import tech_and_money.main.qiita_checker as qiita_checker

@patch.object(qiita_checker.requests, 'get')
def test_get_qiita_trend_success(mock_get):
    """
    QiitaAPIから正常にデータを取得できた場合のテスト
    """
    # モックのレスポンスを設定
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"title": "Test Article 1", "url": "https://qiita.com/test1", "likes_count": 50},
        {"title": "Test Article 2", "url": "https://qiita.com/test2", "likes_count": 40}
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = qiita_checker.get_qiita_trend()

    mock_get.assert_called_once()
    assert "📚 今週のQiita注目記事" in result
    assert "1. Test Article 1 (LGTM: 50)" in result
    assert "https://qiita.com/test1" in result

@patch.object(qiita_checker.requests, 'get')
def test_get_qiita_trend_empty(mock_get):
    """
    該当記事が0件だった場合のテスト
    """
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = qiita_checker.get_qiita_trend()

    assert result == "該当するQiita記事が見つかりませんでした。"

@patch.object(qiita_checker.requests, 'get')
def test_get_qiita_trend_error(mock_get):
    """
    APIリクエストでエラーが発生した場合のテスト
    """
    mock_get.side_effect = qiita_checker.requests.exceptions.RequestException("API Error")

    result = qiita_checker.get_qiita_trend()

    assert "Qiitaのデータ取得に失敗しました: API Error" in result
