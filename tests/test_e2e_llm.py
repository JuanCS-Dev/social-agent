import pytest
import os
from src.agent.understand import understand_engine

# Requires explicit env var to prevent failing CI pipelines without GCP Auth
pytestmark = pytest.mark.skipif(not os.environ.get("RUN_E2E_LLM_TESTS"), reason="RUN_E2E_LLM_TESTS not set. Skipping live Vertex AI calls.")


@pytest.mark.asyncio
async def test_e2e_llm_complaint_pt_br():
    """Tests a highly negative Portuguese input."""
    # Ensure real client is active
    assert understand_engine.client is not None, "Vertex client failed to initialize."

    classification = understand_engine.classify("Meu deus que sistema lixo, toda vez que tento logar essa porcaria cai. Resolvam isso urgente!!!!")

    assert classification.intent == "complaint"
    assert classification.urgency == "high"
    assert classification.language.lower() in ["pt", "pt-br", "pt_br"]


@pytest.mark.asyncio
async def test_e2e_llm_praise_en():
    """Tests positive feedback in English."""
    classification = understand_engine.classify("I absolutely loved the new feature! The UI is slick and it runs so much faster now. Great job team.")

    assert classification.intent == "praise"
    assert classification.urgency == "low"
    assert classification.language.lower() == "en"


@pytest.mark.asyncio
async def test_e2e_llm_question_es():
    """Tests an ambiguous inquiry in Spanish."""
    classification = understand_engine.classify("Hola, ¿dónde puedo encontrar la configuración para cambiar mi contraseña? No la veo en el menú principal.")

    assert classification.intent == "question"
    assert classification.urgency in ["low", "medium"]  # LLMs can wobble on urgency of standard questions
    assert classification.language.lower() == "es"


@pytest.mark.asyncio
async def test_e2e_llm_neutral_abstract():
    """Tests nonsensical or completely out-of-bounds text."""
    classification = understand_engine.classify("The quick brown fox jumps over the lazy dog while eating a slice of pizza on mars.")

    # Needs to default cleanly to neutral instead of hallucinating intent
    assert classification.intent == "neutral"
    assert classification.urgency == "low"
