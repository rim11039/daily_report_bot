import requests
from loguru import logger

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# Notionデータベースのプロパティ名（実際の列名と異なる場合はここを修正）
PROP_TITLE = "タスク名"
PROP_DUE_DATE = "期限"
PROP_PRIORITY = "優先度"
PROP_PROGRESS = "ステータス"


def get_notion_tasks(token: str, database_id: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    # 全タスクを期日順に取得
    payload = {
        "sorts": [
            {"property": PROP_DUE_DATE, "direction": "ascending"}
        ],
    }

    response = requests.post(
        f"{NOTION_API_BASE}/databases/{database_id}/query",
        headers=headers,
        json=payload,
    )

    # 以降の戻り値はそのままLINEの本文になるため、
    # 手元で状況を追えるようログにも同じ内容を残す
    if response.status_code != 200:
        logger.error(f"Notion取得エラー (status: {response.status_code})\n{response.text}")
        return f"[ERROR] Notion取得エラー (status: {response.status_code})\n{response.text}"

    results = response.json().get("results", [])
    logger.info(f"Notionから{len(results)}件のタスクを取得しました")

    if not results:
        return "[INFO] タスクはありません！"

    # ステータスが「完了」以外のタスクをフィルター
    incomplete_tasks = []
    for item in results:
        props = item.get("properties", {})
        status_obj = props.get(PROP_PROGRESS, {}).get("status")
        status = status_obj["name"] if status_obj else ""

        # 親タスクが存在するものは抽出しない
        if props.get("親アイテム", {}).get("relation"):
            continue

        # 「完了 🙌」以外を抽出
        if status != "完了 🙌":
            incomplete_tasks.append(item)

    logger.info(f"未完了タスクは{len(incomplete_tasks)}件です")

    if not incomplete_tasks:
        return "[INFO] 未完了タスクはありません！"

    # ステータスごとにグループ化
    tasks_by_status = {}
    for item in incomplete_tasks:
        props = item.get("properties", {})
        status_obj = props.get(PROP_PROGRESS, {}).get("status")
        status = status_obj["name"] if status_obj else "未設定"

        if status not in tasks_by_status:
            tasks_by_status[status] = []
        tasks_by_status[status].append(item)

    # ステータスの表示順序
    status_order = ["未着手", "進捗10%", "進捗20%", "進捗30%", "進捗40%", "進捗50%", "進捗60%", "進捗70%", "進捗80%", "進捗90%"]
    ordered_statuses = [s for s in status_order if s in tasks_by_status]
    ordered_statuses += [s for s in tasks_by_status.keys() if s not in ordered_statuses]

    lines = [f"[TASKS] 未完了タスク ({len(incomplete_tasks)}件)\n"]

    for status in ordered_statuses:
        status_tasks = tasks_by_status[status]
        lines.append(f"{status} ({len(status_tasks)}件)")

        for item in status_tasks:
            props = item.get("properties", {})

            # タスク名
            title_parts = props.get(PROP_TITLE, {}).get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts) or "(無題)"

            # 期日
            due_obj = props.get(PROP_DUE_DATE, {}).get("date")
            due_date = due_obj["start"][:10] if due_obj else "未設定"

            # 優先度
            priority_obj = props.get(PROP_PRIORITY, {}).get("select")
            priority = priority_obj["name"] if priority_obj else "未設定"

            lines.append(f"  • {title} [{priority}] | {due_date}")

        lines.append("")  # 空行でステータスごとを区切る

    return "\n".join(lines).rstrip()
