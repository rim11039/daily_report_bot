import requests
from datetime import datetime, timedelta


def get_qiita_trend_items() -> list[dict]:
    """
    Qiitaから直近1週間でLGTM数が多い記事を取得する。
    本文(body)を含む構造化データのリストを返す。

    返り値の各要素: {"title", "url", "likes", "body", "created_at"}
    エラー時は空リストを返す。
    """
    # 1週間前の日付を YYYY-MM-DD 形式で取得
    last_week: str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # 検索クエリ: 1週間以内に作成され、LGTMが30以上の記事
    query: str = f"created:>={last_week} stocks:>30"

    url: str = "https://qiita.com/api/v2/items"
    params: dict = {
        "page": 1,
        "query": query,
    }

    try:
        response: requests.Response = requests.get(url, params=params)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        items: list = response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Qiitaのデータ取得に失敗しました: {e}")
        return []

    results: list[dict] = []
    for item in items:
        results.append(
            {
                "title": item.get("title", "(無題)"),
                "url": item.get("url", ""),
                "likes": item.get("likes_count", 0),
                "body": item.get("body", ""),
                "created_at": item.get("created_at", "")[:10],
            }
        )

    return results


# --- 動作確認用 ---
if __name__ == "__main__":
    for i, article in enumerate(get_qiita_trend_items(), 1):
        print(f"{i}. {article['title']} (LGTM: {article['likes']})")
        print(f"   {article['url']}")
        print(f"   本文文字数: {len(article['body'])}")
