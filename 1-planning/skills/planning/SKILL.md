---
name: planning
description: Requirements analysis and project planning for new features or applications. Use when analyzing requirements, creating user stories, defining acceptance criteria, scoping MVP, estimating effort, or identifying risks. Triggers on "plan a feature", "analyze requirements", "create user stories", "what should we build".
---

# Planning Skill

Transform vague requirements into clear, actionable development plans.

## Workflow

```
1. Understand → 2. Define → 3. Scope → 4. Estimate → 5. Document
```

### Step 1: Understand the Problem

Use **5W1H** framework:

| Question | Purpose |
|----------|---------|
| **What** | Core functionality needed |
| **Who** | Target users and stakeholders |
| **Why** | Business value and goals |
| **When** | Timeline and deadlines |
| **Where** | Deployment environment |
| **How** | High-level approach |

Ask clarifying questions before proceeding.

### Step 2: Define User Stories

Format:
```
As a [user type]
I want to [action]
So that [benefit]
```

Example:
```
As a registered user
I want to reset my password via email
So that I can regain access to my account
```

### Step 3: Define Acceptance Criteria

Use **Given-When-Then** format:

```
Given [precondition]
When [action]
Then [expected result]
```

Example:
```
Given I am on the login page
When I click "Forgot Password" and enter my email
Then I receive a password reset link within 5 minutes
```

### Step 4: Scope Definition

**MVP Scoping Matrix**:

| Feature | Must Have | Should Have | Nice to Have |
|---------|-----------|-------------|--------------|
| Core auth | ✅ | | |
| Social login | | ✅ | |
| 2FA | | | ✅ |

**MVP Criteria**:
- Solves the core problem
- Minimal but complete
- Shippable to real users

### Step 5: Risk Identification

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limits | Medium | High | Implement caching |
| Scope creep | High | Medium | Strict MVP definition |

### Step 6: Effort Estimation

Use **T-shirt sizing**:

| Size | Typical Duration | Complexity |
|------|------------------|------------|
| XS | < 2 hours | Single function |
| S | 2-4 hours | Single component |
| M | 1-2 days | Multiple components |
| L | 3-5 days | Feature with tests |
| XL | 1-2 weeks | Major feature |

## Output Template

```markdown
# Project Plan: [Name]

## Overview
[1-2 sentence summary]

## User Stories
1. As a... I want... So that...
2. ...

## Acceptance Criteria
- [ ] Given... When... Then...
- [ ] ...

## Scope
### MVP (Phase 1)
- Feature A
- Feature B

### Phase 2
- Feature C

## Risks
| Risk | Mitigation |
|------|------------|
| ... | ... |

## Estimates
| Story | Size | Notes |
|-------|------|-------|
| ... | M | ... |

## Next Steps
1. Technical design (/system-design)
2. ...
```

## Anti-Patterns

- **Skipping requirements** → Leads to rework
- **Gold plating** → Over-engineering before validation
- **Vague acceptance criteria** → Disputes about "done"
- **No risk assessment** → Surprises during development

## Related Skills

- `system-design` - Technical architecture (Phase 2)
- `tdd-workflow` - Test definition aligns with acceptance criteria
- `eval-harness` - Formal evaluation criteria
