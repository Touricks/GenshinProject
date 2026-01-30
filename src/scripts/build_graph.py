"""
Build the Neo4j knowledge graph from dialogue data.

Usage:
    python -m scripts.build_graph [DATA_DIR]
    python -m scripts.build_graph --clear  # Clear and rebuild
    python -m scripts.build_graph --stats  # Show graph statistics

Examples:
    # Build graph from default Data/ directory
    python -m scripts.build_graph

    # Build from custom directory
    python -m scripts.build_graph /path/to/data

    # Clear existing graph and rebuild
    python -m scripts.build_graph --clear

    # Show current graph statistics
    python -m scripts.build_graph --stats
"""

import argparse
from pathlib import Path
from tqdm import tqdm

from ..graph.connection import Neo4jConnection
from ..graph.builder import GraphBuilder
from ..ingestion.entity_extractor import EntityExtractor
from ..ingestion.llm_kg_extractor import extract_kg_from_file
from ..models.entities import MAIN_CHARACTERS
from ..models.relationships import Relationship, RelationType


def build_graph(
    data_dir: str = "Data/",
    clear_existing: bool = False,
    skip_seed: bool = False,
) -> None:
    """
    Build the Neo4j knowledge graph from dialogue files.

    Args:
        data_dir: Path to the data directory
        clear_existing: Whether to clear existing graph first
        skip_seed: Whether to skip seed data (for incremental updates)
    """
    print("=" * 60)
    print("Neo4j Knowledge Graph Builder")
    print("=" * 60)

    # Initialize connection
    conn = Neo4jConnection()
    if not conn.verify_connectivity():
        print("\nERROR: Cannot connect to Neo4j.")
        print("Make sure Neo4j is running: docker-compose up -d neo4j")
        return

    with GraphBuilder(conn) as builder:
        # Clear if requested
        if clear_existing:
            print("\nClearing existing graph...")
            builder.clear_graph()

        # Setup schema
        builder.setup_schema()

        # Create seed data
        if not skip_seed:
            print("\n--- Phase 1: Seed Data ---")
            builder.create_seed_organizations()
            builder.create_seed_characters()
            builder.create_seed_relationships()

        # Extract and load from dialogue files
        print(f"\n--- Phase 2: Processing Dialogue Files ---")
        print(f"Data directory: {data_dir}")

        # Use EntityExtractor for metadata parsing only
        metadata_extractor = EntityExtractor()
        data_path = Path(data_dir)

        if not data_path.exists():
            print(f"ERROR: Data directory not found: {data_dir}")
            return

        # Get all dialogue files
        dialogue_files = sorted(data_path.rglob("chapter*_dialogue.txt"))

        print(f"Found {len(dialogue_files)} dialogue files")

        # Track all discovered characters and relationships
        all_characters = set()
        all_relationships = []

        # Process each file
        for file_path in tqdm(dialogue_files, desc="Processing files"):
            try:
                # 1. Parse Metadata using EntityExtractor (regex fast path)
                # We extract using extract_from_file but primarily use the metadata
                regex_result = metadata_extractor.extract_from_file(file_path)
                
                # Global Timeline Logic (ADR-007 + Folder Strategy)
                # Calculate global chapter from Folder ID and Chapter Number
                try:
                    folder_id = int(file_path.parent.name)
                    local_chapter = regex_result.metadata.chapter_number or 0
                    global_chapter = folder_id * 100 + local_chapter
                    
                    # Override metadata with global sequence
                    regex_result.metadata.chapter_number = global_chapter
                    regex_result.metadata.task_id = str(folder_id) # Ensure task context is folder ID
                except ValueError:
                     # Fallback for non-numeric folders (e.g. "Lore", "Backup")
                    pass
                
                # 2. Extract Knowledge Graph using LLM (smart slow path)
                try:
                    kg_output = extract_kg_from_file(file_path)
                except Exception as e:
                    print(f"LLM Extraction failed for {file_path.name}: {e}")
                    continue

                # Collect characters from LLM output
                for entity in kg_output.get_characters():
                    # Normalize name (reuse extractor logic or simple strip)
                    char_name = entity.name.strip()
                    all_characters.add(char_name)

                    # Create character node if not in seed data
                    if char_name not in MAIN_CHARACTERS:
                        builder.create_character_simple(
                            char_name,
                            regex_result.metadata.task_id,
                            regex_result.metadata.chapter_number,
                        )
                        # TODO: We could use entity.role to update the character description/title immediately
                        # but create_character_simple doesn't support it yet.

                # Collect relationships from LLM output
                for rel in kg_output.relationships:
                    # Convert Pydantic ExtractedRelationship to Model Relationship
                    try:
                        # Map string to Enum
                        rel_type_enum = RelationType(rel.relation_type)
                        
                        # Create proper Relationship object
                        new_rel = Relationship(
                            source=rel.source,
                            target=rel.target,
                            rel_type=rel_type_enum,
                            properties={
                                "description": rel.description,
                                "evidence": rel.evidence
                            },
                            chapter=regex_result.metadata.chapter_number,
                            task_id=regex_result.metadata.task_id
                        )
                        all_relationships.append(new_rel)
                    except ValueError:
                        print(f"Unknown relation type: {rel.relation_type}")

            except Exception as e:
                print(f"\nError processing {file_path}: {e}")

        # Create relationships (deduplicated)
        print(f"\n--- Phase 3: Creating Relationships ---")
        print(f"Total extracted relationships: {len(all_relationships)}")

        # Deduplicate relationships
        # Key: (source, target, type, chapter) to allow temporal evolution
        seen = set()
        unique_relationships = []
        for rel in all_relationships:
            key = (rel.source, rel.target, rel.rel_type, rel.chapter)
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        print(f"Unique relationships: {len(unique_relationships)}")

        # Create in batches
        for rel in tqdm(unique_relationships, desc="Creating relationships"):
            builder.create_relationship(rel)

        # Print statistics
        print("\n--- Graph Statistics ---")
        stats = builder.get_stats()
        for name, count in stats.items():
            print(f"  {name.capitalize()}: {count}")

        print("\n" + "=" * 60)
        print("Graph build complete!")
        print("=" * 60)


def show_stats() -> None:
    """Show current graph statistics."""
    conn = Neo4jConnection()
    if not conn.verify_connectivity():
        print("Cannot connect to Neo4j.")
        return

    with GraphBuilder(conn) as builder:
        print("\n--- Graph Statistics ---")
        stats = builder.get_stats()
        for name, count in stats.items():
            print(f"  {name.capitalize()}: {count}")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Build Neo4j knowledge graph from dialogue data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "data_dir",
        nargs="?",
        default="Data/",
        help="Path to data directory (default: Data/)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing graph before building",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seed data (for incremental updates)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show graph statistics only",
    )

    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        build_graph(
            data_dir=args.data_dir,
            clear_existing=args.clear,
            skip_seed=args.skip_seed,
        )


if __name__ == "__main__":
    main()
