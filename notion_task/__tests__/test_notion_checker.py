from unittest.mock import MagicMock, patch

import notion_task.main.notion_checker as notion_checker


def _task(title: str, status: str, due: str = None, priority: str = None, parent: bool = False) -> dict:
    """Notionのタスク1件分のレスポンスを組み立てるヘルパー"""
    props = {
        notion_checker.PROP_TITLE: {
            "title": [{"plain_text": title}] if title else [],
        },
        notion_checker.PROP_PROGRESS: {
            "status": {"name": status} if status else None,
        },
        notion_checker.PROP_DUE_DATE: {
            "date": {"start": due} if due else None,
        },
        notion_checker.PROP_PRIORITY: {
            "select": {"name": priority} if priority else None,
        },
        "親アイテム": {"relation": [{"id": "parent-id"}] if parent else []},
    }
    return {"properties": props}


def _mock_response(status_code: int = 200, results=None, text: str = "") -> MagicMock:
    """requests.postの戻り値となるレスポンスモックを作る"""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.json.return_value = {"results": results or []}
    return mock_response


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_success(mock_post):
    """未完了タスクをステータスごとに整形して返すテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("設計を書く", "未着手", due="2026-08-15T00:00:00", priority="高"),
            _task("実装する", "進捗50%", due="2026-08-20T00:00:00", priority="中"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert "未完了タスク (2件)" in result
    assert "未着手 (1件)" in result
    assert "進捗50% (1件)" in result
    assert "• 設計を書く [高] | 2026-08-15" in result
    assert "• 実装する [中] | 2026-08-20" in result


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_query_sorted_by_due_date(mock_post):
    """期限の昇順でソートするクエリを送るテスト"""
    mock_post.return_value = _mock_response(results=[])

    notion_checker.get_notion_tasks("tok", "db")

    args, kwargs = mock_post.call_args
    assert args[0].endswith("/databases/db/query")
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert kwargs["json"]["sorts"] == [
        {"property": notion_checker.PROP_DUE_DATE, "direction": "ascending"}
    ]


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_api_error(mock_post):
    """APIがエラーステータスを返した場合はエラーメッセージを返すテスト"""
    mock_post.return_value = _mock_response(status_code=401, text="unauthorized")

    result = notion_checker.get_notion_tasks("tok", "db")

    assert "[ERROR] Notion取得エラー" in result
    assert "status: 401" in result
    assert "unauthorized" in result


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_no_results(mock_post):
    """タスクが0件の場合のテスト"""
    mock_post.return_value = _mock_response(results=[])

    result = notion_checker.get_notion_tasks("tok", "db")

    assert result == "[INFO] タスクはありません！"


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_all_completed(mock_post):
    """すべて完了済みの場合のテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("完了タスク1", "完了 🙌"),
            _task("完了タスク2", "完了 🙌"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert result == "[INFO] 未完了タスクはありません！"


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_excludes_parent_relation(mock_post):
    """親アイテムを持つ(サブ)タスクは抽出しないテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("親を持つサブタスク", "未着手", parent=True),
            _task("トップレベルタスク", "未着手"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert "親を持つサブタスク" not in result
    assert "トップレベルタスク" in result
    assert "未完了タスク (1件)" in result


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_excludes_completed_only(mock_post):
    """完了タスクは除外し、未完了タスクだけを数えるテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("完了済み", "完了 🙌"),
            _task("進行中", "進捗30%", due="2026-08-18T00:00:00", priority="低"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert "完了済み" not in result
    assert "進行中" in result
    assert "未完了タスク (1件)" in result


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_defaults_for_missing_fields(mock_post):
    """タイトル・期限・優先度が未設定でも既定値で整形するテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("", "未着手"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert "• (無題) [未設定] | 未設定" in result


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_status_display_order(mock_post):
    """ステータスが定義順(未着手→進捗昇順)に並ぶテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("後で着手", "進捗80%"),
            _task("まだ", "未着手"),
            _task("途中", "進捗20%"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    idx_start = result.index("未着手 (1件)")
    idx_20 = result.index("進捗20% (1件)")
    idx_80 = result.index("進捗80% (1件)")
    assert idx_start < idx_20 < idx_80


@patch.object(notion_checker.requests, "post")
def test_get_notion_tasks_unknown_status_goes_last(mock_post):
    """定義順に無いステータスは末尾に回るテスト"""
    mock_post.return_value = _mock_response(
        results=[
            _task("見直し中", "レビュー中"),
            _task("これから", "未着手"),
        ]
    )

    result = notion_checker.get_notion_tasks("tok", "db")

    assert result.index("未着手 (1件)") < result.index("レビュー中 (1件)")
