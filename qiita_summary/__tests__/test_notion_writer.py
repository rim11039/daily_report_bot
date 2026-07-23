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
