from unittest.mock import MagicMock, patch

import qiita_summary.main.gemini_summarizer as gemini_summarizer


@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_success(mock_client_cls):
    """Geminiから正常に要約を取得できた場合のテスト"""
    mock_response = MagicMock()
    mock_response.text = "- 要点1\n- 要点2\n- 要点3"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = gemini_summarizer.summarize_article("タイトル", "本文")

    mock_client.models.generate_content.assert_called_once()
    # 先頭(優先)モデルで呼ばれていること
    assert (
        mock_client.models.generate_content.call_args.kwargs["model"]
        == gemini_summarizer.GEMINI_MODELS[0]
    )
    assert "要点1" in result


@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_trims_long_body(mock_client_cls):
    """本文が上限を超える場合に切り詰められることのテスト"""
    mock_response = MagicMock()
    mock_response.text = "- 要約"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    long_body = "あ" * (gemini_summarizer.MAX_BODY_CHARS + 500)
    gemini_summarizer.summarize_article("タイトル", long_body)

    sent_prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert "以降は省略" in sent_prompt


@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_non_retryable_falls_through_models(mock_client_cls):
    """リトライ対象外(400)のエラーはリトライせず次モデルへフォールバックするテスト"""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = gemini_summarizer.errors.APIError(
        400, {"error": {"message": "bad request"}}
    )
    mock_client_cls.return_value = mock_client

    result = gemini_summarizer.summarize_article("タイトル", "本文")

    assert "失敗" in result
    # 各モデルを1回ずつ試す (リトライはしない)
    assert mock_client.models.generate_content.call_count == len(
        gemini_summarizer.GEMINI_MODELS
    )


@patch.object(gemini_summarizer.time, "sleep")  # スリープを無効化して高速化
@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_retries_then_succeeds(mock_client_cls, mock_sleep):
    """一時エラー(503)後に同一モデルでリトライして成功するテスト"""
    ok_response = MagicMock()
    ok_response.text = "- 要点"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        gemini_summarizer.errors.APIError(503, {"error": {"message": "busy"}}),
        ok_response,
    ]
    mock_client_cls.return_value = mock_client

    result = gemini_summarizer.summarize_article("タイトル", "本文")

    assert "要点" in result
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


@patch.object(gemini_summarizer.time, "sleep")  # スリープを無効化して高速化
@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_falls_back_to_next_model(mock_client_cls, mock_sleep):
    """先頭モデルが503で全リトライ失敗した後、次モデルで成功するテスト"""
    ok_response = MagicMock()
    ok_response.text = "- 要点"

    # 先頭モデルはMAX_RETRIES回すべて503、次モデルで成功
    side_effects = [
        gemini_summarizer.errors.APIError(503, {"error": {"message": "busy"}})
        for _ in range(gemini_summarizer.MAX_RETRIES)
    ]
    side_effects.append(ok_response)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = side_effects
    mock_client_cls.return_value = mock_client

    result = gemini_summarizer.summarize_article("タイトル", "本文")

    assert "要点" in result
    # 先頭モデルで MAX_RETRIES 回 + 次モデルで1回
    assert (
        mock_client.models.generate_content.call_count
        == gemini_summarizer.MAX_RETRIES + 1
    )
    # 2番目のモデルで成功していること
    assert (
        mock_client.models.generate_content.call_args.kwargs["model"]
        == gemini_summarizer.GEMINI_MODELS[1]
    )


@patch.object(gemini_summarizer.time, "sleep")  # スリープを無効化して高速化
@patch.object(gemini_summarizer.genai, "Client")
def test_summarize_article_all_models_exhausted(mock_client_cls, mock_sleep):
    """全モデルが503でリトライ上限まで失敗した場合に失敗を返すテスト"""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = gemini_summarizer.errors.APIError(
        503, {"error": {"message": "busy"}}
    )
    mock_client_cls.return_value = mock_client

    result = gemini_summarizer.summarize_article("タイトル", "本文")

    assert "失敗" in result
    # 各モデルで MAX_RETRIES 回試す
    assert mock_client.models.generate_content.call_count == (
        gemini_summarizer.MAX_RETRIES * len(gemini_summarizer.GEMINI_MODELS)
    )
