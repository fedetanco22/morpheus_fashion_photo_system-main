"""
Morpheus Fashion Photo System - Main ComfyUI Node
Fashion Advertising Decision System for Nano Banana prompt generation
"""

import json
from typing import Dict, Any, List, Tuple, Optional

from .config_loader import ConfigLoader
from .resolvers.local_resolver import LocalResolver
from .resolvers.gemini_resolver import GeminiResolver
from .prompt_compiler import PromptCompiler


class MorpheusFashionPhotoSystem:
    HARDCODED_RULES = """
    === MORPHEUS HARDCODED RULES (NON-MODIFIABLE) ===
    1. Output: Single English sentence starting with "Make"
    2. No lists, no labels, no explanations, no meta
    3. No negative prompts
    4. TALENT identity lock: STRICT preservation of identity and proportions
    5. GARMENTS fidelity: No redesign, no invention, all garments must appear
    6. Fit accuracy: Priority in consideration/fit tasks
    7. Priority hierarchy: Talent > Garments > Fit > Pose > Style > Location > Branding
    8. Studio override: When ON, ignores location references
    9. Default pose: Neutral fit-preserving when no reference
    10. Default style: Premium editorial realism when no reference
    """
    
    def __init__(self):
        self.config = ConfigLoader()
    
    @classmethod
    def INPUT_TYPES(cls):
        config = ConfigLoader()
        
        camera_packs = config.get_pack_ids("camera")
        shot_packs = config.get_pack_ids("shot")
        lighting_packs = config.get_pack_ids("lighting")
        environment_packs = ["AUTO"] + config.get_pack_ids("environment")
        style_packs = config.get_pack_ids("style")
        branding_packs = config.get_pack_ids("branding")
        lens_packs = config.get_pack_ids("lens")
        film_texture_packs = config.get_pack_ids("film_texture")
        color_science_packs = config.get_pack_ids("color_science")
        time_weather_packs = config.get_pack_ids("time_weather")
        pose_discipline_packs = config.get_pack_ids("pose_discipline")
        intents = list(config.get_intents().get("intents", {}).keys())
        gemini_models = config.get_gemini_model_ids()
        
        return {
            "required": {
                "talent_img": ("IMAGE",),
                "garment_img_1": ("IMAGE",),
                "brief_text": ("STRING", {"multiline": True, "default": ""}),
                
                "format": (["9:16", "16:9", "1:1", "4:5", "5:4", "3:4", "4:3"],),
                "intent": (intents,),
                "style_pack": (style_packs,),
                
                "camera_pack": (camera_packs,),
                "lens_pack": (lens_packs,),
                "film_texture_pack": (film_texture_packs,),
                "color_science_pack": (color_science_packs,),
                
                "shot_pack": (shot_packs,),
                "pose_discipline_pack": (pose_discipline_packs,),
                
                "lighting_pack": (lighting_packs,),
                "time_weather_pack": (time_weather_packs,),
                
                "environment_pack": (environment_packs,),
                "studio_override": (["AUTO", "ON", "OFF"],),
                
                "branding_pack": (branding_packs,),
            },
            "optional": {
                "garment_img_2": ("IMAGE",),
                "garment_img_3": ("IMAGE",),
                "garment_img_4": ("IMAGE",),
                "garment_img_5": ("IMAGE",),
                "garment_img_6": ("IMAGE",),
                "brand_logo": ("IMAGE",),
                "target_text": ("STRING", {"multiline": True, "default": ""}),
                "use_pose_ref": ("BOOLEAN", {"default": False}),
                "pose_ref_img": ("IMAGE",),
                "use_photo_style_ref": ("BOOLEAN", {"default": False}),
                "photo_style_ref_1": ("IMAGE",),
                "photo_style_ref_2": ("IMAGE",),
                "photo_style_ref_3": ("IMAGE",),
                "use_location_ref": ("BOOLEAN", {"default": False}),
                "location_ref_1": ("IMAGE",),
                "location_ref_2": ("IMAGE",),
                "use_gemini": ("BOOLEAN", {"default": True}),
                "gemini_mode": (["dual_call", "single_call"],),
                "gemini_model": (gemini_models,),
                "gemini_api_key": ("STRING", {"default": ""}),
                "gemini_temperature": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.1}),
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
        intent: str,
        camera_pack: str,
        shot_pack: str,
        lighting_pack: str,
        environment_pack: str,
        style_pack: str,
        branding_pack: str,
        lens_pack: str,
        film_texture_pack: str,
        color_science_pack: str,
        time_weather_pack: str,
        pose_discipline_pack: str,
        studio_override: str,
        garment_img_2=None,
        garment_img_3=None,
        garment_img_4=None,
        garment_img_5=None,
        garment_img_6=None,
        brand_logo=None,
        target_text: str = "",
        use_pose_ref: bool = False,
        pose_ref_img=None,
        use_photo_style_ref: bool = False,
        photo_style_ref_1=None,
        photo_style_ref_2=None,
        photo_style_ref_3=None,
        use_location_ref: bool = False,
        location_ref_1=None,
        location_ref_2=None,
        use_gemini: bool = True,
        gemini_mode: str = "dual_call",
        gemini_model: str = "gemini-3-flash",
        gemini_api_key: str = "",
        gemini_temperature: float = 0.3,
        gemini_max_tokens: int = 4096,
    ) -> Tuple[str, str, str, str, str]:
        
        debug_log_parts = []
        debug_log_parts.append("=" * 60)
        debug_log_parts.append("MORPHEUS FASHION PHOTO SYSTEM - DEBUG LOG")
        debug_log_parts.append("=" * 60)
        debug_log_parts.append(self.HARDCODED_RULES)
        debug_log_parts.append("")
        
        validation_result, garment_count = self._validate_inputs(
            talent_img=talent_img,
            garment_imgs=[garment_img_1, garment_img_2, garment_img_3, 
                         garment_img_4, garment_img_5, garment_img_6],
            use_pose_ref=use_pose_ref,
            pose_ref_img=pose_ref_img,
            use_photo_style_ref=use_photo_style_ref,
            photo_style_refs=[photo_style_ref_1, photo_style_ref_2, photo_style_ref_3],
            use_location_ref=use_location_ref,
            location_refs=[location_ref_1, location_ref_2]
        )
        
        debug_log_parts.append("=== INPUT VALIDATION ===")
        debug_log_parts.extend(validation_result)
        debug_log_parts.append(f"Garments count: {garment_count}")
        debug_log_parts.append("")
        
        style_ref_count = sum(1 for ref in [photo_style_ref_1, photo_style_ref_2, photo_style_ref_3] if ref is not None)
        location_ref_count = sum(1 for ref in [location_ref_1, location_ref_2] if ref is not None)
        
        seed_state = {
            "brief_text": brief_text,
            "target_text": target_text,
            "format": format,
            "garment_count": garment_count,
            "intent": intent,
            "camera_pack": camera_pack,
            "shot_pack": shot_pack,
            "lighting_pack": lighting_pack,
            "environment_pack": environment_pack if environment_pack != "AUTO" else "minimal_studio_cyclorama",
            "style_pack": style_pack,
            "branding_pack": branding_pack,
            "lens_pack": lens_pack,
            "film_texture_pack": film_texture_pack,
            "color_science_pack": color_science_pack,
            "time_weather_pack": time_weather_pack,
            "pose_discipline_pack": pose_discipline_pack,
            "studio_override": studio_override,
            "use_logo": brand_logo is not None,
            "use_pose_ref": use_pose_ref and pose_ref_img is not None,
            "use_photo_style_ref": use_photo_style_ref and style_ref_count > 0,
            "style_ref_count": style_ref_count,
            "use_location_ref": use_location_ref and location_ref_count > 0,
            "location_ref_count": location_ref_count,
        }
        
        images = {
            "talent_img": talent_img,
            "garment_img_1": garment_img_1,
            "garment_img_2": garment_img_2,
            "garment_img_3": garment_img_3,
            "garment_img_4": garment_img_4,
            "garment_img_5": garment_img_5,
            "garment_img_6": garment_img_6,
            "brand_logo": brand_logo,
            "pose_ref_img": pose_ref_img,
            "photo_style_ref_1": photo_style_ref_1,
            "photo_style_ref_2": photo_style_ref_2,
            "photo_style_ref_3": photo_style_ref_3,
            "location_ref_1": location_ref_1,
            "location_ref_2": location_ref_2,
        }
        
        debug_log_parts.append("=== SEED STATE ===")
        debug_log_parts.append(f"Intent: {intent}")
        debug_log_parts.append(f"Format: {format}")
        debug_log_parts.append(f"Camera Pack: {camera_pack}")
        debug_log_parts.append(f"Shot Pack: {shot_pack}")
        debug_log_parts.append(f"Lighting Pack: {lighting_pack}")
        debug_log_parts.append(f"Environment Pack: {environment_pack}")
        debug_log_parts.append(f"Style Pack: {style_pack}")
        debug_log_parts.append(f"Branding Pack: {branding_pack}")
        debug_log_parts.append(f"Lens Pack: {lens_pack}")
        debug_log_parts.append(f"Film Texture Pack: {film_texture_pack}")
        debug_log_parts.append(f"Color Science Pack: {color_science_pack}")
        debug_log_parts.append(f"Time Weather Pack: {time_weather_pack}")
        debug_log_parts.append(f"Pose Discipline Pack: {pose_discipline_pack}")
        debug_log_parts.append(f"Studio Override: {studio_override}")
        debug_log_parts.append(f"Use Logo: {seed_state['use_logo']}")
        debug_log_parts.append(f"Use Pose Ref: {seed_state['use_pose_ref']}")
        debug_log_parts.append(f"Use Photo Style Ref: {seed_state['use_photo_style_ref']} ({style_ref_count})")
        debug_log_parts.append(f"Use Location Ref: {seed_state['use_location_ref']} ({location_ref_count})")
        debug_log_parts.append(f"Gemini Mode: {gemini_mode}")
        debug_log_parts.append("")
        
        resolved_json = None
        nano_banana_prompt = None
        resolver_used = "none"
        gemini_raw_response = ""
        
        if use_gemini:
            debug_log_parts.append("=== GEMINI VISION RESOLVER ===")
            debug_log_parts.append(f"Mode: {gemini_mode}")
            debug_log_parts.append(f"Model: {gemini_model}")
            
            api_key = gemini_api_key.strip() if gemini_api_key else None
            
            if api_key:
                debug_log_parts.append("API Key: PROVIDED")
            else:
                import os
                env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if env_key:
                    debug_log_parts.append("API Key: FROM ENVIRONMENT")
                    api_key = env_key
                else:
                    debug_log_parts.append("API Key: NOT FOUND - Gemini will fail")
            
            gemini_resolver = GeminiResolver(self.config)
            
            resolved_json, nano_banana_prompt, gemini_log = gemini_resolver.resolve(
                seed_state=seed_state,
                images=images,
                api_key=api_key,
                model_id=gemini_model,
                temperature=gemini_temperature,
                max_tokens=gemini_max_tokens,
                gemini_mode=gemini_mode
            )
            
            debug_log_parts.append(gemini_log)
            gemini_raw_response = gemini_resolver.get_raw_response()
            
            if resolved_json:
                resolver_used = f"gemini_{gemini_mode}"
                debug_log_parts.append(f"[SUCCESS] Using Gemini resolver output ({gemini_mode})")
                
                if nano_banana_prompt:
                    debug_log_parts.append("[SUCCESS] Gemini provided NANO_BANANA_PROMPT")
                else:
                    debug_log_parts.append("[INFO] Prompt will be compiled locally")
            else:
                debug_log_parts.append("[FALLBACK] Gemini failed, falling back to local resolver")
        
        if resolved_json is None:
            debug_log_parts.append("")
            debug_log_parts.append("=== LOCAL RESOLVER (FALLBACK) ===")
            local_resolver = LocalResolver(self.config)
            resolved_json = local_resolver.resolve(seed_state)
            resolver_used = "local_fallback"
            debug_log_parts.append(local_resolver.get_debug_log())
        
        if nano_banana_prompt is None:
            debug_log_parts.append("")
            debug_log_parts.append("=== LOCAL PROMPT COMPILATION ===")
            compiler = PromptCompiler(self.config)
            nano_banana_prompt = compiler.compile(resolved_json)
            debug_log_parts.append(compiler.get_debug_log())
        
        debug_log_parts.append("")
        debug_log_parts.append("=== FINAL OUTPUT ===")
        debug_log_parts.append(f"Resolver used: {resolver_used}")
        debug_log_parts.append(f"Prompt source: {'gemini' if 'gemini' in resolver_used and nano_banana_prompt else 'local_compiler'}")
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
        use_pose_ref: bool,
        pose_ref_img,
        use_photo_style_ref: bool,
        photo_style_refs: List,
        use_location_ref: bool,
        location_refs: List
    ) -> Tuple[List[str], int]:
        
        messages = []
        
        if talent_img is None:
            messages.append("[ERROR] TALENT_IMG is required but not provided")
        else:
            messages.append("[OK] TALENT_IMG provided - identity lock active")
        
        garment_count = sum(1 for g in garment_imgs if g is not None)
        if garment_count == 0:
            messages.append("[ERROR] At least one GARMENT_IMG is required")
        else:
            messages.append(f"[OK] {garment_count} GARMENT_IMG(s) provided - fidelity lock active")
        
        if use_pose_ref:
            if pose_ref_img is not None:
                messages.append("[OK] POSE_REF enabled and provided")
            else:
                messages.append("[WARN] POSE_REF enabled but image not provided - using default pose")
        else:
            messages.append("[INFO] POSE_REF disabled - using neutral fit-preserving pose")
        
        if use_photo_style_ref:
            style_count = sum(1 for s in photo_style_refs if s is not None)
            if style_count > 0:
                messages.append(f"[OK] PHOTO_STYLE_REF enabled with {style_count} reference(s)")
            else:
                messages.append("[WARN] PHOTO_STYLE_REF enabled but no images - using premium editorial default")
        else:
            messages.append("[INFO] PHOTO_STYLE_REF disabled - using premium editorial realism")
        
        if use_location_ref:
            loc_count = sum(1 for l in location_refs if l is not None)
            if loc_count > 0:
                messages.append(f"[OK] LOCATION_REF enabled with {loc_count} reference(s)")
            else:
                messages.append("[WARN] LOCATION_REF enabled but no images provided")
        else:
            messages.append("[INFO] LOCATION_REF disabled")
        
        return messages, garment_count


NODE_CLASS_MAPPINGS = {
    "MorpheusFashionPhotoSystem": MorpheusFashionPhotoSystem
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MorpheusFashionPhotoSystem": "Morpheus Fashion Photo System"
}
