"""
Resolvers for Morpheus Fashion Photo System
"""

from .local_resolver import LocalResolver
from .gemini_resolver import GeminiResolver

__all__ = ['LocalResolver', 'GeminiResolver']
