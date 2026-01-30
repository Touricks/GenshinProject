"""
LLM-based Knowledge Graph Extractor.

Uses LLM (via OpenAI-compatible API) to extract entities and relationships
from dialogue text for building knowledge graphs.

This module is independent of Neo4j and can be tested without a database connection.
"""

import os
from pathlib import Path
from typing import List, Optional, Literal, Set
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env from src directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
print(f"DEBUG: Loading .env from {env_path}")
print(f"DEBUG: GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")
print(f"DEBUG: GEMINI_API_KEY present: {'GEMINI_API_KEY' in os.environ}")


# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================

class ExtractedEntity(BaseModel):
    """A single extracted entity from text."""
    name: str = Field(description="实体名称（中文）")
    entity_type: Literal["Character", "Organization", "Location", "Event"] = Field(
        description="实体类型"
    )
    role: Optional[str] = Field(
        default=None,
        description="角色职业/头衔，如「医生」"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="别名列表"
    )


class ExtractedRelationship(BaseModel):
    """A single extracted relationship between entities."""
    source: str = Field(description="关系源实体名称")
    target: str = Field(description="关系目标实体名称")
    relation_type: Literal[
        "FRIEND_OF",      # 朋友、友好关系
        "ENEMY_OF",       # 敌人、对立关系
        "PARTNER_OF",     # 伙伴、搭档、助理、龙伴
        "FAMILY_OF",      # 亲属关系
        "MEMBER_OF",      # 属于某组织/部族
        "LEADER_OF",      # 组织的领导者
        "PARTICIPATED_IN", # 参与事件
        "LOCATED_IN",     # 位于某地
        "INTERACTS_WITH"  # 仅有对话交互（兜底）
    ] = Field(description="关系类型")
    description: Optional[str] = Field(
        default=None,
        description="关系描述/文本证据"
    )
    evidence: Optional[str] = Field(
        default=None,
        description="支持该关系的原文引用/文本片段"
    )


class KnowledgeGraphOutput(BaseModel):
    """Complete knowledge graph extraction output."""
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="所有提取的实体"
    )
    relationships: List[ExtractedRelationship] = Field(
        default_factory=list,
        description="实体间的关系"
    )

    def get_entity_names(self) -> Set[str]:
        """Get all entity names as a set."""
        return {e.name for e in self.entities}

    def get_characters(self) -> List[ExtractedEntity]:
        """Get only character entities."""
        return [e for e in self.entities if e.entity_type == "Character"]

    def get_organizations(self) -> List[ExtractedEntity]:
        """Get only organization entities."""
        return [e for e in self.entities if e.entity_type == "Organization"]

    def get_locations(self) -> List[ExtractedEntity]:
        """Get only location entities."""
        return [e for e in self.entities if e.entity_type == "Location"]


# =============================================================================
# Extraction Prompt
# =============================================================================

EXTRACTION_PROMPT = """你是一个原神（Genshin Impact）剧情文本分析专家，精通提瓦特大陆（Teyvat）的所有设定，包括但不限于纳塔（Natlan）、枫丹（Fontaine）、须弥（Sumeru）、稻妻（Inazuma）、璃月（Liyue）、蒙德（Mondstadt）和至冬（Snezhnaya）。

请从以下对话文本中提取知识图谱（实体+关系）。

## 背景知识（辅助实体/关系判断）
- **通用组织**：
  - **愚人众 (Fatui)**：执行官（Harbingers，如「队长」、「博士」、「仆人」）、债务处理人、雷萤术士等。
  - **深渊教团 (Abyss Order)**：深渊法师、咏者、「王子/公主」。
  - **冒险家协会**：凯瑟琳、冒险家。
  - **魔女会**：神秘的高战力女性组织。

- **地区特色组织**：
  - **纳塔**：六大部族（花羽会、流泉之众、悬木人、回声之子、烟谜主、沃土之邦）。
  - **枫丹**：执律庭、特巡队、刺玫会、水仙十字结社。
  - **须弥**：教令院（六大学派）、镀金旅团、兰那罗。
  - **稻妻**：三奉行（社奉行、天领奉行、勘定奉行）、海祇岛反抗军。
  - **璃月**：璃月七星、千岩军、往生堂、仙人。
  - **蒙德**：西风骑士团、教会。

- **重要概念**：神之眼（Vision）、神之心（Gnosis）、古名（Natlan特有）、地脉、天空岛（Celestia）。

## 实体提取规则
1. **角色(Character)**：
   - 提取所有对话参与者及提到的重要人物。
   - **旅行者**别名映射：杜麦尼、玩家、Traveler、金发异乡人、荣誉骑士。
   - **派蒙**别名映射：飞行的小精灵、应急食品、最好的伙伴。
   - 提取 Role 字段：如 "火神"、"执行官"、"大萨满"、"代理团长"、"审判官" 等。
   
2. **组织(Organization)**：
   - 各国官方机构、民间组织、敌对势力。
   
3. **地点(Location)**：
   - 七国名称、地标建筑（如「玉京台」、「梅洛彼得堡」）、自然景观。

## 关系提取规则 (relation_type)
请深入理解语境，**不要**仅仅提取 INTERACTS_WITH。
- **MEMBER_OF**: 某人属于某部族/组织/国家。
  - 例："我是流泉之众的向导" -> MEMBER_OF(流泉之众)
  - 例："西风骑士团的侦察骑士" -> MEMBER_OF(西风骑士团)
- **LEADER_OF**: 明确的领导关系。
  - 例："火神玛薇卡" -> LEADER_OF(纳塔)
  - 例："那维莱特是最高审判官" -> LEADER_OF(枫丹执律庭)
- **PARTNER_OF**: 搭档、长期合作、龙伙伴、主仆/助理。
  - 例："基尼奇和阿尤" -> PARTNER_OF (description="龙伙伴")
  - 例："林尼和琳妮特" -> PARTNER_OF (description="魔术搭档")
- **FRIEND_OF**: 朋友、友好的熟人。
- **FAMILY_OF**: 父母、兄弟姐妹、祖孙。
  - 例："林尼、琳妮特、菲米尼" -> FAMILY_OF (description="壁炉之家的家人")
- **ENEMY_OF**: 战斗对手、敌对阵营。
- **INTERACTS_WITH**: 仅当无法归类为以上强关系时，用于记录对话发生。

## 对话文本
{text}

4. **文本证据(evidence)**：
   - 对于每个关系，提取一段支持该关系的原文片段（quote）。
   - 如果是推理得出的关系，引用相关的对话上下文。

请输出严格的JSON格式。
"""


