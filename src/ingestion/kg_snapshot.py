"""
KG Snapshot Management.

Save and load versioned KG snapshots for backup and comparison.
Supports timestamped snapshots, listing, and retrieval of latest versions.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

# Handle both package and standalone imports
try:
    from .llm_kg_extractor import KnowledgeGraphOutput
except ImportError:
    from llm_kg_extractor import KnowledgeGraphOutput


class KGSnapshotManager:
    """
    Manage versioned KG snapshots.

    Features:
    - Save timestamped snapshots with optional names
    - Load snapshots by path
    - List all available snapshots with metadata
    - Retrieve the latest snapshot
    - Compare snapshots (entity/relationship counts)
    """

    def __init__(self, snapshot_dir: str = ".cache/kg/snapshots"):
        """
        Initialize the snapshot manager.

        Args:
            snapshot_dir: Directory to store snapshots
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save(self, kg: KnowledgeGraphOutput, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        Save a KG snapshot.

        Args:
            kg: KnowledgeGraphOutput to save
            name: Optional name for the snapshot
            metadata: Optional additional metadata to store

        Returns:
            Path to the saved snapshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json" if name else f"snapshot_{timestamp}.json"
        path = self.snapshot_dir / filename

        data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "name": name,
            "stats": {
                "entities": len(kg.entities),
                "relationships": len(kg.relationships),
                "characters": len(kg.get_characters()),
                "organizations": len(kg.get_organizations()),
                "locations": len(kg.get_locations()),
            },
            "metadata": metadata or {},
            "kg": kg.model_dump()
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, path: Path) -> KnowledgeGraphOutput:
        """
        Load a KG snapshot.

        Args:
            path: Path to the snapshot file

        Returns:
            KnowledgeGraphOutput from the snapshot
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        return KnowledgeGraphOutput.model_validate(data["kg"])

    def load_with_metadata(self, path: Path) -> Dict[str, Any]:
        """
        Load a snapshot with all metadata.

        Args:
            path: Path to the snapshot file

        Returns:
            Full snapshot data including metadata and KG
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        data["kg"] = KnowledgeGraphOutput.model_validate(data["kg"])
        return data

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots.

        Returns:
            List of snapshot info dicts, sorted by creation time (newest first)
        """
        snapshots = []
        for path in sorted(self.snapshot_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshots.append({
                    "path": str(path),
                    "filename": path.name,
                    "name": data.get("name"),
                    "created_at": data.get("created_at"),
                    "entities": data.get("stats", {}).get("entities"),
                    "relationships": data.get("stats", {}).get("relationships"),
                    "characters": data.get("stats", {}).get("characters"),
                    "organizations": data.get("stats", {}).get("organizations"),
                    "locations": data.get("stats", {}).get("locations"),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return snapshots

    def get_latest(self) -> Optional[KnowledgeGraphOutput]:
        """
        Get the most recent snapshot.

        Returns:
            KnowledgeGraphOutput from the latest snapshot, or None if no snapshots exist
        """
        snapshots = list(self.snapshot_dir.glob("*.json"))
        if not snapshots:
            return None
        latest = max(snapshots, key=lambda p: p.stat().st_mtime)
        return self.load(latest)

    def get_latest_path(self) -> Optional[Path]:
        """
        Get the path to the most recent snapshot.

        Returns:
            Path to the latest snapshot, or None if no snapshots exist
        """
        snapshots = list(self.snapshot_dir.glob("*.json"))
        if not snapshots:
            return None
        return max(snapshots, key=lambda p: p.stat().st_mtime)

    def get_by_name(self, name: str) -> Optional[KnowledgeGraphOutput]:
        """
        Get the most recent snapshot with a given name.

        Args:
            name: Snapshot name to search for

        Returns:
            KnowledgeGraphOutput or None if not found
        """
        matching = list(self.snapshot_dir.glob(f"{name}_*.json"))
        if not matching:
            return None
        latest = max(matching, key=lambda p: p.stat().st_mtime)
        return self.load(latest)

    def delete(self, path: Path) -> bool:
        """
        Delete a snapshot.

        Args:
            path: Path to the snapshot to delete

        Returns:
            True if deleted, False if not found
        """
        if path.exists():
            path.unlink()
            return True
        return False

    def clear_all(self):
        """Delete all snapshots."""
        for path in self.snapshot_dir.glob("*.json"):
            path.unlink()

    def compare(self, path1: Path, path2: Path) -> Dict[str, Any]:
        """
        Compare two snapshots.

        Args:
            path1: Path to first snapshot
            path2: Path to second snapshot

        Returns:
            Dict with comparison results
        """
        kg1 = self.load(path1)
        kg2 = self.load(path2)

        entities1 = kg1.get_entity_names()
        entities2 = kg2.get_entity_names()

        return {
            "snapshot1": str(path1),
            "snapshot2": str(path2),
            "entities": {
                "only_in_1": list(entities1 - entities2),
                "only_in_2": list(entities2 - entities1),
                "in_both": list(entities1 & entities2),
                "count_1": len(entities1),
                "count_2": len(entities2),
            },
            "relationships": {
                "count_1": len(kg1.relationships),
                "count_2": len(kg2.relationships),
            }
        }


# =============================================================================
# CLI for snapshot management
# =============================================================================

if __name__ == "__main__":
    import sys

    manager = KGSnapshotManager()

    if len(sys.argv) < 2:
        print("Usage: python kg_snapshot.py [list|latest|clear]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        snapshots = manager.list_snapshots()
        print(f"Snapshots ({len(snapshots)}):")
        for snap in snapshots:
            print(f"  [{snap['filename']}]")
            print(f"    Name: {snap['name']}")
            print(f"    Created: {snap['created_at']}")
            print(f"    Entities: {snap['entities']} ({snap['characters']} chars, {snap['organizations']} orgs)")
            print(f"    Relationships: {snap['relationships']}")
            print()

    elif command == "latest":
        path = manager.get_latest_path()
        if path:
            kg = manager.load(path)
            print(f"Latest snapshot: {path}")
            print(f"  Entities: {len(kg.entities)}")
            print(f"  Relationships: {len(kg.relationships)}")
        else:
            print("No snapshots found")

    elif command == "clear":
        manager.clear_all()
        print("All snapshots cleared")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
