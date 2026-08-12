import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from notion_checker import get_notion_tasks
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# ログの出力先ディレクトリ (notion_task/logs/)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _setup_logger():
    """
    loguruの出力先を設定する。

    デフォルトのハンドラを外し、コンソール(stderr)とファイルの2系統に出す。
    コンソールの出力レベルは LOG_LEVEL 環境変数で変更できる。
    """
    logger.remove()  # loguruが最初から持っているstderrハンドラを外す
    logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))
    logger.add(
        LOG_DIR / "notion_task_{time:YYYY-MM-DD}.log",
        level="DEBUG",  # ファイルには常に詳細まで残す
        rotation="1 week",
        retention="1 month",
        encoding="utf-8",  # Windowsでも日本語が文字化けしないようにする
    )


def main():
    _setup_logger()
    logger.info("Notionからタスクを取得します")

    task_info = get_notion_tasks(NOTION_TOKEN, NOTION_DATABASE_ID)

    message_text = f"📅 本日のタスク確認\n\n{task_info}"

    logger.info("LINEに送信しています...")

    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        line_bot_api.push_message(USER_ID, TextSendMessage(text=message_text))
        logger.success("LINEへの送信が完了しました")
    except LineBotApiError:
        # スタックトレースまで残したいので exception を使う
        logger.exception("LINEへの送信に失敗しました")


if __name__ == "__main__":
    main()
