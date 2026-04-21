"""
Gemini Resolver for Morpheus Fashion Photo System
Multimodal vision-based resolver that analyzes images and produces RESOLVED_JSON + NANO_BANANA_PROMPT
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


class GeminiResolver:
    STUDIO_KEYWORDS = [
        "studio", "cyclorama", "backdrop", "white seamless", 
        "in studio", "studio setting", "studio shot", "white background",
        "grey background", "gray background", "solid background"
    ]
    
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
    
    def is_available(self) -> Tuple[bool, str]:
        if not HAS_REQUESTS:
            return False, "requests library not available"
        if not HAS_PIL:
            return False, "PIL/Pillow not available for image processing"
        return True, "ready"
    
    def _detect_studio_in_brief(self, brief_text: str) -> bool:
        if not brief_text:
            return False
        
        brief_lower = brief_text.lower()
        presets = self.config.get_gemini_presets()
        keywords = presets.get("studio_keywords", self.STUDIO_KEYWORDS)
        
        for keyword in keywords:
            if keyword.lower() in brief_lower:
                return True
        return False
    
    def _normalize_model_id(self, model_id: str) -> str:
        if model_id.startswith("models/"):
            model_id = model_id[7:]
        return model_id
    
    def _image_to_base64(self, image_tensor, label: str, original_size: Tuple[int, int] = None) -> Optional[Dict[str, Any]]:
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
                "jpeg_bytes": len(jpeg_bytes),
                "base64_bytes": len(base64_data)
            })
            
            self._log(f"[IMAGE] {label}: {original_w}x{original_h} → {final_w}x{final_h}, {len(jpeg_bytes)} bytes JPEG")
            
            return {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            }
            
        except Exception as e:
            self._log(f"[ERROR] Failed to process image {label}: {str(e)}")
            return None
    
    def _array_to_pil(self, img_array, label: str):
        try:
            if img_array.ndim == 4:
                img_array = img_array[0]
            
            if img_array.ndim == 3:
                if img_array.shape[0] in [1, 3, 4]:
                    img_array = np.transpose(img_array, (1, 2, 0))
            
            if img_array.dtype == np.float32 or img_array.dtype == np.float64:
                img_array = (img_array * 255).clip(0, 255).astype(np.uint8)
            
            if len(img_array.shape) == 3 and img_array.shape[-1] == 1:
                img_array = np.squeeze(img_array, axis=-1)
            
            pil_image = Image.fromarray(img_array)
            
            if pil_image.mode == 'RGBA':
                pil_image = pil_image.convert('RGB')
            
            return pil_image
        except Exception as e:
            self._log(f"[ERROR] Failed to convert array to PIL for {label}: {str(e)}")
            return None
    
    def resolve(
        self,
        seed_state: Dict[str, Any],
        images: Dict[str, Any],
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None,
        gemini_mode: str = "dual_call"
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        
        self.debug_entries = []
        self.raw_response = ""
        self.manifest = {"provided": [], "sent": [], "blocked": []}
        self.image_stats = []
        
        self._log("=" * 60)
        self._log("GEMINI VISION RESOLVER START")
        self._log("=" * 60)
        self._log(f"Mode: {gemini_mode}")
        
        available, reason = self.is_available()
        if not available:
            self._log(f"[ERROR] Gemini not available: {reason}")
            return None, None, self.get_debug_log()
        
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if api_key:
                self._log("[CONFIG] Using API key from environment variable")
        else:
            self._log("[CONFIG] Using provided API key")
        
        if not api_key:
            self._log("[ERROR] No API key provided or found in environment")
            self._log("[HINT] Set GEMINI_API_KEY environment variable or provide gemini_api_key input")
            return None, None, self.get_debug_log()
        
        presets = self.config.get_gemini_presets()
        
        if model_id is None:
            model_id = presets.get("default_model", "gemini-2.0-flash")
        
        model_id = self._normalize_model_id(model_id)
        fallback_model = self._normalize_model_id(presets.get("fallback_model", "gemini-2.0-flash"))
        
        model_config = self.config.get_gemini_model(model_id)
        
        resolved_temperature: float = temperature if temperature is not None else float(model_config.get("recommended_temperature", 0.3))
        resolved_max_tokens: int = max_tokens if max_tokens is not None else int(model_config.get("recommended_max_tokens", 4096))
        resolved_timeout: int = timeout if timeout is not None else int(model_config.get("timeout_seconds", 60))
        resolved_retry_count: int = retry_count if retry_count is not None else int(model_config.get("retry_count", 2))
        
        self._log(f"[CONFIG] Model: {model_id}, Fallback: {fallback_model}")
        self._log(f"[CONFIG] Temp: {resolved_temperature}, MaxTokens: {resolved_max_tokens}, Timeout: {resolved_timeout}s")
        
        brief_implies_studio = self._detect_studio_in_brief(seed_state.get("brief_text", ""))
        if brief_implies_studio:
            self._log("[STUDIO RULE] Brief contains studio keywords - location refs will be blocked")
            seed_state["brief_implies_studio"] = True
        
        image_parts = self._prepare_image_parts(images, seed_state, brief_implies_studio)
        
        self._log_manifest()
        self._log_image_stats()
        
        self._log(f"[IMAGES] Prepared {len([p for p in image_parts if 'inline_data' in p])} images for API call")
        
        if gemini_mode == "single_call":
            return self._resolve_single_call(
                seed_state=seed_state,
                image_parts=image_parts,
                api_key=api_key,
                model_id=model_id,
                fallback_model=fallback_model,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                timeout=resolved_timeout,
                retry_count=resolved_retry_count
            )
        else:
            return self._resolve_dual_call(
                seed_state=seed_state,
                image_parts=image_parts,
                api_key=api_key,
                model_id=model_id,
                fallback_model=fallback_model,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                timeout=resolved_timeout,
                retry_count=resolved_retry_count
            )
    
    def _prepare_image_parts(self, images: Dict[str, Any], seed_state: Dict[str, Any], brief_implies_studio: bool) -> List[Dict[str, Any]]:
        parts = []
        
        if images.get("talent_img") is not None:
            self.manifest["provided"].append("TALENT_IMG")
            img_part = self._image_to_base64(images["talent_img"], "TALENT_IMG")
            if img_part:
                parts.append({"text": "[TALENT_IMG - Identity Lock Active]"})
                parts.append(img_part)
                self.manifest["sent"].append("TALENT_IMG")
        
        for i in range(1, 7):
            key = f"garment_img_{i}"
            if images.get(key) is not None:
                self.manifest["provided"].append(f"GARMENT_{i}")
                img_part = self._image_to_base64(images[key], f"GARMENT_{i}")
                if img_part:
                    parts.append({"text": f"[GARMENT_{i} - Fidelity Lock Active]"})
                    parts.append(img_part)
                    self.manifest["sent"].append(f"GARMENT_{i}")
        
        if images.get("brand_logo") is not None:
            self.manifest["provided"].append("BRAND_LOGO")
            if seed_state.get("use_logo"):
                img_part = self._image_to_base64(images["brand_logo"], "BRAND_LOGO")
                if img_part:
                    parts.append({"text": "[BRAND_LOGO]"})
                    parts.append(img_part)
                    self.manifest["sent"].append("BRAND_LOGO")
            else:
                self.manifest["blocked"].append(("BRAND_LOGO", "use_logo toggle off"))
        
        if images.get("pose_ref_img") is not None:
            self.manifest["provided"].append("POSE_REF")
            if seed_state.get("use_pose_ref"):
                img_part = self._image_to_base64(images["pose_ref_img"], "POSE_REF")
                if img_part:
                    parts.append({"text": "[POSE_REFERENCE - Use this pose as guidance]"})
                    parts.append(img_part)
                    self.manifest["sent"].append("POSE_REF")
            else:
                self.manifest["blocked"].append(("POSE_REF", "use_pose_ref toggle off"))
        
        for i in range(1, 4):
            key = f"photo_style_ref_{i}"
            if images.get(key) is not None:
                self.manifest["provided"].append(f"STYLE_REF_{i}")
                if seed_state.get("use_photo_style_ref"):
                    img_part = self._image_to_base64(images[key], f"STYLE_REF_{i}")
                    if img_part:
                        parts.append({"text": f"[PHOTO_STYLE_REFERENCE_{i} - Match this visual style]"})
                        parts.append(img_part)
                        self.manifest["sent"].append(f"STYLE_REF_{i}")
                else:
                    self.manifest["blocked"].append((f"STYLE_REF_{i}", "use_photo_style_ref toggle off"))
        
        for i in range(1, 3):
            key = f"location_ref_{i}"
            if images.get(key) is not None:
                self.manifest["provided"].append(f"LOCATION_REF_{i}")
                
                if brief_implies_studio:
                    self.manifest["blocked"].append((f"LOCATION_REF_{i}", "brief studio rule"))
                elif seed_state.get("studio_override") == "ON":
                    self.manifest["blocked"].append((f"LOCATION_REF_{i}", "studio_override ON"))
                elif not seed_state.get("use_location_ref"):
                    self.manifest["blocked"].append((f"LOCATION_REF_{i}", "use_location_ref toggle off"))
                else:
                    img_part = self._image_to_base64(images[key], f"LOCATION_REF_{i}")
                    if img_part:
                        parts.append({"text": f"[LOCATION_REFERENCE_{i} - Use as environment inspiration]"})
                        parts.append(img_part)
                        self.manifest["sent"].append(f"LOCATION_REF_{i}")
        
        return parts
    
    def _log_manifest(self):
        self._log("")
        self._log("=== MANIFEST ===")
        self._log(f"PROVIDED: {', '.join(self.manifest['provided']) if self.manifest['provided'] else 'none'}")
        self._log(f"SENT: {', '.join(self.manifest['sent']) if self.manifest['sent'] else 'none'}")
        if self.manifest['blocked']:
            blocked_str = ", ".join([f"{slot}({reason})" for slot, reason in self.manifest['blocked']])
            self._log(f"BLOCKED: {blocked_str}")
        else:
            self._log("BLOCKED: none")
    
    def _log_image_stats(self):
        if not self.image_stats:
            return
        
        self._log("")
        self._log("=== IMAGE STATS ===")
        total_jpeg = 0
        total_base64 = 0
        for stat in self.image_stats:
            self._log(f"  {stat['label']}: {stat['original_size']} → {stat['final_size']}, {stat['jpeg_bytes']} bytes")
            total_jpeg += stat['jpeg_bytes']
            total_base64 += stat['base64_bytes']
        
        self._log(f"TOTAL: {len(self.image_stats)} images, {total_jpeg:,} bytes JPEG, {total_base64:,} bytes base64")
    
    def _build_vision_prompt(self, seed_state: Dict[str, Any]) -> str:
        prompts = self.config.get_gemini_prompts()
        
        vision_system = prompts.get("vision_system_prompt", prompts.get("system_prompt", ""))
        
        prompt_parts = [
            vision_system,
            "",
            "## BRIEF",
            seed_state.get("brief_text", "No brief provided"),
            "",
            "## TARGET AUDIENCE",
            seed_state.get("target_text", "Not specified"),
            "",
            "## CONFIGURATION",
            f"- Intent: {seed_state.get('intent', 'awareness')}",
            f"- Format: {seed_state.get('format', '9:16')}",
            f"- Camera Pack: {seed_state.get('camera_pack', 'editorial_static')}",
            f"- Shot Pack: {seed_state.get('shot_pack', 'medium_three_quarter')}",
            f"- Lighting Pack: {seed_state.get('lighting_pack', 'studio_high_key')}",
            f"- Environment Pack: {seed_state.get('environment_pack', 'minimal_studio_cyclorama')}",
            f"- Style Pack: {seed_state.get('style_pack', 'premium_restraint')}",
            f"- Branding Pack: {seed_state.get('branding_pack', 'logo_discreet_lower')}",
            "",
            "## FLAGS",
            f"- Studio Override: {seed_state.get('studio_override', 'AUTO')}",
            f"- Brief Implies Studio: {seed_state.get('brief_implies_studio', False)}",
            f"- Garment Count: {seed_state.get('garment_count', 1)}",
            f"- Use Logo: {seed_state.get('use_logo', False)}",
            f"- Use Pose Reference: {seed_state.get('use_pose_ref', False)}",
            f"- Use Photo Style Reference: {seed_state.get('use_photo_style_ref', False)} ({seed_state.get('style_ref_count', 0)} refs)",
            f"- Use Location Reference: {seed_state.get('use_location_ref', False)} ({seed_state.get('location_ref_count', 0)} refs)",
            "",
            "## INSTRUCTIONS",
            "Analyze ALL provided images carefully. The TALENT_IMG and GARMENT images have STRICT fidelity locks.",
            "If studio_override is ON or brief_implies_studio is True, use minimal studio environment.",
            "",
        ]
        
        return "\n".join(prompt_parts)
    
    def _resolve_single_call(
        self,
        seed_state: Dict[str, Any],
        image_parts: List[Dict[str, Any]],
        api_key: str,
        model_id: str,
        fallback_model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        retry_count: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        
        self._log("")
        self._log("=== SINGLE CALL MODE ===")
        
        prompts = self.config.get_gemini_prompts()
        single_call_template = prompts.get("single_call_prompt", "")
        
        vision_prompt = self._build_vision_prompt(seed_state)
        
        full_prompt = f"""{vision_prompt}

