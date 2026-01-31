"""
Relationship models for the knowledge graph.

Defines relationship types and seed data for character connections.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class RelationType(str, Enum):
    """Types of relationships in the knowledge graph."""

    # Social relationships
    FRIEND_OF = "FRIEND_OF"
    ENEMY_OF = "ENEMY_OF"
    PARTNER_OF = "PARTNER_OF"
    FAMILY_OF = "FAMILY_OF"

    # Organizational relationships
    MEMBER_OF = "MEMBER_OF"
    LEADER_OF = "LEADER_OF"

    # Event relationships
    PARTICIPATED_IN = "PARTICIPATED_IN"
    EXPERIENCES = "EXPERIENCES"  # Character experiences a major Event

    # Location relationships
    OCCURRED_AT = "OCCURRED_AT"
    LOCATED_IN = "LOCATED_IN"

    # Content relationships
    MENTIONED_IN = "MENTIONED_IN"
    CONTAINS = "CONTAINS"

    # Temporal relationships
    LEADS_TO = "LEADS_TO"
    NEXT = "NEXT"

    # Interaction (co-occurrence)
    INTERACTS_WITH = "INTERACTS_WITH"


@dataclass
class Relationship:
    """A relationship between two entities."""

    source: str
    target: str
    rel_type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    chapter: Optional[int] = None
    task_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Neo4j."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.rel_type.value,
            "properties": self.properties,
            "chapter": self.chapter,
            "task_id": self.task_id,
        }


# =============================================================================
# Seed Relationships from Story Analysis
# =============================================================================

SEED_RELATIONSHIPS: List[Relationship] = [
    # -------------------------------------------------------------------------
    # Character -> Organization (MEMBER_OF)
    # -------------------------------------------------------------------------
    Relationship("恰斯卡", "花羽会", RelationType.MEMBER_OF, {"role": "peacemaker"}),
    Relationship("伊法", "烟谜主", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("卡齐娜", "回声之子", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("玛拉妮", "流泉之众", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("基尼奇", "悬木人", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("希诺宁", "回声之子", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("伊安珊", "沃土之邦", RelationType.MEMBER_OF, {"role": "member"}),
    Relationship("茜特菈莉", "烟谜主", RelationType.MEMBER_OF, {"role": "shaman"}),
    # -------------------------------------------------------------------------
    # Character -> Character (PARTNER_OF)
    # -------------------------------------------------------------------------
    Relationship(
        "旅行者", "派蒙", RelationType.PARTNER_OF, {"type": "travel_companion"}
    ),
    Relationship("基尼奇", "阿尤", RelationType.PARTNER_OF, {"type": "dragon_partner"}),
    Relationship("伊法", "咔库库", RelationType.PARTNER_OF, {"type": "assistant"}),
    # -------------------------------------------------------------------------
    # Character -> Character (FRIEND_OF)
    # -------------------------------------------------------------------------
    Relationship("恰斯卡", "卡齐娜", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("恰斯卡", "玛拉妮", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("恰斯卡", "基尼奇", RelationType.FRIEND_OF, {"strength": "acquaintance"}),
    Relationship("恰斯卡", "希诺宁", RelationType.FRIEND_OF, {"strength": "acquaintance"}),
    Relationship("卡齐娜", "玛拉妮", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("卡齐娜", "基尼奇", RelationType.FRIEND_OF, {"strength": "acquaintance"}),
    Relationship("玛拉妮", "基尼奇", RelationType.FRIEND_OF, {"strength": "acquaintance"}),
    Relationship("旅行者", "恰斯卡", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("旅行者", "卡齐娜", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("旅行者", "玛拉妮", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("旅行者", "基尼奇", RelationType.FRIEND_OF, {"strength": "close"}),
    Relationship("旅行者", "希诺宁", RelationType.FRIEND_OF, {"strength": "close"}),
    # -------------------------------------------------------------------------
    # Organization -> Organization (PART_OF)
    # -------------------------------------------------------------------------
    # All tribes are part of Natlan
    Relationship("花羽会", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
    Relationship("流泉之众", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
    Relationship("悬木人", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
    Relationship("沃土之邦", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
    Relationship("回声之子", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
    Relationship("烟谜主", "纳塔", RelationType.MEMBER_OF, {"type": "tribe"}),
]


# Relationship keywords for extraction
RELATIONSHIP_KEYWORDS = {
    "朋友": RelationType.FRIEND_OF,
    "伙伴": RelationType.PARTNER_OF,
    "敌人": RelationType.ENEMY_OF,
    "同伴": RelationType.PARTNER_OF,
    "族长": RelationType.LEADER_OF,
    "成员": RelationType.MEMBER_OF,
    "家人": RelationType.FAMILY_OF,
}
