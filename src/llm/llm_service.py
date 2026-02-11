# LLM Service (Ollama / Gemini / OpenAI)
import requests
import json
import time
import logging
from typing import Dict, Optional
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import config

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLM providers to generate explanations"""
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self.model = config.LLM_MODEL
        self.api_key = config.LLM_API_KEY
        self.ollama_base_url = config.OLLAMA_BASE_URL
    
    def generate_explanation(
        self,
        anomaly_type: str,
        trace_events: list,
        anomaly_description: str,
        context: Dict = None
    ) -> Dict:
        """
        Generate an explanation for a detected anomaly
        
        Args:
            anomaly_type: Type of anomaly (e.g., 'lost_update', 'dirty_read')
            trace_events: List of trace event dictionaries
            anomaly_description: Description of what was detected
            context: Additional context (isolation level, etc.)
        
        Returns:
            Dict with 'explanation', 'tokens_used', 'generation_time_ms'
        """
        prompt = self._build_prompt(anomaly_type, trace_events, anomaly_description, context)
        
        start_time = time.time()
        
        try:
            if self.provider == 'ollama':
                result = self._call_ollama(prompt)
            elif self.provider == 'gemini':
                result = self._call_gemini(prompt)
            elif self.provider == 'openai':
                result = self._call_openai(prompt)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'explanation': result['text'],
                'tokens_used': result.get('tokens_used'),
                'generation_time_ms': generation_time_ms,
                'model': self.model
            }
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                'explanation': f"Failed to generate explanation: {str(e)}",
                'tokens_used': 0,
                'generation_time_ms': int((time.time() - start_time) * 1000),
                'model': self.model
            }
    
    def _build_prompt(self, anomaly_type: str, trace_events: list, anomaly_description: str, context: Dict = None) -> str:
        """Build the prompt for the LLM"""
        
        # Format trace events into a readable timeline
        timeline = []
        for event in trace_events:
            tx_name = event.get('tx_name', 'T?')
            event_type = event.get('event_type')
            table_name = event.get('table_name', '')
            record_key = event.get('record_key', '')
            old_value = event.get('old_value', '')
            new_value = event.get('new_value', '')
            
            if event_type == 'BEGIN':
                timeline.append(f"{tx_name}: BEGIN TRANSACTION")
            elif event_type == 'READ':
                timeline.append(f"{tx_name}: READ {table_name}[{record_key}] = {old_value}")
            elif event_type == 'WRITE':
                timeline.append(f"{tx_name}: WRITE {table_name}[{record_key}] = {new_value} (was {old_value})")
            elif event_type == 'COMMIT':
                timeline.append(f"{tx_name}: COMMIT")
            elif event_type == 'ROLLBACK':
                timeline.append(f"{tx_name}: ROLLBACK")
            else:
                timeline.append(f"{tx_name}: {event_type}")
        
        timeline_str = "\n".join([f"{i+1}. {line}" for i, line in enumerate(timeline)])
        
        isolation_level = context.get('isolation_level', 'READ COMMITTED') if context else 'READ COMMITTED'
        
        prompt = f"""You are a database concurrency expert. Explain this transaction anomaly in a clear, concise way.

**Anomaly:** {anomaly_type}
**Isolation Level:** {isolation_level}

**Timeline:**
{timeline_str}

**Detected Issue:**
{anomaly_description}

Provide a SHORT explanation with EXACTLY these sections (keep each section to 2-3 sentences max):

## 🎯 The Problem
Explain what went wrong in simple terms.

## 🔍 Why It Happened  
Explain which steps in the timeline caused this issue.

## ✅ The Solution
State which isolation level prevents this (SERIALIZABLE, REPEATABLE READ, READ COMMITTED, or READ UNCOMMITTED) and why.

BE CONCISE. Use simple language. No unnecessary details."""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> Dict:
        """Call Ollama local API"""
        url = f"{self.ollama_base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'text': data.get('response', ''),
                'tokens_used': data.get('eval_count', 0)
            }
        
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to Ollama at {self.ollama_base_url}. Is Ollama running?")
        except requests.exceptions.Timeout:
            raise Exception("Ollama request timed out")
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def _call_gemini(self, prompt: str) -> Dict:
        """Call Google Gemini API"""
        try:
            # Use the new google.genai package
            from google import genai
            
            client = genai.Client(api_key=self.api_key)
            
            # Use configured model name directly
            model_name = self.model
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            return {
                'text': response.text,
                'tokens_used': None  # Token info not readily available in new API
            }
        
        except ImportError:
            # Fallback to old API if new one not available
            try:
                import google.generativeai as genai
                
                genai.configure(api_key=self.api_key)
                
                model = genai.GenerativeModel(self.model)
                
                response = model.generate_content(prompt)
                
                return {
                    'text': response.text,
                    'tokens_used': response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
                }
            except ImportError:
                raise Exception("Neither google-genai nor google-generativeai package is installed. Run: pip install google-genai")
        
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _call_openai(self, prompt: str) -> Dict:
        """Call OpenAI API"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a database transaction expert who explains concurrency issues clearly."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                'text': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens
            }
        
        except ImportError:
            raise Exception("openai package not installed. Run: pip install openai")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def test_connection(self) -> tuple[bool, str]:
        """Test if the LLM service is accessible"""
        try:
            if self.provider == 'ollama':
                # Test Ollama connection
                url = f"{self.ollama_base_url}/api/tags"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.model in model_names:
                    return True, f"Connected to Ollama. Model '{self.model}' is available."
                else:
                    return False, f"Connected to Ollama, but model '{self.model}' not found. Available: {model_names}"
            
            elif self.provider == 'gemini':
                # Simple test for Gemini
                if not self.api_key:
                    return False, "Gemini API key not configured"
                return True, f"Gemini configured with model: {self.model}"
            
            elif self.provider == 'openai':
                # Simple test for OpenAI
                if not self.api_key:
                    return False, "OpenAI API key not configured"
                return True, f"OpenAI configured with model: {self.model}"
            
            else:
                return False, f"Unknown provider: {self.provider}"
        
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
