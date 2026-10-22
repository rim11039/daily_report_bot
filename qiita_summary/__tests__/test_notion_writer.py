from unittest.mock import MagicMock, patch

import qiita_summary.main.notion_writer as notion_writer


@patch.object(notion_writer.requests, "post")
def test_create_summary_page_success(mock_post):
    """Notionへの書き込みが成功した場合のテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    result = notion_writer.create_summary_page(
        token="tok",
        database_id="db",
        title="タイトル",
        url="https://qiita.com/test",
        likes=42,
        summary="- 要点1\n- 要点2",
        date="2026-07-19",
    )

    assert result is True
    payload = mock_post.call_args.kwargs["json"]
    assert payload["parent"]["database_id"] == "db"
    props = payload["properties"]
    assert props[notion_writer.PROP_TITLE]["title"][0]["text"]["content"] == "タイトル"
    assert props[notion_writer.PROP_LGTM]["number"] == 42
    assert props[notion_writer.PROP_DATE]["date"]["start"] == "2026-07-19"
    # 要約はページ本文(children)に入る
    assert len(payload["children"]) == 1


@patch.object(notion_writer.requests, "post")
def test_create_summary_page_splits_long_summary(mock_post):
    """2000字を超える要約が複数ブロックに分割されることのテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    long_summary = "あ" * (notion_writer.NOTION_TEXT_LIMIT + 100)
    notion_writer.create_summary_page(
        token="tok",
        database_id="db",
        title="タイトル",
        url="https://qiita.com/test",
        likes=1,
        summary=long_summary,
        date="2026-07-19",
    )

    payload = mock_post.call_args.kwargs["json"]
    assert len(payload["children"]) == 2


def _url_page(url: str) -> dict:
    """登録済みURLを1件持つNotionページのレスポンスを作る"""
    return {"properties": {notion_writer.PROP_URL: {"url": url}}}


@patch.object(notion_writer.requests, "post")
def test_fetch_registered_urls_success(mock_post):
    """登録済みURLを一括取得できた場合のテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            _url_page("https://qiita.com/a"),
            _url_page("https://qiita.com/b"),
        ],
        "has_more": False,
    }
    mock_post.return_value = mock_response

    result = notion_writer.fetch_registered_urls(token="tok", database_id="db")

    assert result == {"https://qiita.com/a", "https://qiita.com/b"}
    # 1ページで収まる場合はリクエストも1回で済む
    assert mock_post.call_count == 1
    assert mock_post.call_args.args[0].endswith("/databases/db/query")


@patch.object(notion_writer.requests, "post")
def test_fetch_registered_urls_paginates(mock_post):
    """has_moreがTrueの場合に次ページまで辿るテスト"""
    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "results": [_url_page("https://qiita.com/a")],
        "has_more": True,
        "next_cursor": "cursor-1",
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "results": [_url_page("https://qiita.com/b")],
        "has_more": False,
    }
    mock_post.side_effect = [first, second]

    result = notion_writer.fetch_registered_urls(token="tok", database_id="db")

    assert result == {"https://qiita.com/a", "https://qiita.com/b"}
    assert mock_post.call_count == 2
    # 2ページ目は前ページのカーソルを引き継ぐ
    assert mock_post.call_args.kwargs["json"]["start_cursor"] == "cursor-1"


@patch.object(notion_writer.requests, "post")
def test_fetch_registered_urls_skips_pages_without_url(mock_post):
    """URLプロパティが空のページは無視するテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            _url_page("https://qiita.com/a"),
            {"properties": {notion_writer.PROP_URL: {"url": None}}},
            {"properties": {}},
        ],
        "has_more": False,
    }
    mock_post.return_value = mock_response

    result = notion_writer.fetch_registered_urls(token="tok", database_id="db")

    assert result == {"https://qiita.com/a"}


@patch.object(notion_writer.requests, "post")
def test_fetch_registered_urls_query_error(mock_post):
    """クエリが失敗した場合は空セットではなくNoneを返すテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "rate limited"
    mock_post.return_value = mock_response

    result = notion_writer.fetch_registered_urls(token="tok", database_id="db")

    # 空セットを返すと全記事が未登録扱いになり重複を作るため、Noneで区別する
    assert result is None


@patch.object(notion_writer.requests, "post")
def test_fetch_registered_urls_network_error(mock_post):
    """ネットワークエラーが発生した場合もNoneを返すテスト"""
    mock_post.side_effect = notion_writer.requests.exceptions.RequestException("boom")

    result = notion_writer.fetch_registered_urls(token="tok", database_id="db")

    assert result is None


@patch.object(notion_writer.requests, "post")
def test_create_summary_page_failure(mock_post):
    """Notionがエラーを返した場合のテスト"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "bad request"
    mock_post.return_value = mock_response

    result = notion_writer.create_summary_page(
        token="tok",
        database_id="db",
        title="タイトル",
        url="https://qiita.com/test",
        likes=1,
        summary="要約",
        date="2026-07-19",
    )

    assert result is False


@patch.object(notion_writer.requests, "post")
def test_create_summary_page_connection_error(mock_post):
    """Notionに接続できない場合は例外を投げずFalseを返すテスト"""
    mock_post.side_effect = notion_writer.requests.exceptions.ConnectionError("boom")

    result = notion_writer.create_summary_page(
        token="tok",
        database_id="db",
        title="タイトル",
        url="https://qiita.com/test",
        likes=1,
        summary="要約",
        date="2026-07-19",
    )

    assert result is False
