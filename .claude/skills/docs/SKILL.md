---
name: Project Documentation Planner
description: Plan and scaffold engineering documentation at project inception. Use when starting a new project to identify required documentation, create directory structure, and generate templates following Google-style engineering practices. Triggers on "what docs do I need", "set up documentation", "project planning", "doc structure", "documentation scaffold".
---

## Documentation Framework

### Phase-Document Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Product Development Lifecycle                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 0: Ideation     Phase 1: Planning      Phase 2: Design              │
│  ───────────────       ───────────────        ─────────────                │
│  • Problem Statement   • PRD                  • Design Docs                │
│  • One-pager           • User Stories         • ADRs                       │
│                        • Success Metrics      • Data Model                 │
│                                               • API Spec                   │
│                                                                             │
│  Phase 3: Build        Phase 4: Test          Phase 5: Launch              │
│  ─────────────         ─────────────          ─────────────                │
│  • Implementation      • Test Plan            • Launch Checklist           │
│    Plan                • Evaluation           • Runbook                    │
│  • Task Breakdown        Dataset              • Post-mortem Template       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Document Types Reference

| 文档类型 | 英文名称 | 缩写 | 阶段 | 必要性 |
|----------|----------|------|------|--------|
| 产品需求文档 | Product Requirements Document | PRD | Planning | P0 |
| 技术设计文档 | Technical Design Document | TDD / Design Doc | Design | P0 |
| 架构决策记录 | Architecture Decision Record | ADR | Design | P1 |
| 数据模型设计 | Data Model Design | - | Design | P1 |
| API 规范 | API Specification | - | Design | P1 |
| 实施计划 | Implementation Plan | - | Build | P0 |
| 测试计划 | Test Plan | - | Test | P1 |
| 上线检查表 | Launch Checklist | - | Launch | P1 |
| 运维手册 | Runbook | - | Launch | P2 |

---

## Workflow

### Step 1: Project Assessment

Ask the user these questions to determine documentation needs:

```markdown
## Project Assessment Questions

1. **Project Type**: What kind of project is this?
   - [ ] New product/system (full documentation needed)
   - [ ] New feature for existing system (design doc + ADR)
   - [ ] Bug fix / refactor (minimal, maybe ADR)
   - [ ] Research / exploration (one-pager)

2. **Team Size**:
   - [ ] Solo developer (lightweight docs)
   - [ ] Small team (2-5) (standard docs)
   - [ ] Large team (5+) (comprehensive docs)

3. **Duration**:
   - [ ] < 1 week (minimal)
   - [ ] 1-4 weeks (standard)
   - [ ] > 1 month (comprehensive)

4. **Technical Complexity**:
   - [ ] Simple (single component)
   - [ ] Medium (multiple components)
   - [ ] Complex (distributed system / ML)

5. **Key Components** (select all that apply):
   - [ ] Backend API
   - [ ] Frontend UI
   - [ ] Database / Data Storage
   - [ ] ML / AI Model
   - [ ] Data Pipeline
   - [ ] Third-party Integrations
   - [ ] Infrastructure / DevOps
```

### Step 2: Generate Documentation Plan

Based on assessment, recommend documents:

| Project Profile | Recommended Documents |
|-----------------|----------------------|
| **Solo + Simple + Short** | README, Implementation Notes |
| **Small Team + Medium** | PRD, Design Doc, Implementation Plan |
| **Any + Complex** | Full suite (PRD, Design Docs, ADRs, Test Plan) |
| **ML/AI Project** | + Evaluation Dataset Design, Model Card |
| **API Project** | + API Spec (OpenAPI), Integration Guide |

### Step 3: Create Directory Structure

Generate the appropriate structure:

```bash
# Standard Structure (Google Style)
docs/
├── README.md                    # Navigation hub
├── PRD.md                       # Product requirements
├── design/
│   ├── README.md                # Design docs index
│   ├── system-architecture.md   # Overall architecture
│   ├── [component]-design.md    # Component-specific designs
│   └── data-model.md            # Database schema
├── adr/
│   ├── README.md                # ADR index + template
│   └── ADR-001-[topic].md       # Individual decisions
├── project/
│   └── implementation-plan.md   # Task breakdown
└── testing/
    └── test-plan.md             # Testing strategy
```

---

## Document Templates

### PRD Template

