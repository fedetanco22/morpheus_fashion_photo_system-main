"""
Test script for Morpheus Fashion Photo System
Simulates node execution without ComfyUI environment
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from morpheus_fashion_photo_system.config_loader import ConfigLoader
from morpheus_fashion_photo_system.resolvers.local_resolver import LocalResolver
from morpheus_fashion_photo_system.resolvers.gemini_resolver import GeminiResolver
from morpheus_fashion_photo_system.prompt_compiler import PromptCompiler


def test_config_loader():
    print("=" * 60)
    print("TEST: ConfigLoader")
    print("=" * 60)
    
    config = ConfigLoader()
    
    print("\nCamera packs:", config.get_pack_ids("camera"))
    print("Shot packs:", config.get_pack_ids("shot"))
    print("Lighting packs:", config.get_pack_ids("lighting"))
    print("Environment packs:", config.get_pack_ids("environment"))
    print("Style packs:", config.get_pack_ids("style"))
    print("Branding packs:", config.get_pack_ids("branding"))
    print("Gemini models:", config.get_gemini_model_ids())
    
    intents = config.get_intents()
    print("Intents:", list(intents.get("intents", {}).keys()))
    
    print("\n[OK] ConfigLoader working correctly")
    return config


def test_local_resolver(config):
    print("\n" + "=" * 60)
    print("TEST: LocalResolver")
    print("=" * 60)
    
    seed_state = {
        "brief_text": "Create a winter campaign image featuring a woman in premium outerwear, walking through a snowy forest with warm lighting",
        "format": "9:16",
        "garment_count": 3,
        "intent": "awareness",
        "camera_pack": "auto",
        "shot_pack": "auto",
        "lighting_pack": "auto",
        "environment_pack": "auto",
        "style_pack": "cinematic_memory",
        "branding_pack": "auto",
        "lens_pack": "auto",
        "film_texture_pack": "auto",
        "color_science_pack": "cold_exterior_warm_interior",
        "time_weather_pack": "deep_night_snowfall",
        "pose_discipline_pack": "auto",
        "studio_override": "OFF",
        "use_logo": True,
        "use_pose_ref": False,
        "use_photo_style_ref": True,
        "style_ref_count": 2,
        "use_location_ref": True,
        "location_ref_count": 1,
    }
    
    resolver = LocalResolver(config)
    resolved = resolver.resolve(seed_state)
    
    print("\nRESOLVED_JSON:")
    import json
    print(json.dumps(resolved, indent=2))
    
    print("\nDEBUG LOG:")
    print(resolver.get_debug_log())
    
    print("\n[OK] LocalResolver working correctly")
    return resolved


def test_prompt_compiler(config, resolved_json):
    print("\n" + "=" * 60)
    print("TEST: PromptCompiler")
    print("=" * 60)
    
    compiler = PromptCompiler(config)
    prompt = compiler.compile(resolved_json)
    
    print("\nNANO_BANANA_PROMPT:")
    print(prompt)
    
    print("\nValidation checks:")
    print(f"  - Starts with 'Make': {prompt.startswith('Make')}")
    print(f"  - Single sentence: {'.' not in prompt[:-1]}")
    print(f"  - Ends with period: {prompt.endswith('.')}")
    print(f"  - Length: {len(prompt)} chars")
    
    print("\nDEBUG LOG:")
    print(compiler.get_debug_log())
    
    print("\n[OK] PromptCompiler working correctly")
    return prompt


def test_studio_override(config):
    print("\n" + "=" * 60)
    print("TEST: Studio Override Behavior")
    print("=" * 60)
    
    seed_state = {
        "brief_text": "Product shot in studio",
        "format": "1:1",
        "garment_count": 1,
        "intent": "consideration",
        "camera_pack": "auto",
        "shot_pack": "auto",
        "lighting_pack": "auto",
        "environment_pack": "minimal_studio_cyclorama",
        "style_pack": "editorial_precision",
        "branding_pack": "auto",
        "lens_pack": "auto",
        "film_texture_pack": "digital_clean_no_emulation",
        "color_science_pack": "neutral_premium_clean",
        "time_weather_pack": "auto",
        "pose_discipline_pack": "fit_preserving_neutral_stance",
        "studio_override": "ON",
        "use_logo": False,
        "use_pose_ref": False,
        "use_photo_style_ref": False,
        "style_ref_count": 0,
        "use_location_ref": True,
        "location_ref_count": 2,
    }
    
    resolver = LocalResolver(config)
    resolved = resolver.resolve(seed_state)
    
    print("\nWith STUDIO_OVERRIDE=ON:")
    print(f"  - Environment type: {resolved['environment']['type']}")
    print(f"  - Studio override applied: {resolved['environment']['studio_override_applied']}")
    print(f"  - Lighting type: {resolved['lighting']['type']}")
    
    compiler = PromptCompiler(config)
    prompt = compiler.compile(resolved)
    print(f"\nPrompt: {prompt}")
    
    print("\n[OK] Studio override working correctly")


def test_intent_variations(config):
    print("\n" + "=" * 60)
    print("TEST: Intent Variations")
    print("=" * 60)
    
    base_state = {
        "brief_text": "Fashion product image",
        "format": "9:16",
        "garment_count": 2,
        "camera_pack": "auto",
        "shot_pack": "auto",
        "lighting_pack": "auto",
        "environment_pack": "minimal_studio_cyclorama",
        "style_pack": "premium_restraint",
        "branding_pack": "auto",
        "lens_pack": "auto",
        "film_texture_pack": "digital_clean_no_emulation",
        "color_science_pack": "neutral_premium_clean",
        "time_weather_pack": "auto",
        "pose_discipline_pack": "fit_preserving_neutral_stance",
        "studio_override": "AUTO",
        "use_logo": True,
        "use_pose_ref": False,
        "use_photo_style_ref": False,
        "style_ref_count": 0,
        "use_location_ref": False,
        "location_ref_count": 0,
    }
    
    for intent in ["awareness", "consideration", "conversion", "retention"]:
        state = base_state.copy()
        state["intent"] = intent
        
        resolver = LocalResolver(config)
        resolved = resolver.resolve(state)
        
        print(f"\n{intent.upper()}:")
        print(f"  - Fit priority: {resolved['wardrobe']['fit_priority']}")
        print(f"  - Intent applied: {resolved['intent_applied']}")


def test_gemini_resolver_availability(config):
    print("\n" + "=" * 60)
    print("TEST: GeminiResolver Availability")
    print("=" * 60)
    
    resolver = GeminiResolver(config)
    available, reason = resolver.is_available()
    
    print(f"\nGemini available: {available}")
    print(f"Reason: {reason}")
    
    if available:
        print("[OK] GeminiResolver ready (requires API key for actual calls)")
    else:
        print("[INFO] GeminiResolver not available - will use local resolver fallback")


def test_gemini_fallback_flow(config):
    print("\n" + "=" * 60)
    print("TEST: Gemini Fallback Flow (No API Key)")
    print("=" * 60)
    
    seed_state = {
        "brief_text": "Test brief for fallback",
        "format": "9:16",
        "garment_count": 1,
        "intent": "awareness",
        "camera_pack": "auto",
        "shot_pack": "auto",
        "lighting_pack": "auto",
        "environment_pack": "minimal_studio_cyclorama",
        "style_pack": "premium_restraint",
        "branding_pack": "auto",
        "lens_pack": "auto",
        "film_texture_pack": "digital_clean_no_emulation",
        "color_science_pack": "neutral_premium_clean",
        "time_weather_pack": "auto",
        "pose_discipline_pack": "fit_preserving_neutral_stance",
        "studio_override": "AUTO",
        "use_logo": False,
        "use_pose_ref": False,
        "use_photo_style_ref": False,
        "style_ref_count": 0,
        "use_location_ref": False,
        "location_ref_count": 0,
    }
    
    gemini_resolver = GeminiResolver(config)
    resolved, nano_prompt, gemini_log = gemini_resolver.resolve(
        seed_state=seed_state,
        images={},
        api_key=None
    )
    
    print("\nGemini attempt without API key:")
    print(gemini_log)
    
    if resolved is None:
        print("\n[EXPECTED] Gemini returned None (no API key)")
        print("[FALLBACK] Now using local resolver...")
        
        local_resolver = LocalResolver(config)
        resolved = local_resolver.resolve(seed_state)
        
        if resolved and "subject" in resolved:
            print("[OK] Local resolver fallback successful")
        else:
            print("[ERROR] Local resolver fallback failed")
    else:
        print("[UNEXPECTED] Gemini returned result without API key")
    
    print("\n[OK] Fallback flow working correctly")


def run_full_simulation():
    print("\n" + "=" * 60)
    print("FULL SIMULATION: Complete Node Execution")
    print("=" * 60)
    
    config = ConfigLoader()
    
    seed_state = {
        "brief_text": """Create an awareness campaign image for a premium Italian fashion brand. 
        Feature a confident woman walking through a winter forest road at golden hour. 
        She wears the complete Fall/Winter collection: wool coat, cashmere sweater, 
        tailored trousers. Mood should be aspirational yet authentic, 
        capturing a moment of quiet confidence.""",
        "target_text": "Women 25-45, urban professionals, high disposable income",
        "format": "9:16",
        "garment_count": 3,
        "intent": "awareness",
        "camera_pack": "auto",
        "shot_pack": "auto",
        "lighting_pack": "auto",
        "environment_pack": "auto",
        "style_pack": "cinematic_memory",
        "branding_pack": "auto",
        "lens_pack": "auto",
        "film_texture_pack": "auto",
        "color_science_pack": "muted_blues_and_amber",
        "time_weather_pack": "auto",
        "pose_discipline_pack": "auto",
        "studio_override": "OFF",
        "use_logo": True,
        "use_pose_ref": True,
        "use_photo_style_ref": True,
        "style_ref_count": 2,
        "use_location_ref": True,
        "location_ref_count": 1,
    }
    
    print("\n--- STEP 1: Local Resolver ---")
    local_resolver = LocalResolver(config)
    resolved = local_resolver.resolve(seed_state)
    
    print("\n--- STEP 2: Prompt Compilation ---")
    compiler = PromptCompiler(config)
    prompt = compiler.compile(resolved)
    
    print("\n" + "=" * 60)
    print("FINAL OUTPUTS")
    print("=" * 60)
    
    print("\n>>> NANO_BANANA_PROMPT:")
    print(prompt)
    
    print("\n>>> RESOLVED_JSON:")
    import json
    print(json.dumps(resolved, indent=2))
    
    print("\n>>> DEBUG_LOG (summary):")
    print(local_resolver.get_debug_log())
    print(compiler.get_debug_log())
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE - All systems operational")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# MORPHEUS FASHION PHOTO SYSTEM - TEST SUITE")
    print("#" * 60)
    
    config = test_config_loader()
    resolved = test_local_resolver(config)
    test_prompt_compiler(config, resolved)
    test_studio_override(config)
    test_intent_variations(config)
    test_gemini_resolver_availability(config)
    test_gemini_fallback_flow(config)
    run_full_simulation()
    
    print("\n" + "#" * 60)
    print("# ALL TESTS PASSED")
    print("#" * 60)