{single_call_template}

Produce a JSON response with this EXACT structure:
{{
  "resolved_json": {{
    "subject": {{"description": "...", "identity_lock": true, "gender": "...", "traits": [...]}},
    "wardrobe": {{"items": [...], "fit_priority": "...", "styling_notes": "..."}},
    "pose": {{"type": "...", "description": "...", "reference_used": true/false}},
    "photography": {{"camera": "...", "shot": "...", "framing": "..."}},
    "lighting": {{"type": "...", "mood": "...", "description": "..."}},
    "environment": {{"type": "...", "description": "...", "studio_override_applied": true/false}},
    "style": {{"aesthetic": "...", "color_grading": "...", "mood": "..."}},
    "branding": {{"logo_used": true/false, "placement": "...", "treatment": "..."}}
  }},
  "nano_banana_prompt": "Make [single sentence prompt starting with Make]",
  "analysis_log": ["brief analysis notes"]
}}
"""
        
        current_model = model_id
        
        for attempt in range(retry_count + 1):
            try:
                self._log(f"[API] Single call attempt {attempt + 1}/{retry_count + 1} with model {current_model}")
                
                result, status_code = self._call_gemini_api(
                    api_key=api_key,
                    model_id=current_model,
                    prompt=full_prompt,
                    image_parts=image_parts,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                if status_code == 404 and current_model != fallback_model:
                    self._log(f"[FALLBACK MODEL] Model {current_model} not found, trying {fallback_model}")
                    current_model = fallback_model
                    continue
                
                if result:
                    self.raw_response = result
                    parsed = self._parse_json_response(result)
                    
                    if parsed and "resolved_json" in parsed and "nano_banana_prompt" in parsed:
                        resolved = parsed["resolved_json"]
                        prompt = parsed["nano_banana_prompt"]
                        
                        if self._validate_resolved_json(resolved):
                            self._log("[SUCCESS] Valid response received (single call)")
                            self._log(f"[PROMPT] {prompt[:100]}...")
                            return resolved, prompt, self.get_debug_log()
                        else:
                            self._log("[WARN] JSON validation failed")
                    else:
                        self._log("[WARN] Missing required fields in response")
                
            except Exception as e:
                self._log(f"[ERROR] API call failed: {str(e)}")
                if attempt < retry_count:
                    time.sleep(1)
        
        self._log("[FALLBACK] Single call failed")
        return None, None, self.get_debug_log()
    
    def _resolve_dual_call(
        self,
        seed_state: Dict[str, Any],
        image_parts: List[Dict[str, Any]],
        api_key: str,
        model_id: str,
        fallback_model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        retry_count: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
        
        self._log("")
        self._log("=== DUAL CALL MODE ===")
        
        resolved_json = None
        current_model = model_id
        
        for attempt in range(retry_count + 1):
            try:
                self._log(f"[CALL 1] Vision analysis attempt {attempt + 1}/{retry_count + 1} with model {current_model}")
                
                resolved_json, status_code = self._call_1_vision_analysis(
                    seed_state=seed_state,
                    image_parts=image_parts,
                    api_key=api_key,
                    model_id=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                if status_code == 404 and current_model != fallback_model:
                    self._log(f"[FALLBACK MODEL] Model {current_model} not found, trying {fallback_model}")
                    current_model = fallback_model
                    continue
                
                if resolved_json:
                    self._log("[CALL 1] SUCCESS - RESOLVED_JSON obtained")
                    break
                    
            except Exception as e:
                self._log(f"[CALL 1] ERROR: {str(e)}")
                if attempt < retry_count:
                    time.sleep(1)
        
        if not resolved_json:
            self._log("[FALLBACK] Call 1 failed, returning None")
            return None, None, self.get_debug_log()
        
        nano_prompt = None
        for attempt in range(retry_count + 1):
            try:
                self._log(f"[CALL 2] Prompt compilation attempt {attempt + 1}/{retry_count + 1}")
                
                nano_prompt = self._call_2_prompt_compilation(
                    resolved_json=resolved_json,
                    seed_state=seed_state,
                    api_key=api_key,
                    model_id=current_model,
                    temperature=0.2,
                    max_tokens=512,
                    timeout=timeout
                )
                
                if nano_prompt:
                    self._log("[CALL 2] SUCCESS - NANO_BANANA_PROMPT obtained")
                    break
                    
            except Exception as e:
                self._log(f"[CALL 2] ERROR: {str(e)}")
                if attempt < retry_count:
                    time.sleep(1)
        
        if not nano_prompt:
            self._log("[FALLBACK] Call 2 failed, prompt will be compiled locally")
        
        return resolved_json, nano_prompt, self.get_debug_log()
    
    def _call_1_vision_analysis(
        self,
        seed_state: Dict[str, Any],
        image_parts: List[Dict[str, Any]],
        api_key: str,
        model_id: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Tuple[Optional[Dict[str, Any]], int]:
        
        self._log("[CALL 1] Vision Analysis - Analyzing images...")
        
        prompts = self.config.get_gemini_prompts()
        vision_prompt = self._build_vision_prompt(seed_state)
        
        analysis_template = prompts.get("vision_analysis_prompt", """
