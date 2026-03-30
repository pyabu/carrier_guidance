import os
import random
import string

os.environ.setdefault("VERCEL", "1")
os.environ["GEMINI_API_KEY"] = ""

from app import (  # noqa: E402
    CAREER_COPILOT_HISTORY_CHAR_LIMITS,
    CAREER_COPILOT_HISTORY_LIMIT,
    _compact_chat_history,
    app,
)


def _random_text(length):
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def test_chatbot_rejects_missing_message_with_json():
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.post("/api/career_copilot", json={})

    assert response.status_code == 400
    assert response.is_json
    assert response.get_json()["error"] == "No message provided"


def test_chatbot_rejects_non_json_payload_with_json():
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.post(
        "/api/career_copilot",
        data="not-json",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 400
    assert response.is_json
    assert response.get_json()["error"] == "No message provided"


def test_compact_chat_history_limits_message_count_and_lengths():
    raw_history = []
    for _ in range(10):
        raw_history.append({"role": "user", "content": _random_text(700)})
        raw_history.append({"role": "assistant", "content": _random_text(1600)})

    compact_history = _compact_chat_history(raw_history)

    assert len(compact_history) <= CAREER_COPILOT_HISTORY_LIMIT
    for item in compact_history:
        assert item["role"] in CAREER_COPILOT_HISTORY_CHAR_LIMITS
        assert len(item["content"]) <= CAREER_COPILOT_HISTORY_CHAR_LIMITS[item["role"]]


def test_chatbot_keeps_session_cookie_small_after_multiple_turns():
    app.config.update(TESTING=True)
    client = app.test_client()

    for _ in range(6):
        response = client.post(
            "/api/career_copilot",
            json={"message": _random_text(900)},
        )
        assert response.status_code == 200
        assert response.is_json

    with client.session_transaction() as sess:
        history = sess["chat_history"]
        assert len(history) <= CAREER_COPILOT_HISTORY_LIMIT
        serializer = app.session_interface.get_signing_serializer(app)
        cookie = serializer.dumps(dict(sess))
        assert len(cookie) < 3800
