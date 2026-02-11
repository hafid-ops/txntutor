"""List available Gemini models"""
from google import genai

api_key = "AIzaSyANi8B-fwM3BNvID853wd2A8e8lirU1BaI"
client = genai.Client(api_key=api_key)

print("Listing available Gemini models...\n")

try:
    models = client.models.list()
    
    print("Available models:\n")
    
    for model in models:
        print(f"Model: {model.name}")
        if hasattr(model, 'display_name'):
            print(f"  Display Name: {model.display_name}")
        if hasattr(model, 'description'):
            print(f"  Description: {model.description[:100]}...")
        if hasattr(model, 'supported_generation_methods'):
            print(f"  Supported methods: {model.supported_generation_methods}")
        print()
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
