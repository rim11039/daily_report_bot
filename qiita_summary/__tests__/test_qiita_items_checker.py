from datetime import datetime
from unittest.mock import MagicMock, patch

import qiita_summary.main.qiita_checker as qiita_checker

# テストで使う固定の基準日
TODAY = datetime(2026, 8, 12)


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

    result = qiita_checker.get_qiita_trend_items(TODAY, 1, 30)

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

    result = qiita_checker.get_qiita_trend_items(TODAY, 1, 30)

    assert result == []


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_error(mock_get):
    """APIリクエストでエラーが発生した場合のテスト"""
    mock_get.side_effect = qiita_checker.requests.exceptions.RequestException("API Error")

    result = qiita_checker.get_qiita_trend_items(TODAY, 1, 30)

    assert result == []


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_sorted_by_likes(mock_get):
    """QiitaAPIの返却順(作成日降順)に関わらずLGTM数の多い順に並ぶこと"""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "title": "新しいが人気は低い",
            "url": "https://qiita.com/new",
            "likes_count": 35,
            "body": "本文",
            "created_at": "2026-08-10T00:00:00+09:00",
        },
        {
            "title": "古いが人気が高い",
            "url": "https://qiita.com/old",
            "likes_count": 198,
            "body": "本文",
            "created_at": "2026-08-01T00:00:00+09:00",
        },
        {
            "title": "中間",
            "url": "https://qiita.com/mid",
            "likes_count": 114,
            "body": "本文",
            "created_at": "2026-08-05T00:00:00+09:00",
        },
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = qiita_checker.get_qiita_trend_items(TODAY, 1, 30)

    assert [r["likes"] for r in result] == [198, 114, 35]


@patch.object(qiita_checker.requests, "get")
def test_get_qiita_trend_items_query_reflects_conditions(mock_get):
    """引数で渡した期間・ストック数が検索クエリに反映されること"""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    qiita_checker.get_qiita_trend_items(TODAY, 4, 10)

    params = mock_get.call_args.kwargs["params"]
    # 2026-08-12 の4週間前は 2026-07-15
    assert params["query"] == "created:>=2026-07-15 stocks:>=10"
    assert params["per_page"] == qiita_checker.PER_PAGE
