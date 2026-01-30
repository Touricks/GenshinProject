"""
Entity Normalizer Module.
Responsible for mapping extracted entity mentions to canonical names based on Seed Data.
Implements the "Seed as Anchor" strategy.
"""

from typing import Dict, List, Optional
import difflib
import logging

logger = logging.getLogger(__name__)

class EntityNormalizer:
    """
    Normalizes entity names against a known seed list (Anchor Data).
    """
    
    # Seed Data (Anchor Targets)
    # In a production system, this might be loaded from a YAML/JSON file.
    KNOWN_ORGANIZATIONS = [
        "花羽会",
        "悬木人",
        "流泉之众",
        "回声之子",
        "烟谜主",
        "沃卢之邦",
        "冒险家协会",
        "愚人众",
        "深渊教团"
    ]

    # Known aliases map (Explicit mappings)
    ALIAS_MAP = {
        "Flower-Feather Clan": "花羽会",
        "People of the Springs": "流泉之众",
        "Masters of the Night-Wind": "烟谜主",
        "Children of Echoes": "回声之子",
        "Scions of the Canopy": "悬木人",
        "Collective of Plenty": "沃卢之邦",
        "Fatui": "愚人众",
        "Abyss Order": "深渊教团",
        "Adventurers' Guild": "冒险家协会"
    }

    def __init__(self):
        """Initialize the normalizer."""
        self._org_set = set(self.KNOWN_ORGANIZATIONS)

    def normalize(self, name: str, entity_type: str = None) -> str:
        """
        Normalize an entity name.
        
        Args:
            name: The raw entity name extracted from text.
            entity_type: Optional type (e.g., 'Organization', 'Character').
            
        Returns:
            The normalized canonical name, or the original name if no match found.
        """
        if not name:
            return name
            
        # 1. Direct Alias Lookup
        if name in self.ALIAS_MAP:
            return self.ALIAS_MAP[name]
            
        # 2. Case-insensitive Alias Lookup
        for alias, canonical in self.ALIAS_MAP.items():
            if alias.lower() == name.lower():
                return canonical
                
        # 3. Organization Normalization
        if entity_type == "Organization" or (entity_type is None):
            normalized = self._normalize_organization(name)
            if normalized:
                return normalized
                
        return name

    def _normalize_organization(self, name: str) -> Optional[str]:
        """Try to normalize an organization name."""
        # 1. Exact match in seed
        if name in self._org_set:
            return name
            
        # 2. Fuzzy match against seed
        # Use simple cutoff 0.6 for now
        matches = difflib.get_close_matches(name, self.KNOWN_ORGANIZATIONS, n=1, cutoff=0.6)
        if matches:
            logger.debug(f"Normalized org '{name}' to '{matches[0]}'")
            return matches[0]
            
        return None
