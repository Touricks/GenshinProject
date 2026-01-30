"""
Verify the Neo4j knowledge graph integrity and test queries.

Usage:
    python -m scripts.verify_graph
"""

from ..graph.connection import Neo4jConnection
from ..graph.builder import GraphBuilder
from ..graph.searcher import GraphSearcher


def verify_schema(conn: Neo4jConnection) -> bool:
    """Verify that all constraints and indexes exist."""
    print("\n--- Verifying Schema ---")

    # Check constraints
    constraints = conn.execute("SHOW CONSTRAINTS")
    constraint_names = [c.get("name", "") for c in constraints]

    expected_constraints = [
        "character_name",
        "org_name",
    ]

    all_present = True
    for expected in expected_constraints:
        found = any(expected in name for name in constraint_names)
        status = "✓" if found else "✗"
        print(f"  {status} Constraint: {expected}")
        if not found:
            all_present = False

    return all_present


def verify_nodes(conn: Neo4jConnection) -> bool:
    """Verify that expected nodes exist."""
    print("\n--- Verifying Nodes ---")

    # Check Character nodes
    chars = conn.execute("MATCH (c:Character) RETURN count(c) as count")
    char_count = chars[0]["count"] if chars else 0
    print(f"  Characters: {char_count}")

    # Check Organization nodes
    orgs = conn.execute("MATCH (o:Organization) RETURN count(o) as count")
    org_count = orgs[0]["count"] if orgs else 0
    print(f"  Organizations: {org_count}")

    # Check specific important characters
    important_chars = ["恰斯卡", "基尼奇", "派蒙", "旅行者"]
    for char in important_chars:
        result = conn.execute(
            "MATCH (c:Character {name: $name}) RETURN c.name as name",
            {"name": char},
        )
        status = "✓" if result else "✗"
        print(f"  {status} Character '{char}' exists")

    return char_count > 0 and org_count > 0


def verify_relationships(conn: Neo4jConnection) -> bool:
    """Verify that expected relationships exist."""
    print("\n--- Verifying Relationships ---")

    # Count total relationships
    rels = conn.execute("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = rels[0]["count"] if rels else 0
    print(f"  Total relationships: {rel_count}")

    # Check specific relationships
    test_cases = [
        ("恰斯卡", "MEMBER_OF", "花羽会"),
        ("基尼奇", "PARTNER_OF", "阿尤"),
        ("旅行者", "PARTNER_OF", "派蒙"),
    ]

    all_present = True
    for source, rel_type, target in test_cases:
        query = f"""
        MATCH (a {{name: $source}})-[r:{rel_type}]-(b {{name: $target}})
        RETURN count(r) as count
        """
        result = conn.execute(query, {"source": source, "target": target})
        found = result[0]["count"] > 0 if result else False
        status = "✓" if found else "✗"
        print(f"  {status} {source} --[{rel_type}]--> {target}")
        if not found:
            all_present = False

    return all_present


def test_queries(searcher: GraphSearcher) -> bool:
    """Test common query patterns."""
    print("\n--- Testing Queries ---")

    all_passed = True

    # Test 1: Search all relations
    print("\n  Test 1: Search all relations for 恰斯卡")
    result = searcher.search("恰斯卡")
    passed = result["count"] > 0
    status = "✓" if passed else "✗"
    print(f"    {status} Found {result['count']} relations")
    all_passed &= passed

    # Test 2: Get friends
    print("\n  Test 2: Get friends of 恰斯卡")
    friends = searcher.get_friends("恰斯卡")
    passed = len(friends) > 0
    status = "✓" if passed else "✗"
    print(f"    {status} Found {len(friends)} friends")
    for f in friends[:3]:
        print(f"      - {f.get('name')}")
    all_passed &= passed

    # Test 3: Get organization members
    print("\n  Test 3: Get members of 花羽会")
    members = searcher.get_organization_members("花羽会")
    passed = len(members) > 0
    status = "✓" if passed else "✗"
    print(f"    {status} Found {len(members)} members")
    for m in members[:3]:
        print(f"      - {m.get('name')} ({m.get('role', 'member')})")
    all_passed &= passed

    # Test 4: Get path between entities
    print("\n  Test 4: Find path between 基尼奇 and 恰斯卡")
    path = searcher.get_path_between("基尼奇", "恰斯卡")
    passed = path is not None
    status = "✓" if passed else "✗"
    if path:
        print(f"    {status} Path: {' -> '.join(path['path_nodes'])}")
    else:
        print(f"    {status} No path found")
    all_passed &= passed

    # Test 5: Character organization
    print("\n  Test 5: Get organization for 基尼奇")
    orgs = searcher.get_character_organization("基尼奇")
    passed = len(orgs) > 0
    status = "✓" if passed else "✗"
    print(f"    {status} Found {len(orgs)} organizations")
    for org in orgs:
        print(f"      - {org.get('org_name')}")
    all_passed &= passed

    return all_passed


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Neo4j Knowledge Graph Verification")
    print("=" * 60)

    conn = Neo4jConnection()

    if not conn.verify_connectivity():
        print("\nERROR: Cannot connect to Neo4j.")
        print("Make sure Neo4j is running: docker-compose up -d neo4j")
        return

    print("\n✓ Connected to Neo4j")

    # Get stats first
    with GraphBuilder(conn) as builder:
        stats = builder.get_stats()
        print("\n--- Current Graph Statistics ---")
        for name, count in stats.items():
            print(f"  {name.capitalize()}: {count}")

    # Run verifications
    results = []

    results.append(("Schema", verify_schema(conn)))
    results.append(("Nodes", verify_nodes(conn)))
    results.append(("Relationships", verify_relationships(conn)))

    with GraphSearcher(conn) as searcher:
        results.append(("Queries", test_queries(searcher)))

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
        all_passed &= passed

    print("\n" + "=" * 60)
    if all_passed:
        print("All verifications PASSED!")
    else:
        print("Some verifications FAILED. Check the output above.")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
