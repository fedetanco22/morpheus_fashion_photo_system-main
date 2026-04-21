"""
Morpheus Fashion Photo System - ComfyUI Custom Node
Fashion Advertising Decision System for Nano Banana prompt generation

Includes two node variants:
- MorpheusFashionPhotoSystem: Full control with pack-based configuration
- MorpheusFashionPhotoSystemLight: Simplified UI with creative Gemini interpretation
"""

from .morpheus_node import MorpheusFashionPhotoSystem
from .morpheus_node_light import MorpheusFashionPhotoSystemLight
from .verify_api_node import MorpheusVerifyGeminiAPI

NODE_CLASS_MAPPINGS = {
    "MorpheusFashionPhotoSystem": MorpheusFashionPhotoSystem,
    "MorpheusFashionPhotoSystemLight": MorpheusFashionPhotoSystemLight,
    "MorpheusVerifyGeminiAPI": MorpheusVerifyGeminiAPI
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MorpheusFashionPhotoSystem": "Morpheus Fashion Photo System",
    "MorpheusFashionPhotoSystemLight": "Morpheus Fashion Photo System (Light)",
    "MorpheusVerifyGeminiAPI": "Morpheus Verify Gemini API"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
