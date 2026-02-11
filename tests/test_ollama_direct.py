#!/usr/bin/env python3
"""
Quick test of Ollama API directly
"""
import requests
import json

def test_ollama_simple():
    """Simple test with minimal prompt"""
    url = "http://localhost:11434/api/generate"
    
    # Try with a very simple prompt first
    payload = {
        "model": "llama2:latest",  # Using smaller model for testing
        "prompt": "What is 2+2?",
        "stream": False,
        "options": {
            "num_predict": 50  # Limit tokens for quick test
        }
    }
    
    print("Testing Ollama with simple prompt...")
    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Success!")
            print(f"Response: {data.get('response', '')}")
            print(f"Tokens: {data.get('eval_count', 0)}")
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"\n✗ Exception: {e}")

if __name__ == '__main__':
    test_ollama_simple()
