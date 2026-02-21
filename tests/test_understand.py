import pytest
from src.agent.understand import UnderstandEngine
from google import genai

@pytest.fixture
def engine(mocker):
    # Mock Vertex AI client to avoid real network calls
    mock_client = mocker.MagicMock()
    mock_models = mocker.MagicMock()
    mock_client.models = mock_models
    
    mocker.patch("google.genai.Client", return_value=mock_client)
    eng = UnderstandEngine()
    eng.client = mock_client # ensure it's set
    return eng

def test_heuristic_fallback(engine):
    res = engine.classify_heuristic("This app is the worst thing ever, fail!")
    assert res.intent == "complaint"
    assert res.urgency == "high"
    
def test_vertex_llm_classification(engine):
    # Setup mock structured output
    mock_response = engine.client.models.generate_content.return_value
    mock_response.text = '{"intent": "question", "urgency": "medium", "language": "en"}'
    
    res = engine.classify("How does this work?")
    assert res.intent == "question"
    assert res.urgency == "medium"
    assert res.language == "en"

def test_vertex_llm_failure_fallback(engine):
    engine.client.models.generate_content.side_effect = Exception("Vertex API Down")
    # Should fallback to heuristic
    res = engine.classify("This is great!")
    assert res.intent == "praise"
    assert res.urgency == "low"
