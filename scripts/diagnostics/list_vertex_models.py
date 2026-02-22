from google import genai

client = genai.Client(vertexai=True, project="vertice-ai-42", location="us-central1")
try:
    for model in client.models.list():
        if model.name and "gemini" in model.name:
            print(f"AVAILABLE MODEL: {model.name}")
except Exception as e:
    print(f"ERROR: {e}")
