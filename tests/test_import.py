"""Test imports directly"""

print("Testing google.genai import...")
try:
    from google import genai
    print("✓ google.genai imported successfully")
except ImportError as e:
    print(f"✗ Failed to import google.genai: {e}")

print("\nTesting google.generativeai import...")
try:
    import google.generativeai as genai_old
    print("✓ google.generativeai imported successfully")
except ImportError as e:
    print(f"✗ Failed to import google.generativeai: {e}")

print("\nTesting Gemini client creation...")
try:
    from google import genai
    
    api_key = "AIzaSyANi8B-fwM3BNvID853wd2A8e8lirU1BaI"
    client = genai.Client(api_key=api_key)
    print(f"✓ Client created: {client}")
    
    print("\nTesting model generation...")
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents="Say hello in one word"
    )
    print(f"✓ Response: {response.text}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