# =============================================================================
# LLM Knowledge Graph Extractor
# =============================================================================

class LLMKnowledgeGraphExtractor:
    """
    Extract complete knowledge graph using LLM.

    This class is independent of Neo4j and produces Pydantic objects
    that can be serialized to JSON for caching or testing.
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the LLM extractor.

        Args:
            model: Model name (defaults to GEMINI_MODEL env var)
            api_key: API key (defaults to GEMINI_API_KEY env var)
        """
        from llama_index.llms.openai_like import OpenAILike

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        api_base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        
        # Try GEMINI_API_KEY first, then GOOGLE_API_KEY
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required")

        self.llm = OpenAILike(
            model=self.model,
            api_base=api_base,
            api_key=api_key,
            is_chat_model=True,
            context_window=32000,
        )
        self.structured_llm = self.llm.as_structured_llm(KnowledgeGraphOutput)

    def _build_prompt(self, text: str) -> str:
        """Build the extraction prompt with the input text."""
        return EXTRACTION_PROMPT.format(text=text)

    def extract(self, text: str) -> KnowledgeGraphOutput:
        """
        Extract entities and relationships from text.

        Args:
            text: Dialogue text to extract from

        Returns:
            KnowledgeGraphOutput containing entities and relationships
        """
        prompt = self._build_prompt(text)
        response = self.structured_llm.complete(prompt)
        return response.raw

    def extract_entities_only(self, text: str) -> List[ExtractedEntity]:
        """
        Extract only entities (for compatibility with existing code).

        Args:
            text: Dialogue text to extract from

        Returns:
            List of extracted entities
        """
        result = self.extract(text)
        return result.entities

    def extract_relationships_only(self, text: str) -> List[ExtractedRelationship]:
        """
        Extract only relationships (for compatibility with existing code).

        Args:
            text: Dialogue text to extract from

        Returns:
            List of extracted relationships
        """
        result = self.extract(text)
        return result.relationships

    def extract_character_names(self, text: str) -> Set[str]:
        """
        Extract character names only (for compatibility with EntityExtractor).

        Args:
            text: Dialogue text to extract from

        Returns:
            Set of character names
        """
        result = self.extract(text)
        return {e.name for e in result.entities if e.entity_type == "Character"}


# =============================================================================
# Convenience Functions
# =============================================================================

def extract_kg_from_text(text: str) -> KnowledgeGraphOutput:
    """
    Convenience function to extract KG from text.

    Args:
        text: Dialogue text

    Returns:
        KnowledgeGraphOutput
    """
    extractor = LLMKnowledgeGraphExtractor()
    return extractor.extract(text)


def extract_kg_from_file(file_path: Path) -> KnowledgeGraphOutput:
    """
    Extract KG from a dialogue file.

    Args:
        file_path: Path to dialogue file

    Returns:
        KnowledgeGraphOutput
    """
    text = file_path.read_text(encoding="utf-8")
    return extract_kg_from_text(text)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    # Test with a sample text
    test_text = """
恰斯卡：这位是我们部族的「医生」伊法…和他的助理咔库库。

伊法：…伤口已经处理完了。

派蒙：——嘿！恰斯卡！

恰斯卡：嗯，派蒙？还有我们的「杜麦尼」？
"""

    print("Testing LLM Knowledge Graph Extractor...")
    print("=" * 60)
    print("Input text:")
    print(test_text)
    print("=" * 60)

    try:
        extractor = LLMKnowledgeGraphExtractor()
        result = extractor.extract(test_text)

        print("\nExtracted Entities:")
        for entity in result.entities:
            role_str = f" (role={entity.role})" if entity.role else ""
            aliases_str = f" aliases={entity.aliases}" if entity.aliases else ""
            print(f"  - {entity.name} [{entity.entity_type}]{role_str}{aliases_str}")

        print("\nExtracted Relationships:")
        for rel in result.relationships:
            desc_str = f" ({rel.description})" if rel.description else ""
            print(f"  - {rel.source} --[{rel.relation_type}]--> {rel.target}{desc_str}")

        print("\nJSON Output:")
        print(result.model_dump_json(indent=2))

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