Analyze all provided images and produce a RESOLVED_JSON decision document.

CRITICAL RULES:
1. TALENT_IMG defines STRICT identity - preserve exact features, proportions, ethnicity
2. GARMENT images define STRICT fidelity - describe exactly what you see, no invention
3. Reference images (POSE, STYLE, LOCATION) provide guidance but can be adapted

Output valid JSON only, no explanations.
""")
        
        full_prompt = f"""{vision_prompt}

{analysis_template}

Return ONLY valid JSON with this structure:
{{
  "subject": {{"description": "...", "identity_lock": true, "gender": "...", "traits": [...]}},
  "wardrobe": {{"items": [...], "fit_priority": "...", "styling_notes": "..."}},
  "pose": {{"type": "...", "description": "...", "reference_used": true/false}},
  "photography": {{"camera": "...", "shot": "...", "framing": "..."}},
  "lighting": {{"type": "...", "mood": "...", "description": "..."}},
  "environment": {{"type": "...", "description": "...", "studio_override_applied": true/false}},
  "style": {{"aesthetic": "...", "color_grading": "...", "mood": "..."}},
  "branding": {{"logo_used": true/false, "placement": "...", "treatment": "..."}}
}}
"""
        
        result, status_code = self._call_gemini_api(
            api_key=api_key,
            model_id=model_id,
            prompt=full_prompt,
            image_parts=image_parts,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            json_mode=True
        )
        
        if result:
            self.raw_response += f"\n--- CALL 1 RESPONSE (Vision Analysis) ---\n{result}"
            parsed = self._parse_json_response(result)
            if parsed:
                if self._validate_resolved_json(parsed):
                    self._log("[CALL 1] JSON validation passed")
                    return parsed, status_code
                else:
                    self._log("[CALL 1] JSON validation failed - missing required fields")
            else:
                self._log("[CALL 1] Failed to parse JSON from response")
        else:
            self._log(f"[CALL 1] No response received (status: {status_code})")
        
        return None, status_code
    
    def _call_2_prompt_compilation(
        self,
        resolved_json: Dict[str, Any],
        seed_state: Dict[str, Any],
        api_key: str,
        model_id: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Optional[str]:
        
        self._log("[CALL 2] Prompt Compilation - Converting JSON to prompt...")
        
        prompts = self.config.get_gemini_prompts()
        
        prompt_template = prompts.get("prompt_compilation_prompt", """