```markdown
# Product Requirements Document
# [Product Name]

> Version: 1.0
> Status: Draft | In Review | Approved
> Created: YYYY-MM-DD

## 1. Overview
### 1.1 Vision
### 1.2 Goals & Success Metrics

## 2. User Analysis
### 2.1 User Personas
### 2.2 User Journey

## 3. User Stories
### Epic 1: [Name]
#### US-1.1: [Story Title]

## 4. Functional Requirements
### 4.1 Priority Matrix (P0/P1/P2)
### 4.2 Non-functional Requirements

## 5. Scope
### 5.1 In Scope (MVP)
### 5.2 Out of Scope
### 5.3 Future Scope
```

### Design Doc Template

```markdown
# [Feature/System] Design Document

> Status: Draft | In Review | Approved
> Author: [Name]
> Reviewers: [Names]
> Last Updated: YYYY-MM-DD

## 1. Overview
- Background & Motivation
- Goals and Non-goals

## 2. Current State / Problem
- Existing solutions and their limitations

## 3. Proposed Design
### 3.1 High-level Architecture
### 3.2 Component Design
### 3.3 Data Model
### 3.4 API Design

## 4. Alternatives Considered
| Option | Pros | Cons | Verdict |

## 5. Cross-cutting Concerns
- Security
- Performance
- Scalability
- Observability

## 6. Implementation Plan
- Milestones
- Dependencies
- Risks

## 7. Open Questions
```

### ADR Template

```markdown
# ADR-[NNN]: [Title]

> Status: Proposed | Approved | Deprecated | Superseded
> Created: YYYY-MM-DD
> Deciders: [Names]

## Context
What is the issue we're addressing?

## Decision
What is the change we're proposing?

## Rationale
Why is this the best choice?

## Alternatives Considered
| Alternative | Pros | Cons |

## Consequences
### Positive
### Negative

## References
```

### Implementation Plan Template

```markdown
# Implementation Plan

> Project: [Name]
> Created: YYYY-MM-DD
> Related: PRD.md, design/*.md

## Phase Overview

| Phase | Duration | Goals | Deliverables |
|-------|----------|-------|--------------|

## Detailed Tasks

### Phase 1: [Name]
- [ ] Task 1.1
- [ ] Task 1.2

### Phase 2: [Name]
...

## Dependencies
## Risks & Mitigations
## Progress Tracking
```

---

## Quick Start Commands

After assessment, offer to execute:

```bash
# Create full documentation structure
mkdir -p docs/{design,adr,project,testing}

# Create index files
touch docs/README.md
touch docs/PRD.md
touch docs/design/README.md
touch docs/adr/README.md
touch docs/project/README.md
touch docs/testing/README.md
```

---

## Checklist for Different Project Types

### Web Application
- [ ] PRD with user stories
- [ ] System architecture (frontend + backend)
- [ ] API specification
- [ ] Data model (database schema)
- [ ] Authentication/Authorization ADR
- [ ] Deployment architecture

### ML/AI System
- [ ] PRD with success metrics
- [ ] ML system design (training + inference)
- [ ] Data pipeline design
- [ ] Evaluation dataset specification
- [ ] Model selection ADR
- [ ] Model card / documentation

### Data Pipeline
- [ ] PRD with data requirements
- [ ] Pipeline architecture
- [ ] Data model / schema design
- [ ] Data quality test plan
- [ ] Storage selection ADR

### API/SDK
- [ ] PRD with use cases
- [ ] API design document
- [ ] OpenAPI/Swagger specification
- [ ] SDK design (if applicable)
- [ ] Versioning strategy ADR
- [ ] Integration guide

---

## Output Format

When invoked, provide:

1. **Assessment Summary**: Brief analysis of project needs
2. **Recommended Documents**: Prioritized list with rationale
3. **Directory Structure**: Ready-to-execute commands
4. **Next Steps**: Which document to write first

Example output:

```
## Documentation Plan for [Project Name]

### Assessment
- Type: New ML System
- Complexity: High
- Duration: 4+ weeks

### Recommended Documents (by priority)

| Priority | Document | Rationale |
|----------|----------|-----------|
| P0 | PRD | Define success metrics first |
| P0 | System Architecture | ML + API components |
| P0 | Data Pipeline Design | Core to ML system |
| P1 | Evaluation Dataset | Required for ML validation |
| P1 | ADR: Model Selection | Document Gemini vs Claude decision |
| P2 | Runbook | Post-launch operations |

### Directory Structure
[Generated structure]

### Recommended Order
1. Start with PRD to align on goals
2. Write system architecture for technical direction
3. Create ADRs as you make key decisions
4. Detail component designs in parallel
```
