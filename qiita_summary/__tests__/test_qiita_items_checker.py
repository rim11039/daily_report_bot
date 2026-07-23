from unittest.mock import MagicMock, patch

import qiita_summary.main.qiita_checker as qiita_checker


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_success(mock_get):
    """QiitaAPIから正常にデータを取得できた場合のテスト"""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "title": "Test Article 1",
            "url": "https://qiita.com/test1",
            "likes_count": 50,
            "body": "本文1",
            "created_at": "2026-07-15T00:00:00+09:00",
        },
        {
            "title": "Test Article 2",
            "url": "https://qiita.com/test2",
            "likes_count": 40,
            "body": "本文2",
            "created_at": "2026-07-16T00:00:00+09:00",
        },
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = qiita_checker.get_qiita_trend_items()

    mock_get.assert_called_once()
    assert len(result) == 2
    assert result[0]["title"] == "Test Article 1"
    assert result[0]["likes"] == 50
    assert result[0]["body"] == "本文1"
    assert result[0]["created_at"] == "2026-07-15"


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_empty(mock_get):
    """該当記事が0件だった場合のテスト"""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = qiita_checker.get_qiita_trend_items()

    assert result == []


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_error(mock_get):
    """APIリクエストでエラーが発生した場合のテスト"""
    mock_get.side_effect = qiita_checker.requests.exceptions.RequestException("API Error")

    result = qiita_checker.get_qiita_trend_items()

    assert result == []
