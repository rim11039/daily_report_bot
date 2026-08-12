import time

from google import genai
from google.genai import types, errors
from loguru import logger

# 使用するGeminiモデル (すべて無料枠対象・動作確認済み)。
# 左から順に試し、混雑(503)などでリトライも尽きたら次のモデルにフォールバックする。
# 主力のgemini-3.5-flashは需要集中で503になりやすいため、混雑しにくい
# 軽量・旧世代モデルを優先し、主力は最後の候補にしている。
GEMINI_MODELS = [
    "gemini-3.1-flash-lite",  # 動作確認済み・lite系で混雑しにくい
    "gemini-2.0-flash",       # 動作確認済み(枠に余裕があれば)
    "gemini-3.5-flash",       # 主力・最後の砦(混雑しやすい)
]

# 記事本文が長すぎる場合に切り詰める上限文字数 (トークン/レート対策)
MAX_BODY_CHARS = 12000

# 一時的なサーバー側エラー時にリトライするHTTPステータス
# 429=レート超過, 500=内部エラー, 503=混雑
RETRYABLE_STATUS = {429, 500, 503}
MAX_RETRIES = 3  # 最大試行回数

# 要約時のシステム指示
SYSTEM_INSTRUCTION = (
    "あなたは技術記事を要約するアシスタントです。"
    "渡されたQiita記事を日本語で3〜4個の箇条書きに要約してください。"
    "各箇条書きは1行で簡潔に、記事の要点・結論・使いどころが分かるように。"
    "前置きや「以下が要約です」などの文は不要で、箇条書きのみを出力してください。"
)


def summarize_article(title: str, body: str) -> str:
    """
    記事のタイトルと本文をGeminiに渡し、日本語で要約する。
    GEMINI_API_KEY (または GOOGLE_API_KEY) 環境変数を利用してAPIに接続する。
    失敗時はエラーメッセージ文字列を返す。
    """
    # 本文が長い場合は先頭を優先して切り詰める
    trimmed_body = body[:MAX_BODY_CHARS]
    if len(body) > MAX_BODY_CHARS:
        trimmed_body += "\n\n(...本文が長いため以降は省略)"

    prompt = f"# タイトル\n{title}\n\n# 本文\n{trimmed_body}"

    try:
        client = genai.Client()  # GEMINI_API_KEY / GOOGLE_API_KEY を環境変数から読む
    except Exception as e:  # noqa: BLE001 - botを止めないため予期せぬ例外も握る
        logger.exception("Geminiクライアントの初期化に失敗しました")
        return f"(要約の生成に失敗しました: {e})"

    last_error = None

    # モデルを順に試す (フォールバック)
    for model in GEMINI_MODELS:
        # 各モデルで一時エラーは指数バックオフでリトライ
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        max_output_tokens=1024,
                    ),
                )
                summary = (response.text or "").strip()
                return summary or "(要約を生成できませんでした)"
            except errors.APIError as e:
                last_error = e
                if getattr(e, "code", None) in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                    wait = 2**attempt  # 2, 4秒
                    logger.warning(
                        f"Gemini一時エラー({e.code}) model={model}。"
                        f"{wait}秒後にリトライ ({attempt}/{MAX_RETRIES})"
                    )
                    time.sleep(wait)
                    continue
                # このモデルは諦めて次のモデルへフォールバック
                logger.warning(
                    f"model={model} で失敗({getattr(e, 'code', '?')})。次のモデルを試します。"
                )
                break
            except Exception as e:  # noqa: BLE001 - 予期せぬ例外も次モデルへ
                last_error = e
                logger.warning(f"model={model} で予期せぬエラー: {e}。次のモデルを試します。")
                break

    logger.error(f"すべてのモデルでGemini要約に失敗しました: {last_error}")
    return f"(要約の生成に失敗しました: {last_error})"


# --- 動作確認用 ---
if __name__ == "__main__":
    sample = summarize_article(
        "テスト記事",
        "これはGemini要約の動作確認用のサンプル本文です。要点を箇条書きにしてください。",
    )
    print(sample)
