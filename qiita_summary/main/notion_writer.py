import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# Notionデータベースのプロパティ名（実際の列名と異なる場合はここを修正）
PROP_TITLE = "タイトル"
PROP_URL = "URL"
PROP_LGTM = "LGTM"
PROP_DATE = "取得日"

# Notionの1テキストブロックあたりの文字数上限
NOTION_TEXT_LIMIT = 2000


def _paragraph_blocks(text: str) -> list[dict]:
    """要約テキストを2000字ごとに分割してparagraphブロックのリストにする。"""
    blocks: list[dict] = []
    for i in range(0, len(text), NOTION_TEXT_LIMIT):
        chunk = text[i : i + NOTION_TEXT_LIMIT]
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": chunk}}
                    ]
                },
            }
        )
    return blocks


def page_exists_with_url(token: str, database_id: str, url: str) -> bool:
    """
    同じURLのページがNotionデータベースに既に存在するか判定する。
    存在すれば True。URLが空、またはクエリに失敗した場合は False を返す
    （書き込みを止めてしまわないよう、判定できないときは「未登録」扱いにする）。
    """
    if not url:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "filter": {"property": PROP_URL, "url": {"equals": url}},
        "page_size": 1,
    }

    response = requests.post(
        f"{NOTION_API_BASE}/databases/{database_id}/query",
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        print(
            f"[WARN] Notion重複チェックに失敗しました (status: {response.status_code})\n{response.text}"
        )
        return False

    return bool(response.json().get("results"))


def create_summary_page(
    token: str,
    database_id: str,
    title: str,
    url: str,
    likes: int,
    summary: str,
    date: str,
) -> bool:
    """
    Qiita記事の要約をNotionデータベースに1ページとして追加する。
    成功時 True、失敗時 False を返す。
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    properties = {
        PROP_TITLE: {"title": [{"text": {"content": title}}]},
        PROP_URL: {"url": url or None},
        PROP_LGTM: {"number": likes},
    }
    if date:
        properties[PROP_DATE] = {"date": {"start": date}}

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": _paragraph_blocks(summary),
    }

    response = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        print(
            f"[ERROR] Notion書き込みエラー (status: {response.status_code})\n{response.text}"
        )
        return False

    return True
