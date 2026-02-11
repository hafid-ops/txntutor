"""Test Gemini with working model"""
from google import genai

api_key = "AIzaSyANi8B-fwM3BNvID853wd2A8e8lirU1BaI"
client = genai.Client(api_key=api_key)

print("Testing gemini-2.0-flash model...")

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Explain what a database transaction is in one sentence."
    )
    
    print("✓ Success!")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
