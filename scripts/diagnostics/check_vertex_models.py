from google import genai
client = genai.Client(vertexai=True, project="vertice-ai-42", location="global")

models_to_test = [
    "gemini-3.0-flash", "gemini-3.0-flash-preview", "gemini-3.0-flash-exp",
    "gemini-3.1-flash", "gemini-3.1-flash-preview", "gemini-3.1-flash-exp",
    "gemini-2.5-flash", "gemini-2.5-flash-preview", "gemini-2.5-flash-exp",
    "gemini-2.0-flash", "gemini-2.0-flash-exp",
    "gemini-1.5-flash-001", "gemini-1.5-flash-002", "gemini-1.5-flash"
]

for m in models_to_test:
    try:
        resp = client.models.generate_content(model=m, contents="hello")
        print(f"[SUCCESS] {m}")
        break # stop on first success
    except Exception as e:
        print(f"[FAIL] {m}: {str(e).split('}')[0] + '}'}")
