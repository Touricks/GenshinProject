# Architecture Decision Record (ADR) Template

## ADR Format

```markdown
# ADR-[NUMBER]: [TITLE]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Date
[YYYY-MM-DD]

## Context
[Describe the situation and why a decision is needed.
Include technical and business drivers.]

## Decision
[State the decision clearly and unambiguously.
Start with "We will..." or "We have decided to..."]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Neutral
- [Observation that is neither positive nor negative]

## Alternatives Considered

### Option 1: [Name]
[Brief description]
- Pros: ...
- Cons: ...
- Why rejected: ...

### Option 2: [Name]
[Brief description]
- Pros: ...
- Cons: ...
- Why rejected: ...

## References
- [Link to relevant documentation]
- [Link to discussion]
```

## Example ADR

```markdown
# ADR-001: Use PostgreSQL as Primary Database

## Status
Accepted

## Date
2024-01-15

## Context
We need to select a primary database for our application.
Requirements:
- ACID compliance for financial transactions
- JSON support for flexible metadata
- Good ORM support for TypeScript
- Managed hosting options available

## Decision
We will use PostgreSQL as our primary database, hosted on Supabase.

## Consequences

### Positive
- Strong ACID compliance
- Excellent JSON/JSONB support
- Supabase provides auth, realtime, and storage
- Large ecosystem and community
- Team has PostgreSQL experience

### Negative
- Vertical scaling limitations
- Supabase vendor lock-in for some features
- More complex than SQLite for simple use cases

### Neutral
- Need to manage migrations carefully
- Will use Prisma as ORM

## Alternatives Considered

### Option 1: MongoDB
- Pros: Flexible schema, horizontal scaling
- Cons: No ACID for multi-document, team unfamiliar
- Why rejected: ACID requirement for transactions

### Option 2: PlanetScale (MySQL)
- Pros: Serverless scaling, branching
- Cons: No foreign keys, less JSON support
- Why rejected: Foreign key constraints needed

## References
- https://supabase.com/docs
- Internal discussion: Slack #engineering 2024-01-10
```

## ADR Naming Convention

```
docs/
└── adr/
    ├── 0001-use-postgresql.md
    ├── 0002-authentication-strategy.md
    ├── 0003-api-versioning.md
    └── README.md (index)
```

## When to Write an ADR

- Technology selection (database, framework, cloud)
- Architecture changes (monolith to microservices)
- API design decisions (REST vs GraphQL)
- Security approach (auth method, encryption)
- Integration patterns (sync vs async)
- Breaking changes to existing systems
