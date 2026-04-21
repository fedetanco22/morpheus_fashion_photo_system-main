"""
Morpheus Gemini API Verification Node
Tests the Gemini API connection and returns detailed status
"""

import os
from typing import Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .config_loader import ConfigLoader


class MorpheusVerifyGeminiAPI:
    
    def __init__(self):
        self.config = ConfigLoader()
    
    @classmethod
    def INPUT_TYPES(cls):
        config = ConfigLoader()
        gemini_models = config.get_gemini_model_ids()
        
        return {
            "required": {},
            "optional": {
                "gemini_api_key": ("STRING", {"default": ""}),
                "gemini_model": (gemini_models,),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("api_key_status",)
    FUNCTION = "verify"
    CATEGORY = "Morpheus/Prompt"
    
    def verify(
        self,
        gemini_api_key: str = "",
        gemini_model: str = "gemini-2.0-flash"
    ) -> Tuple[str]:
        
        log_lines = []
        
        log_lines.append("=" * 50)
        log_lines.append("GEMINI API VERIFICATION")
        log_lines.append("=" * 50)
        
        if not HAS_REQUESTS:
            log_lines.append("[ERROR] requests library not installed")
            return ("\n".join(log_lines),)
        
        api_key = gemini_api_key.strip() if gemini_api_key else ""
        
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
            if api_key:
                log_lines.append("[INFO] Using API key from environment variable")
                log_lines.append(f"[INFO] Key length: {len(api_key)} chars")
            else:
                log_lines.append("[ERROR] No API key provided")
                log_lines.append("[HINT] Set GEMINI_API_KEY environment variable")
                log_lines.append("[HINT] Or provide key in gemini_api_key input")
                log_lines.append("")
                log_lines.append("STATUS: API key not verified")
                return ("\n".join(log_lines),)
        else:
            log_lines.append("[INFO] Using provided API key")
            log_lines.append(f"[INFO] Key length: {len(api_key)} chars")
        
        log_lines.append(f"[INFO] Testing model: {gemini_model}")
        
        presets = self.config.get_gemini_presets()
        base_url = presets.get("api_base_url", "https://generativelanguage.googleapis.com/v1beta/models")
        
        url = f"{base_url}/{gemini_model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Say 'API working' in exactly 2 words."}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 10
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            log_lines.append("[INFO] Sending test request...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            log_lines.append(f"[INFO] HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    log_lines.append(f"[SUCCESS] Response: {text.strip()}")
                    log_lines.append("")
                    log_lines.append("STATUS: API key verified OK")
                except (KeyError, IndexError) as e:
                    log_lines.append(f"[WARN] Unexpected response structure: {e}")
                    log_lines.append(f"[INFO] Raw response: {str(data)[:200]}")
                    log_lines.append("")
                    log_lines.append("STATUS: API key verified (partial)")
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                log_lines.append(f"[ERROR] Bad request: {error_msg}")
                log_lines.append("")
                log_lines.append("STATUS: API key may be invalid")
            elif response.status_code == 401:
                log_lines.append("[ERROR] Authentication failed - invalid API key")
                log_lines.append("")
                log_lines.append("STATUS: API key INVALID")
            elif response.status_code == 403:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Access denied")
                log_lines.append(f"[ERROR] Access denied: {error_msg}")
                log_lines.append("[HINT] Check if the API is enabled in Google Cloud Console")
                log_lines.append("")
                log_lines.append("STATUS: API access denied")
            elif response.status_code == 404:
                log_lines.append(f"[ERROR] Model not found: {gemini_model}")
                log_lines.append("[HINT] Try a different model like gemini-2.0-flash")
                log_lines.append("")
                log_lines.append("STATUS: Model not available")
            elif response.status_code == 429:
                log_lines.append("[ERROR] Rate limit exceeded")
                log_lines.append("[HINT] Wait a few seconds and try again")
                log_lines.append("")
                log_lines.append("STATUS: Rate limited (key works)")
            else:
                log_lines.append(f"[ERROR] Unexpected status: {response.status_code}")
                log_lines.append(f"[INFO] Response: {response.text[:300]}")
                log_lines.append("")
                log_lines.append("STATUS: API key not verified")
                
        except requests.exceptions.Timeout:
            log_lines.append("[ERROR] Request timed out (30s)")
            log_lines.append("[HINT] Check your network connection")
            log_lines.append("")
            log_lines.append("STATUS: Connection timeout")
        except requests.exceptions.ConnectionError as e:
            log_lines.append(f"[ERROR] Connection failed: {str(e)[:100]}")
            log_lines.append("[HINT] Check your network connection")
            log_lines.append("")
            log_lines.append("STATUS: Connection error")
        except Exception as e:
            log_lines.append(f"[ERROR] Unexpected error: {str(e)[:200]}")
            log_lines.append("")
            log_lines.append("STATUS: Error occurred")
        
        return ("\n".join(log_lines),)
