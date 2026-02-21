from pydantic import BaseModel
from google import genai
from google.genai import types
from src.core.config import settings
from src.core.logger import log

class ContextClassification(BaseModel):
    intent: str  # e.g., question, complaint, praise, neutral
    urgency: str # low, medium, high
    language: str

class UnderstandEngine:
    def __init__(self):
        try:
            self.client = genai.Client(
                vertexai=True, 
                project=settings.gcp_project, 
                location="global" # Gemini 3 models require the global region
            )
        except Exception as e:
            log.error(f"Failed to initialize Vertex AI Client: {e}")
            self.client = None
                
        # The correct, exact identifier for Gemini 3 Flash on Vertex AI
        self.model = "gemini-3-flash-preview"
        
        # Explicit identifier logic: this is Byte Social Agent, NOT the existing Cloud Run bot
        self.agent_identity = "ByteSocialAgent_v1"

    def classify_heuristic(self, content: str) -> ContextClassification:
        """Fallback MVP heuristic keyword matching if LLM fails or is missing."""
        content_lower = content.lower()
        
        intent = "neutral"
        if "?" in content or "how" in content_lower or "what" in content_lower:
            intent = "question"
        elif "bad" in content_lower or "worst" in content_lower or "fail" in content_lower:
            intent = "complaint"
        elif "good" in content_lower or "great" in content_lower or "awesome" in content_lower:
            intent = "praise"
            
        urgency = "low"
        if intent == "complaint" or "urgent" in content_lower or "asap" in content_lower:
            urgency = "high"
            
        return ContextClassification(
            intent=intent,
            urgency=urgency,
            language="un" # unknown heuristic
        )

    def classify(self, content: str) -> ContextClassification:
        """
        Classifies incoming content using Gemini Structural Output.
        """
        if not self.client:
            log.warning("Gemini Client not configured. Falling back to heuristic.")
            return self.classify_heuristic(content)

        try:
            prompt = f"""
            System Identity: You are {self.agent_identity}, a distinct social media context classifier.
            IMPORTANT: You are NOT the existing bot running on Cloud Run. You operate independently.
            
            Analyze the following social media text.
            Determine its primary intent (question, complaint, praise, neutral), 
            its urgency level (low, medium, high), and the 2-letter language code (e.g., pt, en, es).
            
            Text: "{content}"
            """
            
            # Using structured output feature with Vertex AI gemini-3.0-flash
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContextClassification,
                    temperature=0.1
                ),
            )
            
            return ContextClassification.model_validate_json(response.text)
            
        except Exception as e:
            log.error(f"LLM Classification failed, using fallback: {e}")
            return self.classify_heuristic(content)

understand_engine = UnderstandEngine()
