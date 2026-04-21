"""
Configuration loader for Morpheus Fashion Photo System
Loads all JSON config files from the config directory
"""

import json
import os
from typing import Dict, Any, List, Optional

class ConfigLoader:
    def __init__(self, config_dir: Optional[str] = None, mode: str = "standard"):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), "config")
        self.config_dir = config_dir
        self.mode = mode
        base_templates = os.path.join(os.path.dirname(__file__), "templates")
        self.templates_dir = os.path.join(base_templates, mode)
        self.templates_dir_standard = os.path.join(base_templates, "standard")
        self.templates_dir_light = os.path.join(base_templates, "light")
        self._cache: Dict[str, Any] = {}
    
    def _load_json(self, filename: str, directory: Optional[str] = None) -> Dict[str, Any]:
        if directory is None:
            directory = self.config_dir
        
        cache_key = f"{directory}/{filename}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[cache_key] = data
                return data
        except FileNotFoundError:
            raise ValueError(f"Config file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
    
    def get_camera_packs(self) -> Dict[str, Any]:
        return self._load_json("camera_packs.json")
    
    def get_shot_packs(self) -> Dict[str, Any]:
        return self._load_json("shot_packs.json")
    
    def get_lighting_packs(self) -> Dict[str, Any]:
        return self._load_json("lighting_packs.json")
    
    def get_environment_packs(self) -> Dict[str, Any]:
        return self._load_json("environment_packs.json")
    
    def get_style_packs(self) -> Dict[str, Any]:
        return self._load_json("style_packs.json")
    
    def get_branding_packs(self) -> Dict[str, Any]:
        return self._load_json("branding_packs.json")
    
    def get_gemini_presets(self) -> Dict[str, Any]:
        return self._load_json("gemini_presets.json")
    
    def get_lens_packs(self) -> Dict[str, Any]:
        return self._load_json("lens_packs.json")
    
    def get_film_texture_packs(self) -> Dict[str, Any]:
        return self._load_json("film_texture_packs.json")
    
    def get_color_science_packs(self) -> Dict[str, Any]:
        return self._load_json("color_science_packs.json")
    
    def get_time_weather_packs(self) -> Dict[str, Any]:
        return self._load_json("time_weather_packs.json")
    
    def get_pose_discipline_packs(self) -> Dict[str, Any]:
        return self._load_json("pose_discipline_packs.json")
    
    def get_intents(self) -> Dict[str, Any]:
        return self._load_json("intents.json")
    
    def get_prompt_compiler_template(self) -> Dict[str, Any]:
        return self._load_json("prompt_compiler.json", self.templates_dir_standard)
    
    def get_gemini_prompts(self) -> Dict[str, Any]:
        return self._load_json("gemini_prompts.json", self.templates_dir_standard)
    
    def get_gemini_prompts_light(self) -> Dict[str, Any]:
        return self._load_json("gemini_prompts_light.json", self.templates_dir_light)
    
    def get_pack_ids(self, pack_type: str) -> List[str]:
        pack_methods = {
            "camera": self.get_camera_packs,
            "shot": self.get_shot_packs,
            "lighting": self.get_lighting_packs,
            "environment": self.get_environment_packs,
            "style": self.get_style_packs,
            "branding": self.get_branding_packs,
            "lens": self.get_lens_packs,
            "film_texture": self.get_film_texture_packs,
            "color_science": self.get_color_science_packs,
            "time_weather": self.get_time_weather_packs,
            "pose_discipline": self.get_pose_discipline_packs,
        }
        
        if pack_type not in pack_methods:
            raise ValueError(f"Unknown pack type: {pack_type}")
        
        data = pack_methods[pack_type]()
        packs = data.get("packs", {})
        
        if isinstance(packs, dict):
            first_value = next(iter(packs.values()), None)
            if isinstance(first_value, list):
                return [item.get("id") for item in first_value if isinstance(item, dict) and "id" in item]
            return list(packs.keys())
        elif isinstance(packs, list):
            return [item.get("id") for item in packs if isinstance(item, dict) and "id" in item]
        return []
    
    def get_pack(self, pack_type: str, pack_id: str) -> Dict[str, Any]:
        pack_methods = {
            "camera": self.get_camera_packs,
            "shot": self.get_shot_packs,
            "lighting": self.get_lighting_packs,
            "environment": self.get_environment_packs,
            "style": self.get_style_packs,
            "branding": self.get_branding_packs,
            "lens": self.get_lens_packs,
            "film_texture": self.get_film_texture_packs,
            "color_science": self.get_color_science_packs,
            "time_weather": self.get_time_weather_packs,
            "pose_discipline": self.get_pose_discipline_packs,
        }
        
        if pack_type not in pack_methods:
            raise ValueError(f"Unknown pack type: {pack_type}")
        
        data = pack_methods[pack_type]()
        packs = data.get("packs", {})
        
        if isinstance(packs, dict):
            first_value = next(iter(packs.values()), None)
            if isinstance(first_value, list):
                pack_list = first_value
                for item in pack_list:
                    if isinstance(item, dict) and item.get("id") == pack_id:
                        return item
                default_id = data.get("default")
                if default_id:
                    for item in pack_list:
                        if isinstance(item, dict) and item.get("id") == default_id:
                            return item
                raise ValueError(f"Pack ID '{pack_id}' not found in {pack_type} packs")
            
            if pack_id not in packs:
                default_id = data.get("default")
                if default_id and default_id in packs:
                    return packs[default_id]
                raise ValueError(f"Pack ID '{pack_id}' not found in {pack_type} packs")
            return packs[pack_id]
        elif isinstance(packs, list):
            for item in packs:
                if isinstance(item, dict) and item.get("id") == pack_id:
                    return item
            default_id = data.get("default")
            if default_id:
                for item in packs:
                    if isinstance(item, dict) and item.get("id") == default_id:
                        return item
            raise ValueError(f"Pack ID '{pack_id}' not found in {pack_type} packs")
        
        raise ValueError(f"Invalid packs structure in {pack_type}")
    
    def get_intent(self, intent_id: str) -> Dict[str, Any]:
        data = self.get_intents()
        intents = data.get("intents", {})
        
        if intent_id not in intents:
            default_id = data.get("default", "awareness")
            if default_id in intents:
                return intents[default_id]
            raise ValueError(f"Intent '{intent_id}' not found")
        
        return intents[intent_id]
    
    def get_gemini_model_ids(self) -> List[str]:
        data = self.get_gemini_presets()
        return list(data.get("models", {}).keys())
    
    def get_gemini_model(self, model_id: str) -> Dict[str, Any]:
        data = self.get_gemini_presets()
        models = data.get("models", {})
        
        if model_id not in models:
            default_id = data.get("default_model", "gemini-1.5-flash")
            if default_id in models:
                return models[default_id]
            raise ValueError(f"Gemini model '{model_id}' not found")
        
        return models[model_id]
    
    def validate_pack_selections(self, selections: Dict[str, str]) -> List[str]:
        errors = []
        
        pack_types = ["camera", "shot", "lighting", "environment", "style", "branding", 
                      "lens", "film_texture", "color_science", "time_weather", "pose_discipline"]
        
        for pack_type in pack_types:
            pack_id = selections.get(f"{pack_type}_pack")
            if pack_id and pack_id.lower() != "auto":
                available = self.get_pack_ids(pack_type)
                if pack_id not in available:
                    errors.append(f"Invalid {pack_type} pack: '{pack_id}'. Available: {available}")
        
        return errors
    
    def clear_cache(self):
        self._cache.clear()
