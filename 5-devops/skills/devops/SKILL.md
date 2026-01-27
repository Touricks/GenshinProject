---
name: devops
description: CI/CD pipelines, containerization, cloud deployment, and infrastructure management. Use when setting up CI/CD, configuring Docker, deploying to cloud platforms (AWS, GCP, Vercel, Railway), setting up monitoring and alerting, or managing infrastructure. Triggers on "deploy", "CI/CD", "Docker", "kubernetes", "monitoring", "infrastructure".
---

# DevOps Skill

Automate build, test, deploy, and monitor workflows.

## Workflow

```
1. Containerize → 2. CI/CD → 3. Deploy → 4. Monitor → 5. Iterate
```

### Step 1: Containerization

**Dockerfile Best Practices**:

```dockerfile
# Multi-stage build for smaller images
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

**Docker Compose** (local dev):

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/app
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

### Step 2: CI/CD Pipeline

**GitHub Actions** (recommended):

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run test -- --coverage
      - run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Deploy steps here
```

**CI Pipeline Stages**:

| Stage | Purpose | Fail Fast |
|-------|---------|-----------|
| Lint | Code style | Yes |
| Type Check | TypeScript errors | Yes |
| Unit Tests | Logic correctness | Yes |
| Build | Compilation | Yes |
| Integration Tests | API contracts | Yes |
| E2E Tests | User flows | Optional |
| Security Scan | Vulnerabilities | Warn |
| Deploy | Release | - |

### Step 3: Deployment Platforms

**Platform Selection**:

| Platform | Best For | Complexity |
|----------|----------|------------|
| **Vercel** | Next.js, static sites | Low |
| **Railway** | Full-stack, databases | Low |
| **Fly.io** | Global edge, containers | Medium |
| **AWS ECS** | Enterprise, scale | High |
| **GCP Cloud Run** | Serverless containers | Medium |
| **Kubernetes** | Multi-cloud, complex | High |

**Vercel Deployment**:

```bash
# Install CLI
npm i -g vercel

# Deploy
vercel --prod
```

**Railway Deployment**:

```bash
# Install CLI
npm i -g @railway/cli

# Deploy
railway up
```

**Cloud Run (GCP)**:

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT/app

# Deploy
gcloud run deploy app \
  --image gcr.io/PROJECT/app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Step 4: Environment Management

**Environment Variables**:

```bash
# .env.example (committed)
DATABASE_URL=
REDIS_URL=
API_KEY=

# .env.local (gitignored)
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
API_KEY=sk-...
```

**Secrets Management**:

| Method | Use Case |
|--------|----------|
| Platform secrets | Vercel, Railway, Fly.io |
| AWS Secrets Manager | AWS infrastructure |
| GCP Secret Manager | GCP infrastructure |
| HashiCorp Vault | Multi-cloud, enterprise |
| 1Password/Doppler | Team sharing |

### Step 5: Monitoring & Observability

**Three Pillars**:

| Pillar | Tools | Purpose |
|--------|-------|---------|
| **Logs** | Loki, CloudWatch | Debug, audit |
| **Metrics** | Prometheus, DataDog | Performance |
| **Traces** | Jaeger, Tempo | Request flow |

**Basic Health Check Endpoint**:

```typescript
// GET /health
app.get('/health', async (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    checks: {
      database: await checkDatabase(),
      redis: await checkRedis(),
    }
  }

  const isHealthy = Object.values(health.checks)
    .every(c => c === 'ok')

  res.status(isHealthy ? 200 : 503).json(health)
})
```

**Alerting Rules**:

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Error rate | > 1% | Critical |
| Latency p99 | > 2s | Warning |
| CPU usage | > 80% | Warning |
| Memory usage | > 85% | Critical |
| Disk usage | > 90% | Critical |

## Deployment Checklist

```markdown
## Pre-Deployment
- [ ] All tests passing
- [ ] Build succeeds locally
- [ ] Environment variables documented
- [ ] Secrets configured in platform
- [ ] Database migrations ready
- [ ] Rollback plan documented

## Deployment
- [ ] Deploy to staging first
- [ ] Smoke test staging
- [ ] Deploy to production
- [ ] Verify health endpoints
- [ ] Check error rates

## Post-Deployment
- [ ] Monitor for 15 minutes
- [ ] Check key metrics
- [ ] Notify team
- [ ] Update documentation
```

## Infrastructure as Code

**Terraform** (example):

```hcl
# main.tf
resource "aws_ecs_service" "app" {
  name            = "app-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 3000
  }
}
```

## Anti-Patterns

- **Manual deployments** → Error-prone, not reproducible
- **No staging environment** → Production surprises
- **Secrets in code** → Security breach
- **No rollback plan** → Extended outages
- **Alert fatigue** → Missed critical alerts

## References

For detailed guides, see:
- `references/ci-cd-patterns.md` - Pipeline examples
- `references/docker-patterns.md` - Container best practices
- `references/cloud-deploy.md` - Platform-specific guides

## Related Skills

- `system-design` - Architecture decisions (Phase 2)
- `security-review` - Security scanning
- `verification-loop` - Pre-deploy checks
