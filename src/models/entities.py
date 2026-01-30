"""
Entity models for the knowledge graph.

Defines dataclasses for Character, Organization, Location, and Event nodes.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Character:
    """Character entity for the knowledge graph."""

    name: str
    aliases: List[str] = field(default_factory=list)
    title: Optional[str] = None
    region: Optional[str] = None
    tribe: Optional[str] = None
    description: Optional[str] = None
    first_appearance_task: Optional[str] = None
    first_appearance_chapter: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Neo4j."""
        return {
            "name": self.name,
            "aliases": self.aliases,
            "title": self.title,
            "region": self.region,
            "tribe": self.tribe,
            "description": self.description,
            "first_appearance_task": self.first_appearance_task,
            "first_appearance_chapter": self.first_appearance_chapter,
        }


@dataclass
class Organization:
    """Organization entity (tribe, guild, nation)."""

    name: str
    org_type: str  # "tribe", "guild", "nation", "faction"
    region: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Neo4j."""
        return {
            "name": self.name,
            "type": self.org_type,
            "region": self.region,
            "description": self.description,
        }


@dataclass
class Location:
    """Location entity."""

    name: str
    location_type: Optional[str] = None  # "arena", "settlement", "landmark"
    region: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Neo4j."""
        return {
            "name": self.name,
            "type": self.location_type,
            "region": self.region,
            "description": self.description,
        }


@dataclass
class Event:
    """Event entity (quest, battle, ceremony)."""

    name: str
    event_type: Optional[str] = None  # "battle", "ceremony", "quest"
    chapter_range: List[int] = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Neo4j."""
        return {
            "name": self.name,
            "type": self.event_type,
            "chapter_range": self.chapter_range,
            "description": self.description,
        }


# =============================================================================
# Seed Data: Known entities from story analysis
# =============================================================================

KNOWN_ORGANIZATIONS = {
    # Natlan tribes
    "花羽会": Organization("花羽会", "tribe", "纳塔", "以飞行和弓术闻名的部族"),
    "流泉之众": Organization("流泉之众", "tribe", "纳塔", "擅长水疗和医术的部族"),
    "悬木人": Organization("悬木人", "tribe", "纳塔", "与龙共存的战士部族，擅长极限运动"),
    "沃土之邦": Organization("沃土之邦", "tribe", "纳塔", "商业繁荣的部族"),
    "回声之子": Organization("回声之子", "tribe", "纳塔", "精通机关和采矿的部族"),
    "烟谜主": Organization("烟谜主", "tribe", "纳塔", "与灵界沟通的神秘部族"),
    # Nations
    "纳塔": Organization("纳塔", "nation", "纳塔", "火之国度"),
    "枫丹": Organization("枫丹", "nation", "枫丹", "水之国度"),
    "须弥": Organization("须弥", "nation", "须弥", "智慧之国度"),
    "蒙德": Organization("蒙德", "nation", "蒙德", "风之国度"),
    "璃月": Organization("璃月", "nation", "璃月", "岩之国度"),
    # Factions
    "愚人众": Organization("愚人众", "faction", "至冬", "至冬的执行者组织"),
}

MAIN_CHARACTERS = {
    # Natlan main characters
    "恰斯卡": Character(
        name="恰斯卡",
        title="花羽会调停人",
        region="纳塔",
        tribe="花羽会",
        description="花羽会的调停人，精通弓术和飞行",
    ),
    "卡齐娜": Character(
        name="卡齐娜",
        region="纳塔",
        tribe="回声之子",
        description="年轻的大地岩手，性格坚韧",
    ),
    "玛拉妮": Character(
        name="玛拉妮",
        region="纳塔",
        tribe="流泉之众",
        description="著名的水上用品商店老板，擅长水上运动",
    ),
    "基尼奇": Character(
        name="基尼奇",
        region="纳塔",
        tribe="悬木人",
        description="被称为「回火的猎手」的猎龙人，与龙阿尤是伙伴",
    ),
    "阿尤": Character(
        name="阿尤",
        aliases=["阿乔", "库胡勒阿乔"],
        description="基尼奇的龙伙伴，自称「圣龙」，喜欢说话和吐槽",
    ),
    "希诺宁": Character(
        name="希诺宁",
        region="纳塔",
        tribe="回声之子",
        description="著名的锻造师和打碟手",
    ),
    "伊法": Character(
        name="伊法",
        region="纳塔",
        tribe="烟谜主",
        description="著名的理疗师，曾在花羽会工作",
    ),
    "咔库库": Character(
        name="咔库库",
        description="伊法的助理，一只会学舌的小龙",
    ),
    "伊安珊": Character(
        name="伊安珊",
        region="纳塔",
        tribe="沃土之邦",
        description="沃土之邦的强力战士，纳塔的向导",
    ),
    "玛薇卡": Character(
        name="玛薇卡",
        title="火神",
        region="纳塔",
        description="纳塔的火之神",
    ),
    # Traveler and companion
    "旅行者": Character(
        name="旅行者",
        aliases=["玩家", "杜麦尼", "Traveler"],
        description="来自异世界的旅行者，在纳塔获得了古名杜麦尼",
    ),
    "派蒙": Character(
        name="派蒙",
        description="旅行者的向导，飞行的小精灵",
    ),
    # Other important characters
    "伊涅芙": Character(
        name="伊涅芙",
        description="来自挪德卡莱的机关人偶，正在寻找自己的记忆",
    ),
    "爱诺": Character(
        name="爱诺",
        description="伊涅芙的制造者",
    ),
    "茜特菈莉": Character(
        name="茜特菈莉",
        aliases=["黑曜石奶奶"],
        region="纳塔",
        tribe="烟谜主",
        description="烟谜主的大萨满",
    ),
}

# System characters to filter out during extraction
SYSTEM_CHARACTERS = {
    "？？？",
    "选项",
    "---",
    "黑雾诅咒",
    "小机器人",
    "受伤的绒翼龙",
    "「木偶」",
}
