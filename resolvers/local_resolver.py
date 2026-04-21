"""
Local Resolver for Morpheus Fashion Photo System
Applies rules and presets to produce RESOLVED_JSON without LLM
"""

import json
from typing import Dict, Any, List, Optional

class LocalResolver:
    PRIORITY_HIERARCHY = [
        "talent_identity",
        "garments_fidelity", 
        "fit_accuracy",
        "pose",
        "photo_style",
        "location",
        "branding"
    ]
    
    def __init__(self, config_loader):
        self.config = config_loader
        self.debug_entries: List[str] = []
    
    def _log(self, message: str):
        self.debug_entries.append(message)
    
    def resolve(self, seed_state: Dict[str, Any]) -> Dict[str, Any]:
        self.debug_entries = []
        self._log("=== LOCAL RESOLVER START ===")
        
        packs_applied = self._resolve_packs_applied(seed_state)
        rendering = self._resolve_rendering(seed_state, packs_applied)
        
        resolved = {
            "subject": self._resolve_subject(seed_state),
            "wardrobe": self._resolve_wardrobe(seed_state),
            "pose": self._resolve_pose(seed_state),
            "photography": self._resolve_photography(seed_state),
            "lighting": self._resolve_lighting(seed_state),
            "environment": self._resolve_environment(seed_state),
            "style": self._resolve_style(seed_state),
            "branding": self._resolve_branding(seed_state),
            "lens": self._resolve_lens(seed_state),
            "film_texture": self._resolve_film_texture(seed_state),
            "color_science": self._resolve_color_science(seed_state),
            "time_weather": self._resolve_time_weather(seed_state),
            "packs_applied": packs_applied,
            "rendering": rendering,
            "intent_applied": seed_state.get("intent", "awareness"),
            "format": seed_state.get("format", "9:16")
        }
        
        self._log("=== LOCAL RESOLVER COMPLETE ===")
        
        return resolved
    
    def _resolve_packs_applied(self, state: Dict[str, Any]) -> Dict[str, Any]:
        studio_override = state.get("studio_override", "AUTO")
        use_pose_ref = state.get("use_pose_ref", False)
        intent = state.get("intent", "awareness")
        
        selected = {
            "lens_pack": state.get("lens_pack", "normal_perspective"),
            "film_texture_pack": state.get("film_texture_pack", "clean_digital"),
            "color_science_pack": state.get("color_science_pack", "neutral_premium_clean"),
            "time_weather_pack": state.get("time_weather_pack", "studio_controlled"),
            "pose_discipline_pack": state.get("pose_discipline_pack", "fit_preserving_neutral_stance")
        }
        
        effective = dict(selected)
        
        if studio_override == "ON":
            effective["time_weather_pack"] = "studio_controlled"
            self._log(f"[PACKS] time_weather overridden: studio_override=ON → studio_controlled")
        
        if use_pose_ref:
            effective["pose_discipline_pack"] = "IGNORED (pose_ref provided)"
            self._log(f"[PACKS] pose_discipline ignored: pose_ref provided")
        
        if intent in ["consideration", "fit"]:
            self._log(f"[PACKS] Intent {intent} may subordinate style rendering to fit readability")
        
        lens_pack = self.config.get_pack("lens", effective["lens_pack"] if "IGNORED" not in str(effective.get("lens_pack", "")) else selected["lens_pack"])
        film_pack = self.config.get_pack("film_texture", effective["film_texture_pack"] if "IGNORED" not in str(effective.get("film_texture_pack", "")) else selected["film_texture_pack"])
        color_pack = self.config.get_pack("color_science", effective["color_science_pack"] if "IGNORED" not in str(effective.get("color_science_pack", "")) else selected["color_science_pack"])
        time_weather_pack = self.config.get_pack("time_weather", effective["time_weather_pack"] if "IGNORED" not in str(effective.get("time_weather_pack", "")) else "studio_controlled")
        pose_pack = self.config.get_pack("pose_discipline", selected["pose_discipline_pack"]) if not use_pose_ref else {}
        
        fragments = {
            "lens": lens_pack.get("prompt_fragment", ""),
            "film_texture": film_pack.get("prompt_fragment", ""),
            "color_science": color_pack.get("prompt_fragment", ""),
            "time_weather": time_weather_pack.get("prompt_fragment", ""),
            "pose_discipline": pose_pack.get("prompt_fragment", "") if pose_pack else "COPIED FROM REFERENCE"
        }
        
        self._log("=== PACKS APPLIED ===")
        self._log(f"Selected: {json.dumps(selected)}")
        self._log(f"Effective: {json.dumps(effective)}")
        self._log(f"Fragments: lens='{fragments['lens'][:50]}...'" if len(fragments['lens']) > 50 else f"Fragments: lens='{fragments['lens']}'")
        
        return {
            "selected": selected,
            "effective": effective,
            "fragments": fragments
        }
    
    def _resolve_rendering(self, state: Dict[str, Any], packs_applied: Dict[str, Any]) -> Dict[str, Any]:
        fragments = packs_applied.get("fragments", {})
        
        return {
            "lens": fragments.get("lens", ""),
            "film_texture": fragments.get("film_texture", ""),
            "color_science": fragments.get("color_science", ""),
            "time_weather": fragments.get("time_weather", ""),
            "pose_discipline": fragments.get("pose_discipline", "")
        }
    
    def _resolve_subject(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[SUBJECT] Applying STRICT identity lock")
        
        return {
            "description": "the provided talent model",
            "identity_lock": True,
            "gender": "as provided in reference",
            "traits": ["exact features preserved", "proportions locked", "ethnicity maintained"]
        }
    
    def _resolve_wardrobe(self, state: Dict[str, Any]) -> Dict[str, Any]:
        garment_count = state.get("garment_count", 1)
        intent = state.get("intent", "awareness")
        
        self._log(f"[WARDROBE] Processing {garment_count} garment(s)")
        self._log("[WARDROBE] Applying STRICT fidelity - no redesign, no invention")
        
        intent_data = self.config.get_intent(intent)
        fit_strictness = intent_data.get("fit_strictness", "high")
        
        if intent == "consideration":
            fit_priority = "very_high"
            self._log("[WARDROBE] Consideration intent: fit accuracy is CRITICAL")
        else:
            fit_priority = "high" if fit_strictness in ["high", "very_high"] else "medium"
        
        garment_items = [f"garment_{i+1} as provided" for i in range(garment_count)]
        
        return {
            "items": garment_items,
            "fit_priority": fit_priority,
            "styling_notes": f"All {garment_count} provided garments must appear exactly as shown, styled naturally together"
        }
    
    def _resolve_pose(self, state: Dict[str, Any]) -> Dict[str, Any]:
        use_pose_ref = state.get("use_pose_ref", False)
        shot_pack_id = state.get("shot_pack", "medium_three_quarter")
        pose_discipline_id = state.get("pose_discipline_pack", "fit_preserving_neutral_stance")
        
        if use_pose_ref:
            self._log("[POSE] Using provided pose reference - pose will be copied, not interpreted")
            return {
                "type": "reference-based",
                "description": "following the provided pose reference exactly while maintaining garment visibility",
                "reference_used": True,
                "discipline_applied": False
            }
        else:
            pose_discipline = self.config.get_pack("pose_discipline", pose_discipline_id)
            self._log(f"[POSE] No reference - using pose discipline: {pose_discipline_id}")
            
            return {
                "type": pose_discipline.get("name", "fit-preserving stance"),
                "description": pose_discipline.get("prompt_fragment", "fit-preserving neutral stance"),
                "reference_used": False,
                "discipline_applied": True,
                "fit_priority": pose_discipline.get("fit_priority", "high")
            }
    
    def _resolve_photography(self, state: Dict[str, Any]) -> Dict[str, Any]:
        camera_pack_id = state.get("camera_pack", "editorial_static")
        shot_pack_id = state.get("shot_pack", "medium_three_quarter")
        
        camera_pack = self.config.get_pack("camera", camera_pack_id)
        shot_pack = self.config.get_pack("shot", shot_pack_id)
        
        self._log(f"[PHOTOGRAPHY] Camera: {camera_pack_id}, Shot: {shot_pack_id}")
        
        return {
            "camera": camera_pack.get("behavior", "static"),
            "shot": shot_pack.get("framing", "medium"),
            "framing": f"{shot_pack.get('coverage', 'medium')} coverage, {camera_pack.get('depth_of_field', 'controlled')} depth of field"
        }
    
    def _resolve_lighting(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lighting_pack_id = state.get("lighting_pack", "studio_high_key")
        studio_override = state.get("studio_override", "AUTO")
        
        if studio_override == "ON":
            lighting_pack_id = "studio_high_key"
            self._log("[LIGHTING] Studio override ON - forcing studio lighting")
        
        lighting_pack = self.config.get_pack("lighting", lighting_pack_id)
        
        self._log(f"[LIGHTING] Applied: {lighting_pack_id}")
        
        return {
            "type": lighting_pack.get("type", "artificial"),
            "mood": lighting_pack.get("mood", "clean bright"),
            "description": lighting_pack.get("prompt_fragment", "professional lighting setup")
        }
    
    def _resolve_environment(self, state: Dict[str, Any]) -> Dict[str, Any]:
        env_pack_id = state.get("environment_pack", "minimal_studio_cyclorama")
        studio_override = state.get("studio_override", "AUTO")
        use_location_ref = state.get("use_location_ref", False)
        
        studio_override_applied = False
        
        if studio_override == "ON":
            env_pack_id = "minimal_studio_cyclorama"
            studio_override_applied = True
            self._log("[ENVIRONMENT] Studio override ON - ignoring location references, forcing studio")
        elif studio_override == "AUTO" and not use_location_ref:
            env_pack_id = "minimal_studio_cyclorama"
            self._log("[ENVIRONMENT] AUTO mode, no location ref - defaulting to studio")
        elif use_location_ref:
            self._log(f"[ENVIRONMENT] Using location reference with pack: {env_pack_id}")
        
        env_pack = self.config.get_pack("environment", env_pack_id)
        
        return {
            "type": env_pack.get("type", "studio"),
            "description": env_pack.get("prompt_fragment", "in a clean neutral setting"),
            "studio_override_applied": studio_override_applied
        }
    
    def _resolve_style(self, state: Dict[str, Any]) -> Dict[str, Any]:
        style_pack_id = state.get("style_pack", "premium_restraint")
        use_style_ref = state.get("use_photo_style_ref", False)
        intent = state.get("intent", "awareness")
        
        style_subordinated = False
        if intent in ["consideration", "fit"]:
            style_subordinated = True
            self._log("[STYLE] Intent is fit/consideration - style refs subordinate to readability")
        
        if not use_style_ref:
            style_pack_id = "premium_restraint"
            self._log("[STYLE] No style reference - defaulting to premium editorial realism")
        else:
            self._log(f"[STYLE] Using style reference with pack: {style_pack_id}")
        
        style_pack = self.config.get_pack("style", style_pack_id)
        
        return {
            "aesthetic": style_pack.get("aesthetic", "minimalist luxury"),
            "color_grading": style_pack.get("color_grading", "neutral subtle"),
            "mood": style_pack.get("mood", "refined understated"),
            "subordinated_to_fit": style_subordinated
        }
    
    def _resolve_branding(self, state: Dict[str, Any]) -> Dict[str, Any]:
        use_logo = state.get("use_logo", True)
        branding_pack_id = state.get("branding_pack", "logo_discreet_lower")
        
        if not use_logo:
            self._log("[BRANDING] Logo disabled")
            return {
                "logo_used": False,
                "placement": "none",
                "treatment": "none"
            }
        
        branding_pack = self.config.get_pack("branding", branding_pack_id)
        
        self._log(f"[BRANDING] Logo enabled with pack: {branding_pack_id}")
        
        return {
            "logo_used": True,
            "placement": branding_pack.get("placement", "lower right corner safe area"),
            "treatment": branding_pack.get("size", "small discreet")
        }
    
    def _resolve_lens(self, state: Dict[str, Any]) -> Dict[str, Any]:
        lens_pack_id = state.get("lens_pack", "normal_perspective")
        lens_pack = self.config.get_pack("lens", lens_pack_id)
        
        self._log(f"[LENS] Applied: {lens_pack_id}")
        
        return {
            "perspective": lens_pack.get("name", "Normal Perspective"),
            "description": lens_pack.get("prompt_fragment", "natural perspective, true-to-life proportions")
        }
    
    def _resolve_film_texture(self, state: Dict[str, Any]) -> Dict[str, Any]:
        film_pack_id = state.get("film_texture_pack", "clean_digital")
        film_pack = self.config.get_pack("film_texture", film_pack_id)
        
        self._log(f"[FILM TEXTURE] Applied: {film_pack_id}")
        
        return {
            "texture_type": film_pack.get("name", "Clean Digital"),
            "description": film_pack.get("prompt_fragment", "clean digital finish, crisp edges, no grain")
        }
    
    def _resolve_color_science(self, state: Dict[str, Any]) -> Dict[str, Any]:
        color_pack_id = state.get("color_science_pack", "neutral_premium_clean")
        color_pack = self.config.get_pack("color_science", color_pack_id)
        
        self._log(f"[COLOR SCIENCE] Applied: {color_pack_id}")
        
        return {
            "palette": color_pack.get("name", "Neutral Premium Clean"),
            "description": color_pack.get("prompt_fragment", "premium neutral color science, true-to-life garment colors")
        }
    
    def _resolve_time_weather(self, state: Dict[str, Any]) -> Dict[str, Any]:
        time_weather_id = state.get("time_weather_pack", "studio_controlled")
        studio_override = state.get("studio_override", "AUTO")
        
        if studio_override == "ON":
            time_weather_id = "studio_controlled"
            self._log("[TIME WEATHER] Studio override ON - using studio controlled")
        
        time_weather_pack = self.config.get_pack("time_weather", time_weather_id)
        
        self._log(f"[TIME WEATHER] Applied: {time_weather_id}")
        
        return {
            "conditions": time_weather_pack.get("name", "Studio Controlled"),
            "description": time_weather_pack.get("prompt_fragment", "controlled studio lighting"),
            "time_of_day": time_weather_pack.get("time_of_day", "studio"),
            "weather": time_weather_pack.get("weather", "none")
        }
    
    def get_debug_log(self) -> str:
        return "\n".join(self.debug_entries)
