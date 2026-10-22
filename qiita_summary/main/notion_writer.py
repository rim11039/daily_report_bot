import requests
from loguru import logger

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# Notionデータベースのプロパティ名（実際の列名と異なる場合はここを修正）
PROP_TITLE = "タイトル"
PROP_URL = "URL"
PROP_LGTM = "LGTM"
PROP_DATE = "取得日"

# Notionの1テキストブロックあたりの文字数上限
NOTION_TEXT_LIMIT = 2000

# 1回のクエリで取得するページ数 (NotionAPIの上限は100)
NOTION_PAGE_SIZE = 100

# ページネーションの上限 (万一 has_more が下がらない場合の無限ループ防止)
MAX_QUERY_PAGES = 50

# APIの応答を待つ上限秒数 (未指定だと応答がない場合に処理が止まり続ける)
REQUEST_TIMEOUT = 30


def fetch_registered_urls(token: str, database_id: str) -> set[str] | None:
    """
    Notionデータベースに登録済みのURLをまとめて取得する。

    記事ごとに問い合わせるとNotionのレート制限(毎秒3リクエスト程度)に掛かり、
    429を「未登録」と誤判定して重複ページを作ってしまう。
    それを避けるため起動時に1度だけ取得し、以降はこのセットで判定する。

    取得に失敗した場合は None を返す。「登録が1件も無い」ことを表す空セットと
    区別できるようにしてあるので、呼び出し側は None を「判定不能」として扱い、
    重複を作らないよう処理を中止すること。
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    urls: set[str] = set()
    start_cursor: str | None = None

    for _ in range(MAX_QUERY_PAGES):
        payload: dict = {"page_size": NOTION_PAGE_SIZE}
        # 2ページ目以降は前回の続きから取得する
        if start_cursor:
            payload["start_cursor"] = start_cursor

        try:
            response = requests.post(
                f"{NOTION_API_BASE}/databases/{database_id}/query",
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException:
            logger.exception("Notion登録済みURLの取得に失敗しました")
            return None

        if response.status_code != 200:
            logger.error(
                f"Notion登録済みURLの取得に失敗しました "
                f"(status: {response.status_code})\n{response.text}"
            )
            return None

        data = response.json()
        for page in data.get("results", []):
            url = page.get("properties", {}).get(PROP_URL, {}).get("url")
            if url:
                urls.add(url)

        # 続きが無ければ完了
        if not data.get("has_more"):
            logger.info(f"Notion登録済みURLを{len(urls)}件取得しました")
            return urls

        start_cursor = data.get("next_cursor")

    logger.warning(f"Notionの取得が上限({MAX_QUERY_PAGES}ページ)に達したため打ち切りました")
    return urls


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

    try:
        response = requests.post(
            f"{NOTION_API_BASE}/pages",
            headers=headers,
            json=payload,
        )
    except requests.exceptions.RequestException:
        logger.exception("Notionへの書き込み時に接続に失敗しました")
        return False

    if response.status_code != 200:
        logger.error(
            f"Notion書き込みエラー (status: {response.status_code})\n{response.text}"
        )
        return False

    return True
