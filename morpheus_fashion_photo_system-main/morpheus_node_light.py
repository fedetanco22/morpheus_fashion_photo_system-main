"""
Morpheus Fashion Photo System Light - ComfyUI Custom Node
Simplified version with creative Gemini interpretation for technical and environmental decisions
"""

import json
import os
from typing import Dict, Any, List, Tuple, Optional

from .config_loader import ConfigLoader
from .resolvers.gemini_resolver_light import GeminiResolverLight


class MorpheusFashionPhotoSystemLight:
    HARDCODED_RULES = """
    === MORPHEUS LIGHT HARDCODED RULES (NON-MODIFIABLE) ===
    1. Output: Single English sentence starting with "Make"
    2. TALENT identity lock: STRICT preservation of identity and proportions
    3. GARMENTS fidelity: No redesign, no invention, perfect fit description
    4. POSE: EXACT replication from pose reference
    5. ENVIRONMENT: Creative interpretation similar to location reference
    6. STYLE: Creative technical description (photographer, equipment, lenses, distortions)
    7. References always active: pose, style, location
    """
    
    def __init__(self):
        self.config = ConfigLoader(mode="light")
    
    @classmethod
    def INPUT_TYPES(cls):
        config = ConfigLoader()
        gemini_models = config.get_gemini_model_ids()
        
        return {
            "required": {
                "talent_img": ("IMAGE",),
                "garment_img_1": ("IMAGE",),
                "brief_text": ("STRING", {"multiline": True, "default": ""}),
                "format": (["9:16", "16:9", "1:1", "4:5", "5:4", "3:4", "4:3"],),
            },
            "optional": {
                "garment_img_2": ("IMAGE",),
                "garment_img_3": ("IMAGE",),
                "garment_img_4": ("IMAGE",),
                "garment_img_5": ("IMAGE",),
                "garment_img_6": ("IMAGE",),
                "target_text": ("STRING", {"multiline": True, "default": ""}),
                "pose_ref_img": ("IMAGE",),
                "photo_style_ref": ("IMAGE",),
                "location_ref_1": ("IMAGE",),
                "location_ref_2": ("IMAGE",),
                "gemini_model": (gemini_models,),
                "gemini_api_key": ("STRING", {"default": ""}),
                "gemini_temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1}),
                "gemini_max_tokens": ("INT", {"default": 4096, "min": 512, "max": 8192}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("NANO_BANANA_PROMPT", "RESOLVED_JSON", "DEBUG_LOG", "GEMINI_RAW_RESPONSE", "ASPECT_RATIO")
    FUNCTION = "orchestrate"
    CATEGORY = "Morpheus/Prompt"
    
    def orchestrate(
        self,
        talent_img,
        garment_img_1,
        brief_text: str,
        format: str,
        garment_img_2=None,
        garment_img_3=None,
        garment_img_4=None,
        garment_img_5=None,
        garment_img_6=None,
        target_text: str = "",
        pose_ref_img=None,
        photo_style_ref=None,
        location_ref_1=None,
        location_ref_2=None,
        gemini_model: str = "gemini-2.0-flash",
        gemini_api_key: str = "",
        gemini_temperature: float = 0.7,
        gemini_max_tokens: int = 4096,
    ) -> Tuple[str, str, str, str, str]:
        
        debug_log_parts = []
        debug_log_parts.append("=" * 60)
        debug_log_parts.append("MORPHEUS FASHION PHOTO SYSTEM LIGHT - DEBUG LOG")
        debug_log_parts.append("=" * 60)
        debug_log_parts.append(self.HARDCODED_RULES)
        debug_log_parts.append("")
        
        validation_result, garment_count = self._validate_inputs(
            talent_img=talent_img,
            garment_imgs=[garment_img_1, garment_img_2, garment_img_3, 
                         garment_img_4, garment_img_5, garment_img_6],
            pose_ref_img=pose_ref_img,
            photo_style_ref=photo_style_ref,
            location_refs=[location_ref_1, location_ref_2]
        )
        
        debug_log_parts.append("=== INPUT VALIDATION ===")
        debug_log_parts.extend(validation_result)
        debug_log_parts.append(f"Garments count: {garment_count}")
        debug_log_parts.append("")
        
        has_style_ref = photo_style_ref is not None
        location_ref_count = sum(1 for ref in [location_ref_1, location_ref_2] if ref is not None)
        
        seed_state = {
            "brief_text": brief_text,
            "target_text": target_text,
            "format": format,
            "garment_count": garment_count,
            "use_pose_ref": pose_ref_img is not None,
            "use_photo_style_ref": has_style_ref,
            "use_location_ref": location_ref_count > 0,
            "location_ref_count": location_ref_count,
            "mode": "light",
        }
        
        images = {
            "talent_img": talent_img,
            "garment_img_1": garment_img_1,
            "garment_img_2": garment_img_2,
            "garment_img_3": garment_img_3,
            "garment_img_4": garment_img_4,
            "garment_img_5": garment_img_5,
            "garment_img_6": garment_img_6,
            "pose_ref_img": pose_ref_img,
            "photo_style_ref": photo_style_ref,
            "location_ref_1": location_ref_1,
            "location_ref_2": location_ref_2,
        }
        
        debug_log_parts.append("=== SEED STATE (LIGHT MODE) ===")
        debug_log_parts.append(f"Format: {format}")
        debug_log_parts.append(f"Garments: {garment_count}")
        debug_log_parts.append(f"POSE_REF: {'PROVIDED' if pose_ref_img is not None else 'NOT PROVIDED'}")
        debug_log_parts.append(f"PHOTO_STYLE_REF: {'PROVIDED' if has_style_ref else 'NOT PROVIDED'}")
        debug_log_parts.append(f"LOCATION_REF: {location_ref_count}")
        debug_log_parts.append(f"Mode: LIGHT (Creative Gemini Interpretation)")
        debug_log_parts.append("")
        
        resolved_json = None
        nano_banana_prompt = None
        gemini_raw_response = ""
        
        debug_log_parts.append("=== GEMINI LIGHT RESOLVER ===")
        debug_log_parts.append(f"Model: {gemini_model}")
        debug_log_parts.append(f"Temperature: {gemini_temperature} (higher = more creative)")
        
        api_key = gemini_api_key.strip() if gemini_api_key else None
        
        if api_key:
            debug_log_parts.append("API Key: PROVIDED")
        else:
            env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if env_key:
                debug_log_parts.append("API Key: FROM ENVIRONMENT")
                api_key = env_key
            else:
                debug_log_parts.append("API Key: NOT FOUND - Gemini will fail")
                debug_log_parts.append("[ERROR] No API key provided. Set GEMINI_API_KEY or provide in node.")
        
        if api_key:
            gemini_resolver = GeminiResolverLight(self.config)
            
            resolved_json, nano_banana_prompt, gemini_log = gemini_resolver.resolve(
                seed_state=seed_state,
                images=images,
                api_key=api_key,
                model_id=gemini_model,
                temperature=gemini_temperature,
                max_tokens=gemini_max_tokens
            )
            
            debug_log_parts.append(gemini_log)
            gemini_raw_response = gemini_resolver.get_raw_response()
            
            if resolved_json:
                debug_log_parts.append("[SUCCESS] Gemini Light resolver completed")
            else:
                debug_log_parts.append("[ERROR] Gemini Light resolver failed")
        
        if resolved_json is None:
            debug_log_parts.append("")
            debug_log_parts.append("[FALLBACK] Creating minimal structure")
            resolved_json = self._create_fallback_json(seed_state, garment_count)
            nano_banana_prompt = self._create_fallback_prompt(resolved_json)
        
        if nano_banana_prompt is None:
            nano_banana_prompt = self._create_fallback_prompt(resolved_json)
        
        debug_log_parts.append("")
        debug_log_parts.append("=== FINAL OUTPUT ===")
        debug_log_parts.append(f"Prompt length: {len(nano_banana_prompt)} chars")
        debug_log_parts.append("")
        debug_log_parts.append("NANO_BANANA_PROMPT:")
        debug_log_parts.append(nano_banana_prompt)
        debug_log_parts.append("")
        debug_log_parts.append("=" * 60)
        
        resolved_json_str = json.dumps(resolved_json, indent=2)
        debug_log = "\n".join(debug_log_parts)
        
        aspect_ratio = format
        
        return (nano_banana_prompt, resolved_json_str, debug_log, gemini_raw_response, aspect_ratio)
    
    def _validate_inputs(
        self,
        talent_img,
        garment_imgs: List,
        pose_ref_img,
        photo_style_ref,
        location_refs: List
    ) -> Tuple[List[str], int]:
        
        messages = []
        
        if talent_img is None:
            messages.append("[ERROR] TALENT_REF is required but not provided")
        else:
            messages.append("[OK] TALENT_REF provided - identity lock active")
        
        garment_count = sum(1 for g in garment_imgs if g is not None)
        if garment_count == 0:
            messages.append("[ERROR] At least one GARMENT_REF is required")
        else:
            messages.append(f"[OK] {garment_count} GARMENT_REF(s) provided - fidelity lock active")
        
        if pose_ref_img is not None:
            messages.append("[OK] POSE_REF provided - will be EXACTLY replicated")
        else:
            messages.append("[INFO] POSE_REF not provided - Gemini will suggest creative pose")
        
        if photo_style_ref is not None:
            messages.append("[OK] PHOTO_STYLE_REF - technical style will be analyzed")
        else:
            messages.append("[INFO] PHOTO_STYLE_REF not provided - Gemini will create original style")
        
        loc_count = sum(1 for l in location_refs if l is not None)
        if loc_count > 0:
            messages.append(f"[OK] {loc_count} LOCATION_REF(s) - similar environment will be created")
        else:
            messages.append("[INFO] No LOCATION_REF - Gemini will create environment from brief")
        
        return messages, garment_count
    
    def _create_fallback_json(self, seed_state: Dict[str, Any], garment_count: int) -> Dict[str, Any]:
        return {
            "subject": {
                "description": "Fashion model as shown in talent reference",
                "mirror_rules": None,
                "age": "as shown",
                "expression": {
                    "eyes": {"look": "natural", "energy": "confident", "direction": "toward camera"},
                    "mouth": {"position": "relaxed", "energy": "composed"},
                    "overall": "professional fashion expression"
                }
            },
            "accessories": {
                "jewelry": None,
                "device": None,
                "prop": None,
                "headwear": None
            },
            "photography": {
                "camera_style": "professional fashion photography",
                "angle": "eye level",
                "shot_type": "full body",
                "aspect_ratio": seed_state.get("format", "9:16"),
                "texture": "sharp, clean",
                "lighting": "professional studio",
                "depth_of_field": "moderate"
            },
            "background": {
                "setting": "as suggested by references",
                "wall_color": None,
                "elements": [],
                "atmosphere": "professional",
                "lighting": "balanced"
            },
            "the_vibe": {
                "energy": "confident",
                "mood": "editorial",
                "aesthetic": "fashion forward",
                "authenticity": "professional",
                "intimacy": "medium",
                "story": "fashion editorial",
                "caption_energy": "stylish"
            },
            "constraints": {
                "must_keep": [
                    "exact talent identity",
                    f"all {garment_count} garment(s) visible",
                    "pose from reference"
                ],
                "avoid": [
                    "identity changes",
                    "garment modifications",
                    "pose alterations"
                ]
            },
            "negative_prompt": [
                "low quality",
                "blurry",
                "bad anatomy",
                "wrong proportions"
            ]
        }
    
    def _create_fallback_prompt(self, resolved_json: Dict[str, Any]) -> str:
        subject = resolved_json.get("subject", {})
        photography = resolved_json.get("photography", {})
        
        return f"Make a fashion photograph of {subject.get('description', 'the model')} with {photography.get('camera_style', 'professional')} styling and {photography.get('lighting', 'balanced')} lighting."


NODE_CLASS_MAPPINGS = {
    "MorpheusFashionPhotoSystemLight": MorpheusFashionPhotoSystemLight
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MorpheusFashionPhotoSystemLight": "Morpheus Fashion Photo System (Light)"
}
