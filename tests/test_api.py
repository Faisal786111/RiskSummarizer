from fastapi.testclient import TestClient

from app import main
from app.fetcher import FetchError
from app.llm import LLMError
from app.schemas import RiskLevel, RiskSummary

client = TestClient(main.app)

LONG_TEXT = "The vendor has missed three delivery deadlines and payment terms are unclear. " * 3


def fake_result():
    return RiskSummary(
        summary="The vendor is unreliable.",
        risk_level=RiskLevel.high,
        reasons=["Missed deadlines", "Unclear payment terms"],
    )


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_summarize_text(monkeypatch):
    monkeypatch.setattr(main, "analyse", lambda text: fake_result())
    response = client.post("/summarize", json={"text": LONG_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "text"
    assert body["result"]["risk_level"] == "high"
    assert body["characters_analysed"] == len(LONG_TEXT.strip())


def test_summarize_url(monkeypatch):
    monkeypatch.setattr(main, "fetch_text", lambda url: LONG_TEXT)
    monkeypatch.setattr(main, "analyse", lambda text: fake_result())
    response = client.post("/summarize", json={"url": "https://example.com/report"})
    assert response.status_code == 200
    assert response.json()["source"] == "url"


def test_requires_exactly_one_source():
    assert client.post("/summarize", json={}).status_code == 422
    both = {"text": LONG_TEXT, "url": "https://example.com"}
    assert client.post("/summarize", json=both).status_code == 422


def test_rejects_short_text():
    assert client.post("/summarize", json={"text": "too short"}).status_code == 422


def test_unsafe_url_returns_400(monkeypatch):
    def boom(url):
        raise FetchError("URLs that point to private or internal addresses are not allowed.")
    monkeypatch.setattr(main, "fetch_text", boom)
    response = client.post("/summarize", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 400


def test_llm_failure_returns_502(monkeypatch):
    def boom(text):
        raise LLMError("The AI service request failed. Please try again.")
    monkeypatch.setattr(main, "analyse", boom)
    response = client.post("/summarize", json={"text": LONG_TEXT})
    assert response.status_code == 502
