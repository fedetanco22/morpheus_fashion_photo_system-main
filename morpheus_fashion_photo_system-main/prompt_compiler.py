"""
Prompt Compiler for Morpheus Fashion Photo System
Converts RESOLVED_JSON into a single Nano Banana prompt starting with "Make"
"""

from typing import Dict, Any, List

class PromptCompiler:
    def __init__(self, config_loader):
        self.config = config_loader
        self.debug_entries: List[str] = []
    
    def _log(self, message: str):
        self.debug_entries.append(message)
    
    def compile(self, resolved_json: Dict[str, Any]) -> str:
        self.debug_entries = []
        self._log("=== PROMPT COMPILER START ===")
        
        template = self.config.get_prompt_compiler_template()
        fallbacks = template.get("fallback_values", {})
        
        subject_part = self._compile_subject(resolved_json.get("subject", {}))
        wardrobe_part = self._compile_wardrobe(resolved_json.get("wardrobe", {}))
        pose_part = self._compile_pose(resolved_json.get("pose", {}), fallbacks)
        photography_part = self._compile_photography(resolved_json.get("photography", {}))
        lens_part = self._compile_lens(resolved_json.get("lens", {}))
        lighting_part = self._compile_lighting(resolved_json.get("lighting", {}))
        environment_part = self._compile_environment(resolved_json.get("environment", {}), fallbacks)
        time_weather_part = self._compile_time_weather(resolved_json.get("time_weather", {}))
        style_part = self._compile_style(resolved_json.get("style", {}), fallbacks)
        color_science_part = self._compile_color_science(resolved_json.get("color_science", {}))
        film_texture_part = self._compile_film_texture(resolved_json.get("film_texture", {}))
        branding_part = self._compile_branding(resolved_json.get("branding", {}))
        
        prompt_parts = [
            f"Make {subject_part}",
            f"wearing {wardrobe_part}",
            pose_part,
            photography_part,
            lens_part,
            lighting_part,
            environment_part,
            time_weather_part,
            style_part,
            color_science_part,
            film_texture_part
        ]
        
        prompt_parts = [p for p in prompt_parts if p]
        
        prompt = ", ".join(prompt_parts)
        
        if branding_part:
            prompt += f", {branding_part}"
        
        if not prompt.endswith("."):
            prompt += "."
        
        max_length = template.get("rules", {}).get("max_length", 500)
        if len(prompt) > max_length:
            self._log(f"[WARN] Prompt exceeds max length ({len(prompt)} > {max_length}), truncating")
            prompt = prompt[:max_length-1] + "."
        
        self._log(f"[OUTPUT] Final prompt length: {len(prompt)} chars")
        self._log("=== PROMPT COMPILER COMPLETE ===")
        
        return prompt
    
    def _compile_subject(self, subject: Dict[str, Any]) -> str:
        description = subject.get("description", "a fashion model")
        gender = subject.get("gender", "")
        
        if gender and gender != "as provided in reference":
            return f"a {gender} model with the exact features and proportions from the provided reference"
        
        return f"{description} with strictly preserved identity from the reference"
    
    def _compile_wardrobe(self, wardrobe: Dict[str, Any]) -> str:
        items = wardrobe.get("items", [])
        styling = wardrobe.get("styling_notes", "")
        
        if not items:
            return "the provided garments exactly as shown"
        
        num_items = len(items)
        
        if num_items == 1:
            return "the single provided garment exactly as shown with accurate fit"
        elif num_items <= 3:
            return f"all {num_items} provided garments together exactly as shown with natural styling"
        else:
            return f"all {num_items} provided garments styled together naturally while preserving each piece exactly as shown"
    
    def _compile_pose(self, pose: Dict[str, Any], fallbacks: Dict[str, str]) -> str:
        if pose.get("reference_used", False):
            return "posed following the provided reference while maintaining full garment visibility"
        
        pose_type = pose.get("type", "")
        description = pose.get("description", fallbacks.get("pose", "in a natural confident stance"))
        
        return description
    
    def _compile_photography(self, photography: Dict[str, Any]) -> str:
        camera = photography.get("camera", "static")
        shot = photography.get("shot", "medium")
        framing = photography.get("framing", "")
        
        camera_pack_id = self._reverse_lookup_camera(camera)
        shot_pack_id = self._reverse_lookup_shot(shot)
        
        try:
            camera_pack = self.config.get_pack("camera", camera_pack_id)
            shot_pack = self.config.get_pack("shot", shot_pack_id)
            
            camera_fragment = camera_pack.get("prompt_fragment", "")
            shot_fragment = shot_pack.get("prompt_fragment", "")
            
            parts = []
            if shot_fragment:
                parts.append(shot_fragment)
            if camera_fragment:
                parts.append(camera_fragment)
            
            if parts:
                return " and ".join(parts)
        except:
            pass
        
        return f"{shot} shot with {camera} camera approach"
    
    def _compile_lighting(self, lighting: Dict[str, Any]) -> str:
        description = lighting.get("description", "")
        if description:
            return description
        
        light_type = lighting.get("type", "studio")
        mood = lighting.get("mood", "clean")
        
        return f"with {mood} {light_type} lighting"
    
    def _compile_environment(self, environment: Dict[str, Any], fallbacks: Dict[str, str]) -> str:
        description = environment.get("description", fallbacks.get("environment", "in a clean neutral setting"))
        
        if environment.get("studio_override_applied", False):
            return "set against a clean minimal studio backdrop"
        
        return description
    
    def _compile_style(self, style: Dict[str, Any], fallbacks: Dict[str, str]) -> str:
        aesthetic = style.get("aesthetic", "")
        mood = style.get("mood", "")
        
        if not aesthetic and not mood:
            return fallbacks.get("style", "in premium editorial realism")
        
        if aesthetic and mood:
            return f"styled with {aesthetic} aesthetic and {mood} mood"
        elif aesthetic:
            return f"styled with {aesthetic} aesthetic"
        else:
            return f"conveying a {mood} mood"
    
    def _compile_branding(self, branding: Dict[str, Any]) -> str:
        if not branding.get("logo_used", False):
            return ""
        
        placement = branding.get("placement", "lower corner")
        treatment = branding.get("treatment", "discreet")
        
        if placement == "none":
            return ""
        
        return f"with {treatment} brand logo in {placement}"
    
    def _reverse_lookup_camera(self, behavior: str) -> str:
        try:
            camera_packs = self.config.get_camera_packs().get("packs", {})
            for pack_id, pack in camera_packs.items():
                if pack.get("behavior") == behavior:
                    return pack_id
        except:
            pass
        return "editorial_static"
    
    def _reverse_lookup_shot(self, framing: str) -> str:
        try:
            shot_packs = self.config.get_shot_packs().get("packs", {})
            for pack_id, pack in shot_packs.items():
                if pack.get("framing") == framing:
                    return pack_id
        except:
            pass
        return "medium_three_quarter"
    
    def _compile_lens(self, lens: Dict[str, Any]) -> str:
        description = lens.get("description", "")
        if description:
            return description
        return ""
    
    def _compile_film_texture(self, film_texture: Dict[str, Any]) -> str:
        description = film_texture.get("description", "")
        if description:
            return description
        return ""
    
    def _compile_color_science(self, color_science: Dict[str, Any]) -> str:
        description = color_science.get("description", "")
        if description:
            return description
        return ""
    
    def _compile_time_weather(self, time_weather: Dict[str, Any]) -> str:
        description = time_weather.get("description", "")
        if time_weather.get("time_of_day") == "studio":
            return ""
        if description:
            return description
        return ""
    
    def get_debug_log(self) -> str:
        return "\n".join(self.debug_entries)
