---
name: system-design
description: System architecture and technical design for software projects. Use when selecting tech stack, designing architecture, making technical decisions, creating ADRs, drawing system diagrams, or planning data models. Triggers on "design the system", "choose tech stack", "architecture decision", "draw diagram".
---

# System Design Skill

Define system architecture, select technologies, and document design decisions.

## Workflow

```
1. Requirements → 2. Constraints → 3. Tech Stack → 4. Architecture → 5. Document
```

### Step 1: Gather Technical Requirements

From planning phase, extract:

| Aspect | Questions |
|--------|-----------|
| **Scale** | Users? Requests/sec? Data volume? |
| **Performance** | Latency requirements? Throughput? |
| **Reliability** | Uptime SLA? Disaster recovery? |
| **Security** | Auth requirements? Compliance? |
| **Budget** | Infrastructure budget? Team size? |

### Step 2: Identify Constraints

| Constraint Type | Examples |
|-----------------|----------|
| **Technical** | Existing systems, required integrations |
| **Organizational** | Team expertise, timeline |
| **Regulatory** | GDPR, HIPAA, SOC2 |
| **Budget** | Cloud costs, licensing |

### Step 3: Tech Stack Selection

**Selection Framework**:

```
For each component:
1. List requirements
2. Identify 2-3 options
3. Evaluate trade-offs
4. Document decision (ADR)
```

**Common Stack Patterns**:

| Pattern | Stack | Best For |
|---------|-------|----------|
| **Full-Stack JS** | Next.js + Node + PostgreSQL | Rapid development, small teams |
| **Python Backend** | FastAPI + React + PostgreSQL | ML/AI integration, data processing |
| **Enterprise** | Spring + React + Oracle | Large teams, complex business logic |
| **Serverless** | Lambda + DynamoDB + CloudFront | Variable load, cost optimization |

### Step 4: Architecture Design

**Architecture Patterns**:

| Pattern | When to Use |
|---------|-------------|
| **Monolith** | MVP, small team, simple domain |
| **Modular Monolith** | Growing complexity, single deployment |
| **Microservices** | Independent scaling, large teams |
| **Serverless** | Event-driven, variable load |

**C4 Model Levels**:

```
Level 1: System Context - External systems and users
Level 2: Container - Major deployable units
Level 3: Component - Internal structure
Level 4: Code - Class/function level (optional)
```

### Step 5: Data Model Design

**Entity Identification**:
1. Extract nouns from user stories
2. Define relationships
3. Identify attributes
4. Normalize appropriately

**Schema Considerations**:
- Primary keys (UUID vs auto-increment)
- Indexing strategy
- Soft delete vs hard delete
- Audit fields (created_at, updated_at)

## ADR Template

```markdown
# ADR-001: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[Why is this decision needed?]

## Decision
[What is the decision?]

## Consequences

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Alternatives Considered
1. [Alternative 1]: [Why rejected]
2. [Alternative 2]: [Why rejected]
```

## Output Template

```markdown
# System Design: [Project Name]

## Technical Requirements
- Scale: [X users, Y requests/sec]
- Performance: [latency requirements]
- Reliability: [uptime SLA]

## Architecture Overview

[ASCII diagram or description]

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js | SSR, React ecosystem |
| Backend | FastAPI | Performance, Python ML |
| Database | PostgreSQL | ACID, JSON support |
| Cache | Redis | Session, hot data |
| Queue | Redis/BullMQ | Background jobs |

## Data Model

### Core Entities
- User (id, email, name, created_at)
- Project (id, user_id, name, status)
- ...

### Key Relationships
- User 1:N Project
- ...

## ADRs
- ADR-001: [Link to decision]
- ...

## Next Steps
1. Set up project structure
2. Implement data models
3. Create API skeleton
```

## Diagram Patterns

**System Context (ASCII)**:
```
┌─────────┐     ┌──────────────┐     ┌─────────┐
│  User   │────▶│   System     │────▶│ External│
│ Browser │◀────│   Backend    │◀────│   API   │
└─────────┘     └──────────────┘     └─────────┘
```

**Container Diagram (ASCII)**:
```
┌───────────────────────────────────────────────┐
│                   System                       │
├─────────────────┬─────────────────────────────┤
│    Frontend     │         Backend             │
│   (Next.js)     │        (FastAPI)            │
│                 │                             │
│  ┌───────────┐  │  ┌───────────┐ ┌─────────┐ │
│  │  Pages    │  │  │  Routers  │ │ Services│ │
│  │  Comps    │  │  │  Models   │ │ Workers │ │
│  └───────────┘  │  └───────────┘ └─────────┘ │
└─────────────────┴─────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────┐       ┌─────────────┐
│  PostgreSQL │       │    Redis    │
└─────────────┘       └─────────────┘
```

## Anti-Patterns

- **Resume-driven development** → Choose tech for learning, not fit
- **Over-engineering** → Microservices for MVP
- **No documentation** → Decisions lost over time
- **Ignoring constraints** → Budget/timeline surprises

## References

For detailed patterns, see:
- `references/architecture-patterns.md` - Common architecture patterns
- `references/tech-stack-comparison.md` - Technology comparisons
- `references/adr-template.md` - ADR examples

## Related Skills

- `planning` - Requirements input (Phase 1)
- `backend-patterns` - Implementation patterns (Phase 3)
- `frontend-patterns` - UI architecture (Phase 4)
- `devops` - Deployment architecture (Phase 5)
