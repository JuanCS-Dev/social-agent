from src.agent.understand import UnderstandEngine
import src.core.config


def test_engine_init_failure(mocker, monkeypatch):
    # Simulate failed init
    monkeypatch.setattr(src.core.config.settings, "gcp_project", "bad")
    mocker.patch("google.genai.Client", side_effect=Exception("Auth error"))
    eng = UnderstandEngine()
    assert eng.client is None


def test_heuristic_branches():
    eng = UnderstandEngine()
    eng.client = None  # Force heuristic

    # Test Question
    q = eng.classify("how do I do this?")
    assert q.intent == "question"

    # Test Praise
    p = eng.classify("this is awesome!")
    assert p.intent == "praise"

    # Test default
    d = eng.classify("I am walking my dog")
    assert d.intent == "neutral"
