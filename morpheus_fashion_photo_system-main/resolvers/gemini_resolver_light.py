"""
Gemini Resolver Light for Morpheus Fashion Photo System
Creative multimodal resolver that generates artistic photography descriptions
"""

import json
import os
import re
import time
import base64
import io
from typing import Dict, Any, Optional, Tuple, List

import requests
HAS_REQUESTS = True

try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    np = None


class GeminiResolverLight:
    
    def __init__(self, config_loader):
        self.config = config_loader
        self.debug_entries = []
        self.raw_response = ""
        self.manifest = {
            "provided": [],
            "sent": [],
            "blocked": []
        }
        self.image_stats = []
    
    def _log(self, message: str):
        self.debug_entries.append(message)
    
    def get_debug_log(self) -> str:
        return "\n".join(self.debug_entries)
    
    def get_raw_response(self) -> str:
        return self.raw_response
    
    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not available"
        if not HAS_PIL:
            return False, "PIL/Pillow not available for image processing"
        return True, "ready"
    
    def _normalize_model_id(self, model_id: str) -> str:
        if model_id.startswith("models/"):
            model_id = model_id[7:]
        return model_id
    
    def _image_to_base64(self, image_tensor, label: str) -> Optional[Dict[str, Any]]:
        if image_tensor is None:
            return None
        
        if not HAS_PIL:
            self._log(f"[WARN] PIL not available, cannot process {label}")
            return None
        
        presets = self.config.get_gemini_presets()
        max_size = presets.get("max_image_size", 1024)
        jpeg_quality = presets.get("jpeg_quality", 85)
        
        try:
            pil_image = None
            
            if isinstance(image_tensor, Image.Image):
                pil_image = image_tensor
                if pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')
            elif hasattr(image_tensor, 'cpu'):
                img_array = image_tensor.cpu().numpy()
                pil_image = self._array_to_pil(img_array, label)
            elif isinstance(image_tensor, np.ndarray):
                pil_image = self._array_to_pil(image_tensor, label)
            else:
                self._log(f"[WARN] Unknown image type for {label}: {type(image_tensor)}")
                return None
            
            if pil_image is None:
                return None
            
            original_w, original_h = pil_image.size
            
            if max(pil_image.size) > max_size:
                ratio = max_size / max(pil_image.size)
                new_size = (int(pil_image.width * ratio), int(pil_image.height * ratio))
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
            
            final_w, final_h = pil_image.size
            
            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG", quality=jpeg_quality)
            jpeg_bytes = buffer.getvalue()
            base64_data = base64.b64encode(jpeg_bytes).decode('utf-8')
            
            self.image_stats.append({
                "label": label,
                "original_size": f"{original_w}x{original_h}",
                "final_size": f"{final_w}x{final_h}",
                "jpeg_bytes": len(jpeg_bytes)
            })
            
            return {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            }
            
        except Exception as e:
            self._log(f"[ERROR] Failed to process {label}: {str(e)[:100]}")
            return None
    
    def _array_to_pil(self, img_array: np.ndarray, label: str) -> Optional[Image.Image]:
        try:
            if img_array.ndim == 4:
                img_array = img_array[0]
            
            if img_array.ndim == 3:
                if img_array.shape[0] in [1, 3, 4]:
                    img_array = np.transpose(img_array, (1, 2, 0))
                
                if img_array.shape[2] == 1:
                    img_array = np.squeeze(img_array, axis=2)
            
            if img_array.dtype == np.float32 or img_array.dtype == np.float64:
                if img_array.max() <= 1.0:
                    img_array = (img_array * 255).astype(np.uint8)
                else:
                    img_array = img_array.astype(np.uint8)
            
            return Image.fromarray(img_array)
            
        except Exception as e:
            self._log(f"[ERROR] Array conversion failed for {label}: {str(e)[:100]}")
            return None
    
    def _prepare_image_parts(
        self,
        images: Dict[str, Any],
        seed_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        parts = []
        
        if images.get("talent_img") is not None:
            self.manifest["provided"].append("TALENT_REF")
            img_part = self._image_to_base64(images["talent_img"], "TALENT_REF")
            if img_part:
                parts.append({"text": "[TALENT_REF - STRICT Identity Lock: Preserve exact features, proportions, ethnicity]"})
                parts.append(img_part)
                self.manifest["sent"].append("TALENT_REF")
        
        for i in range(1, 7):
            key = f"garment_img_{i}"
            if images.get(key) is not None:
                self.manifest["provided"].append(f"GARMENT_REF_{i}")
                img_part = self._image_to_base64(images[key], f"GARMENT_REF_{i}")
                if img_part:
                    parts.append({"text": f"[GARMENT_REF_{i} - STRICT Fidelity: Describe EXACT fit on model]"})
                    parts.append(img_part)
                    self.manifest["sent"].append(f"GARMENT_REF_{i}")
        
        if images.get("pose_ref_img") is not None:
            self.manifest["provided"].append("POSE_REF")
            img_part = self._image_to_base64(images["pose_ref_img"], "POSE_REF")
            if img_part:
                parts.append({"text": "[POSE_REF - EXACT REPLICATION: Copy this pose precisely - same body angles, limb positions, weight distribution]"})
                parts.append(img_part)
                self.manifest["sent"].append("POSE_REF")
        
        if images.get("photo_style_ref") is not None:
            self.manifest["provided"].append("PHOTO_STYLE_REF")
            img_part = self._image_to_base64(images["photo_style_ref"], "PHOTO_STYLE_REF")
            if img_part:
                parts.append({"text": "[PHOTO_STYLE_REF - CREATIVE ANALYSIS: Extract photographer style, camera equipment, lens characteristics, color grading, lighting setup]"})
                parts.append(img_part)
                self.manifest["sent"].append("PHOTO_STYLE_REF")
        
        for i in range(1, 3):
            key = f"location_ref_{i}"
            if images.get(key) is not None:
                self.manifest["provided"].append(f"LOCATION_REF_{i}")
                img_part = self._image_to_base64(images[key], f"LOCATION_REF_{i}")
                if img_part:
                    parts.append({"text": f"[LOCATION_REF_{i} - CREATIVE INTERPRETATION: Create SIMILAR environment with same mood and atmosphere]"})
                    parts.append(img_part)
                    self.manifest["sent"].append(f"LOCATION_REF_{i}")
        
        return parts
    
    def _log_manifest(self):
        self._log("")
        self._log("=== MANIFEST ===")
        self._log(f"PROVIDED: {', '.join(self.manifest['provided']) if self.manifest['provided'] else 'none'}")
        self._log(f"SENT: {', '.join(self.manifest['sent']) if self.manifest['sent'] else 'none'}")
    
    def _log_image_stats(self):
        if not self.image_stats:
            return
        
        self._log("")
        self._log("=== IMAGE STATS ===")
        total_bytes = 0
        for stat in self.image_stats:
            self._log(f"  {stat['label']}: {stat['original_size']} -> {stat['final_size']}, {stat['jpeg_bytes']} bytes")
            total_bytes += stat['jpeg_bytes']
        
        self._log(f"TOTAL: {len(self.image_stats)} images, {total_bytes:,} bytes")
    
    def _build_creative_prompt(self, seed_state: Dict[str, Any]) -> str:
        prompts = self.config.get_gemini_prompts_light()
        
        system_prompt = prompts.get("system_prompt", "")
        vision_analysis = prompts.get("vision_analysis_prompt", "")
        single_call = prompts.get("single_call_prompt", "")
        
        prompt_parts = [
            system_prompt,
            "",
            "## BRIEF",
            seed_state.get("brief_text", "Create a fashion editorial image"),
            "",
            "## TARGET AUDIENCE",
            seed_state.get("target_text", "Fashion-conscious consumers"),
            "",
            "## FORMAT",
            f"Aspect Ratio: {seed_state.get('format', '9:16')}",
            "",
            "## REFERENCES PROVIDED",
            f"- GARMENT_REF: {seed_state.get('garment_count', 1)} garment(s)",
            f"- POSE_REF: {'YES - REPLICATE EXACTLY' if seed_state.get('use_pose_ref') else 'NO - create creative pose'}",
            f"- PHOTO_STYLE_REF: {'YES - analyze for technical details' if seed_state.get('use_photo_style_ref') else 'NO - create original style'}",
            f"- LOCATION_REF: {seed_state.get('location_ref_count', 0)} reference(s) (create similar environment)",
            "",
            vision_analysis,
            "",
            single_call,
        ]
        
        return "\n".join(prompt_parts)
    
    def _get_json_structure(self) -> str:
        return """{
  "subject": {
    "description": "[Full description of model wearing garments in pose]",
    "mirror_rules": null,
    "age": "[Estimated age range]",
    "expression": {
      "eyes": {"look": "[Direction]", "energy": "[Quality]", "direction": "[Specific]"},
      "mouth": {"position": "[Position]", "energy": "[Quality]"},
      "overall": "[Summary]"
    }
  },
  "accessories": {
    "jewelry": "[Any jewelry or null]",
    "device": "[Any devices or null]",
    "prop": "[Any props or null]",
    "headwear": "[Any headwear or null]"
  },
  "photography": {
    "camera_style": "[e.g., 'In the style of Peter Lindbergh, shot on Hasselblad X2D 100C']",
    "angle": "[Camera angle]",
    "shot_type": "[Shot type and framing]",
    "aspect_ratio": "[Format ratio]",
    "texture": "[Grain, sharpness, skin rendering details]",
    "lighting": "[Complete lighting description]",
    "depth_of_field": "[Focus characteristics]"
  },
  "background": {
    "setting": "[Environment description]",
    "wall_color": "[Color or null]",
    "elements": ["[Background elements]"],
    "atmosphere": "[Mood]",
    "lighting": "[Background lighting]"
  },
  "the_vibe": {
    "energy": "[Overall energy]",
    "mood": "[Emotional mood]",
    "aesthetic": "[Visual style]",
    "authenticity": "[Type]",
    "intimacy": "[Level]",
    "story": "[Narrative]",
    "caption_energy": "[Caption style]"
  },
  "constraints": {
    "must_keep": ["[Essential elements to preserve]"],
    "avoid": ["[Elements to avoid]"]
  },
  "negative_prompt": ["[Negative prompt items]"]
}"""
    
    def resolve(
        self,
        seed_state: Dict[str, Any],
        images: Dict[str, Any],
        api_key: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        
        self.debug_entries = []
        self.raw_response = ""
        self.manifest = {"provided": [], "sent": [], "blocked": []}
        self.image_stats = []
        
        self._log("=== GEMINI LIGHT RESOLVER START ===")
        self._log(f"Mode: Creative Interpretation")
        self._log(f"Model: {model_id}")
        self._log(f"Temperature: {temperature}")
        
        available, status = self.is_available()
        if not available:
            self._log(f"[ERROR] Resolver not available: {status}")
            return None, None, self.get_debug_log()
        
        if not api_key:
            self._log("[ERROR] No API key provided")
            return None, None, self.get_debug_log()
        
        image_parts = self._prepare_image_parts(images, seed_state)
        self._log_manifest()
        self._log_image_stats()
        
        if len(image_parts) == 0:
            self._log("[ERROR] No images could be processed")
            return None, None, self.get_debug_log()
        
        creative_prompt = self._build_creative_prompt(seed_state)
        json_structure = self._get_json_structure()
        
        full_prompt = f"""{creative_prompt}

## OUTPUT FORMAT
Return a valid JSON object following this EXACT structure:
{json_structure}

After the JSON, on a new line, provide a NANO_BANANA_PROMPT:
- Single sentence starting with "Make"
- Include talent, garments, pose, environment, and technical photography style
- Maximum 500 characters
- Be poetic but precise

Format your response as:
```json
[your JSON here]
```

NANO_BANANA_PROMPT: Make [your prompt here]
"""
        
        presets = self.config.get_gemini_presets()
        model_config = presets.get("models", {}).get(model_id, {})
        timeout = model_config.get("timeout_seconds", 45)
        retry_count = model_config.get("retry_count", 2)
        
        for attempt in range(retry_count + 1):
            try:
                self._log(f"[API] Attempt {attempt + 1}/{retry_count + 1}")
                
                result, status_code = self._call_gemini_api(
                    api_key=api_key,
                    model_id=model_id,
                    prompt=full_prompt,
                    image_parts=image_parts,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                if result:
                    self.raw_response = result
                    resolved_json, nano_prompt = self._parse_response(result)
                    
                    if resolved_json:
                        self._log("[SUCCESS] Response parsed successfully")
                        return resolved_json, nano_prompt, self.get_debug_log()
                    else:
                        self._log("[WARN] Failed to parse response, retrying...")
                        self._log(f"[DEBUG] Raw response preview: {result[:500]}...")
                else:
                    self._log(f"[WARN] No response (status: {status_code})")
                    
            except Exception as e:
                self._log(f"[ERROR] Attempt failed: {str(e)[:100]}")
                if attempt < retry_count:
                    time.sleep(1)
        
        self._log("[ERROR] All attempts failed")
        return None, None, self.get_debug_log()
    
    def _call_gemini_api(
        self,
        api_key: str,
        model_id: str,
        prompt: str,
        image_parts: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Tuple[Optional[str], int]:
        
        presets = self.config.get_gemini_presets()
        base_url = presets.get("api_base_url", "https://generativelanguage.googleapis.com/v1beta/models")
        
        model_id = self._normalize_model_id(model_id)
        url = f"{base_url}/{model_id}:generateContent?key={api_key}"
        
        parts = []
        parts.extend(image_parts)
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            image_count = len([p for p in image_parts if 'inline_data' in p])
            self._log(f"[API] Calling {model_id} ({image_count} images)...")
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            status_code = response.status_code
            
            self._log(f"[API] Status: {status_code}")
            
            if status_code != 200:
                error_text = response.text[:500]
                self._log(f"[ERROR] {error_text}")
                self.raw_response = f"API Error {status_code}: {error_text}"
                return None, status_code
            
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            self._log(f"[API] Response: {len(text)} chars")
            return text, 200
            
        except requests.exceptions.Timeout:
            self._log(f"[ERROR] Timeout after {timeout}s")
            return None, 408
        except Exception as e:
            self._log(f"[ERROR] Request failed: {str(e)[:100]}")
            return None, 0
    
    def _parse_response(self, response: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        resolved_json = None
        nano_prompt = None
        
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                resolved_json = json.loads(json_match.group(1))
                self._log("[PARSE] JSON extracted from code block")
            except json.JSONDecodeError as e:
                self._log(f"[PARSE] JSON decode error in code block: {str(e)[:80]}")
        
        if resolved_json is None:
            any_code_match = re.search(r'```(?:json|jsonc|JSON)?\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
            if any_code_match:
                content = any_code_match.group(1).strip()
                if content.startswith('{'):
                    try:
                        resolved_json = json.loads(content)
                        self._log("[PARSE] JSON extracted from generic code block")
                    except json.JSONDecodeError:
                        pass
        
        if resolved_json is None:
            decoder = json.JSONDecoder()
            search_pos = 0
            while search_pos < len(response):
                brace_pos = response.find('{', search_pos)
                if brace_pos == -1:
                    break
                try:
                    candidate, end_idx = decoder.raw_decode(response, brace_pos)
                    if isinstance(candidate, dict) and 'subject' in candidate:
                        resolved_json = candidate
                        self._log("[PARSE] JSON extracted by raw_decode (subject found)")
                        break
                    elif isinstance(candidate, dict) and len(candidate) > 3:
                        resolved_json = candidate
                        self._log("[PARSE] JSON extracted by raw_decode")
                        break
                    else:
                        search_pos = brace_pos + 1
                except json.JSONDecodeError:
                    search_pos = brace_pos + 1
        
        prompt_patterns = [
            r'NANO_BANANA_PROMPT:\s*(.+?)(?:\n\n|\n```|$)',
            r'NANO_BANANA_PROMPT:\s*(.+?)(?:\n|$)',
            r'Nano[_\s]?Banana[_\s]?Prompt:\s*(.+?)(?:\n\n|\n```|$)',
            r'(?:^|\n)(Make\s+(?:a\s+)?(?:fashion\s+)?photograph.+?)(?:\n\n|\n```|$)',
            r'(?:^|\n)(Make\s+.{50,500})(?:\n|$)',
        ]
        
        for pattern in prompt_patterns:
            prompt_match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if prompt_match:
                candidate = prompt_match.group(1).strip()
                if candidate.startswith("Make") and len(candidate) > 30:
                    nano_prompt = candidate
                    if len(nano_prompt) > 500:
                        nano_prompt = nano_prompt[:500]
                    self._log(f"[PARSE] Nano prompt extracted: {len(nano_prompt)} chars")
                    break
        
        if nano_prompt is None:
            make_match = re.search(r'(Make\s+.+?)(?:\n\n|\n```|$)', response, re.DOTALL)
            if make_match:
                nano_prompt = make_match.group(1).strip()
                if len(nano_prompt) > 30:
                    if len(nano_prompt) > 500:
                        nano_prompt = nano_prompt[:500]
                    self._log(f"[PARSE] Nano prompt found (fallback): {len(nano_prompt)} chars")
        
        return resolved_json, nano_prompt