Convert this RESOLVED_JSON into a single English sentence starting with "Make".

RULES:
1. Start with "Make"
2. Single sentence only - no lists, no labels, no explanations
3. No negative prompts
4. Flow naturally: subject → wardrobe → pose → photography → lighting → environment → style → branding
5. Be specific and descriptive but concise
6. Maximum 200 words

RESOLVED_JSON:
{resolved_json}

Output ONLY the prompt sentence starting with "Make":
""")
        
        full_prompt = prompt_template.replace("{resolved_json}", json.dumps(resolved_json, indent=2))
        
        result, status_code = self._call_gemini_api(
            api_key=api_key,
            model_id=model_id,
            prompt=full_prompt,
            image_parts=[],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            json_mode=False
        )
        
        if result:
            self.raw_response += f"\n--- CALL 2 RESPONSE (Prompt Compilation) ---\n{result}"
            prompt = result.strip()
            prompt = prompt.strip('"').strip("'")
            
            if prompt.startswith("Make"):
                self._log(f"[CALL 2] Valid prompt received: {prompt[:80]}...")
                return prompt
            elif "Make" in prompt:
                idx = prompt.find("Make")
                extracted = prompt[idx:].split("\n")[0].strip()
                self._log(f"[CALL 2] Extracted prompt: {extracted[:80]}...")
                return extracted
            else:
                self._log(f"[CALL 2] Prompt doesn't start with 'Make': {prompt[:50]}...")
        else:
            self._log(f"[CALL 2] No response received (status: {status_code})")
        
        return None
    
    def _call_gemini_api(
        self,
        api_key: str,
        model_id: str,
        prompt: str,
        image_parts: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        timeout: int,
        json_mode: bool = True
    ) -> Tuple[Optional[str], int]:
        
        presets = self.config.get_gemini_presets()
        base_url = presets.get("api_base_url", "https://generativelanguage.googleapis.com/v1beta/models")
        
        model_id = self._normalize_model_id(model_id)
        url = f"{base_url}/{model_id}:generateContent?key={api_key}"
        
        parts = []
        parts.extend(image_parts)
        parts.append({"text": prompt})
        
        image_count = len([p for p in image_parts if 'inline_data' in p])
        total_parts = len(parts)
        
        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            self._log(f"[API] Calling {model_id} ({image_count} images, {total_parts} parts)...")
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            status_code = response.status_code
            self._log(f"[API] HTTP Status: {status_code}")
            
            if status_code != 200:
                error_text = response.text[:1500]
                self._log(f"[ERROR] API returned status {status_code}")
                self._log(f"[ERROR] URL: {base_url}/{model_id}:generateContent")
                self._log(f"[ERROR] Model ID: {model_id}")
                self._log(f"[ERROR] Parts: {total_parts}, Images: {image_count}")
                self._log(f"[ERROR] Response: {error_text[:500]}")
                
                self.raw_response += f"\n--- API ERROR ---\n"
                self.raw_response += f"Status: {status_code}\n"
                self.raw_response += f"URL: {url.split('?')[0]}\n"
                self.raw_response += f"Model: {model_id}\n"
                self.raw_response += f"Parts: {total_parts}, Images: {image_count}\n"
                self.raw_response += f"Response:\n{error_text}\n"
                
                if status_code == 400:
                    if json_mode and "responseMimeType" in error_text.lower():
                        self._log("[RETRY] JSON mode failed, retrying without responseMimeType...")
                        payload["generationConfig"].pop("responseMimeType", None)
                        prompt_addition = "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or explanation."
                        parts[-1] = {"text": prompt + prompt_addition}
                        payload["contents"][0]["parts"] = parts
                        
                        retry_response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                        if retry_response.status_code == 200:
                            self._log("[RETRY] Success without JSON mode")
                            data = retry_response.json()
                            try:
                                text = data["candidates"][0]["content"]["parts"][0]["text"]
                                return text, 200
                            except (KeyError, IndexError):
                                pass
                    self._log("[ERROR] Bad request - check payload format")
                elif status_code == 401:
                    self._log("[ERROR] Invalid API key - check your GEMINI_API_KEY")
                elif status_code == 403:
                    self._log("[ERROR] API access denied - enable Gemini API in Google Cloud")
                elif status_code == 404:
                    self._log(f"[ERROR] Model '{model_id}' not found")
                elif status_code == 413:
                    self._log("[ERROR] Payload too large - reduce image count or size")
                elif status_code == 429:
                    self._log("[ERROR] Rate limit exceeded - wait and retry")
                elif status_code == 500:
                    self._log("[ERROR] Server error - try again later")
                
                return None, status_code
            
            data = response.json()
            self._log(f"[API] Response received successfully")
            
        except requests.exceptions.Timeout:
            self._log(f"[ERROR] API request timed out after {timeout}s")
            self.raw_response += f"\n--- TIMEOUT ---\nRequest timed out after {timeout}s\n"
            return None, 408
        except requests.exceptions.ConnectionError as e:
            self._log(f"[ERROR] Connection failed: {str(e)[:100]}")
            self.raw_response += f"\n--- CONNECTION ERROR ---\n{str(e)[:200]}\n"
            return None, 0
        except Exception as e:
            self._log(f"[ERROR] Request failed: {str(e)[:200]}")
            self.raw_response += f"\n--- REQUEST ERROR ---\n{str(e)[:200]}\n"
            return None, 0
        
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            self._log(f"[API] Got text response: {len(text)} chars")
            return text, 200
        except (KeyError, IndexError) as e:
            self._log(f"[ERROR] Unexpected response structure: {e}")
            self._log(f"[ERROR] Response data: {str(data)[:300]}")
            self.raw_response += f"\n--- PARSE ERROR ---\n{str(data)[:500]}\n"
            return None, 200
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        self._log(f"[PARSE] Failed to extract JSON from: {response_text[:200]}...")
        return None
    
    def _validate_resolved_json(self, data: Dict[str, Any]) -> bool:
        required_keys = [
            "subject", "wardrobe", "pose", "photography",
            "lighting", "environment", "style", "branding"
        ]
        
        for key in required_keys:
            if key not in data:
                self._log(f"[VALIDATION] Missing required key: {key}")
                return False
        
        if "subject" in data:
            if not data["subject"].get("identity_lock", False):
                self._log("[VALIDATION] WARNING: identity_lock not set to true")
        
        return True
    
    def get_debug_log(self) -> str:
        return "\n".join(self.debug_entries)
    
    def get_raw_response(self) -> str:
        return self.raw_response
