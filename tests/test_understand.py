import pytest
from src.agent.persona import SOCIAL_INFLUENCER_PERSONA
from src.agent.understand import UnderstandEngine
from src.core.contracts import Platform


@pytest.fixture
def engine(mocker):
    # Mock Vertex AI client to avoid real network calls
    mock_client = mocker.MagicMock()
    mock_models = mocker.MagicMock()
    mock_client.models = mock_models

    mocker.patch("google.genai.Client", return_value=mock_client)
    eng = UnderstandEngine()
    eng.client = mock_client  # ensure it's set
    return eng


def test_heuristic_fallback(engine):
    res = engine.classify_heuristic("This app is the worst thing ever, fail!")
    assert res.intent == "complaint"
    assert res.urgency == "high"


def test_vertex_llm_classification(engine, monkeypatch):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "autonomy_enable_grounding", False)

    # Setup mock structured output
    mock_response = engine.client.models.generate_content.return_value
    mock_response.text = '{"intent": "question", "urgency": "medium", "language": "en"}'

    res = engine.classify("How does this work?")
    assert res.intent == "question"
    assert res.urgency == "medium"
    assert res.language == "en"

    prompt = engine.client.models.generate_content.call_args.kwargs["contents"]
    assert "Current UTC timestamp:" in prompt


def test_vertex_llm_failure_fallback(engine):
    engine.client.models.generate_content.side_effect = Exception("Vertex API Down")
    # Should fallback to heuristic
    res = engine.classify("This is great!")
    assert res.intent == "praise"
    assert res.urgency == "low"


def test_generate_reply_enables_grounding(engine, monkeypatch, mocker):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "autonomy_use_llm_generation", True)
    monkeypatch.setattr(src.core.config.settings, "autonomy_enable_grounding", True)
    monkeypatch.setattr(src.core.config.settings, "autonomy_require_grounding", True)

    mock_response = engine.client.models.generate_content.return_value
    mock_response.text = '{"text":"grounded reply"}'
    candidate = mocker.MagicMock()
    candidate.grounding_metadata = {"search_entry_point": "ok"}
    mock_response.candidates = [candidate]

    reply = engine.generate_reply(
        profile_name="SocialAgent_X",
        platform=Platform.X,
        source_text="What happened today?",
        intent="question",
        urgency="medium",
        language="en",
    )

    assert "grounded reply" in reply
    call = engine.client.models.generate_content.call_args.kwargs
    config = call["config"]
    prompt = call["contents"]
    assert config.tools is not None
    assert "Agent Persona: Social Influencer Autonomo" in prompt
    assert SOCIAL_INFLUENCER_PERSONA.strip().splitlines()[0] in prompt


def test_classify_requires_grounding_when_enabled(engine, monkeypatch):
    import src.core.config

    monkeypatch.setattr(src.core.config.settings, "autonomy_enable_grounding", True)
    monkeypatch.setattr(src.core.config.settings, "autonomy_require_grounding", True)

    # Response is parseable but has no grounding metadata.
    mock_response = engine.client.models.generate_content.return_value
    mock_response.text = '{"intent":"question","urgency":"medium","language":"en"}'
    mock_response.candidates = []

    # "great" should be praise in heuristic fallback.
    res = engine.classify("This is great!")
    assert res.intent == "praise"
    assert engine.client.models.generate_content.call_count == 1
