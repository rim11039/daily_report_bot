import os
from datetime import datetime

from dotenv import load_dotenv
from qiita_checker import get_qiita_trend_items
from gemini_summarizer import summarize_article
from notion_writer import create_summary_page, fetch_registered_urls
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

# .env ファイルの内容を読み込む
load_dotenv()

NUMBER_OF_ARTICLES = 3

# 検索条件を優先順に定義する。
# ストック数がトレンドの指標なので、閾値は極力維持し、まず期間を延ばして母数を稼ぐ。
SEARCH_CONDITIONS: list[tuple[int, int]] = [
    (1, 30),   # 直近1週間の話題作
    (2, 30),
    (4, 30),
    (8, 30),   # ここまでで実質100件、まず尽きない
    (8, 10),   # 最後の保険として閾値を下げる
]

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
QIITA_SUMMARY_DATABASE_ID = os.getenv("QIITA_SUMMARY_DATABASE_ID")

def main():
    print("Qiitaトレンド記事を取得中...\n")
    today = datetime.now()

    # 1. Notionに登録済みのURLを一括で取得する
    #    記事ごとに問い合わせるとレート制限に掛かるため、起動時に1度だけ取得する
    registered_urls = fetch_registered_urls(NOTION_TOKEN, QIITA_SUMMARY_DATABASE_ID)
    if registered_urls is None:
        # 登録状況が分からないまま進めると同じ記事を二重に登録してしまうため中止する
        _send_line(
            "📚 本日のQiitaトレンド要約\n\n"
            "Notionの登録状況を取得できなかったため、処理を中止しました。"
        )
        return

    # 2. Notion未登録の記事を規定数集める
    articles = _collect_articles(today, registered_urls)

    if not articles:
        _send_line("📚 本日のQiitaトレンド要約\n\n該当する記事が見つかりませんでした。")
        return

    # 3. 要約・Notionへの書き込み・メッセージ本文の作成
    message_text = _create_message_text(articles, today.strftime("%Y-%m-%d"))

    # 4. LINEへの送信
    _send_line(message_text)


def _collect_articles(today: datetime, registered_urls: set[str]) -> list[dict]:
    """
    Notionに未登録のQiita記事を NUMBER_OF_ARTICLES 件集める。

    SEARCH_CONDITIONS を優先順に試し、規定数に達した時点で打ち切る。
    既に要約済みの記事はスキップして次の記事を対象にするため、
    毎日実行するとランキングを上から順に消化していく動きになる。
    条件を出し切っても足りない場合は、集まった分だけ返す。

    registered_urls は登録済みURLのセット (fetch_registered_urls の返却値)。

    返却値：list[dict]
    """
    summary_articles: list[dict] = []
    # 期間を延ばすと前回の検索結果を含むため、判定済みのURLを覚えておく
    checked_urls: set[str] = set()

    for search_weeks, search_stocks in SEARCH_CONDITIONS:
        print(f"[INFO] 検索: 直近{search_weeks}週間 / ストック{search_stocks}以上")
        get_articles = get_qiita_trend_items(today, search_weeks, search_stocks)

        # LGTM数の多い順に並んでいるため、上から順に未登録の記事を拾っていく
        for article in get_articles:
            url = article["url"]
            title = article["title"]

            if url in checked_urls:
                continue
            checked_urls.add(url)

            # 同一URLのページが既にNotionにある場合は要約せず、次の記事を対象にする
            if url in registered_urls:
                print(f"  登録済みのためスキップ: {title}")
                continue

            summary_articles.append(article)
            print(f"  要約対象 ({len(summary_articles)}/{NUMBER_OF_ARTICLES}): {title}")

            if len(summary_articles) >= NUMBER_OF_ARTICLES:
                return summary_articles

        # 全ての記事がNotionに記載されていた場合は条件を広げて検索からやり直す
        print("[INFO] 規定数に達しなかったため、条件を広げて再検索します")

    print(
        f"[WARN] 条件を広げましたが{NUMBER_OF_ARTICLES}件に届きませんでした "
        f"({len(summary_articles)}件)"
    )
    return summary_articles

def _create_message_text(articles: list[dict], today: str) -> str:
    """
    要約対象の記事をGeminiで要約してNotionに書き込み、
    LINE送信用の本文を組み立てて返す。

    渡される articles は _collect_articles でNotion未登録に絞り込み済みのため、
    ここでは重複チェックを行わない。
    """
    line_lines = ["📚 本日のQiitaトレンド要約\n"]
    articles_len = len(articles)

    # 各記事をGeminiで要約し、Notionに書き込む
    for i, article in enumerate(articles, 1):
        title = article["title"]
        url = article["url"]
        likes = article["likes"]

        print(f"[{i}/{articles_len}] 要約中: {title}")
        summary = summarize_article(title, article["body"])

        print(f"[{i}/{articles_len}] Notionに書き込み中...")
        ok = create_summary_page(
            token=NOTION_TOKEN,
            database_id=QIITA_SUMMARY_DATABASE_ID,
            title=title,
            url=url,
            likes=likes,
            summary=summary,
            date=today,
        )
        if not ok:
            print(f"[WARN] Notionへの書き込みに失敗しました: {title}")

        # LINE用: タイトル・URL・要約の先頭行
        # 検索期間を広げると古い記事も対象になるため、投稿日もあわせて表示する
        first_line = summary.splitlines()[0] if summary else ""
        line_lines.append(f"{i}. {title} (LGTM: {likes} / {article['created_at']})")
        line_lines.append(f"{first_line}")
        line_lines.append(f"{url}\n")

    line_lines.append("📝 詳しい要約はNotionに保存しました。")
    return "\n".join(line_lines)


def _send_line(message_text: str):
    """
    main関数で作成したLINEの本文を
    LineBotApiを使用して送信する。
    """
    print("【LINEに送信しています...】")
    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message_text))
        print("[SUCCESS] 送信完了しました！")
    except LineBotApiError as e:
        print(f"[ERROR] 送信エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
