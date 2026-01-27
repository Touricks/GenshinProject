# CI/CD Patterns Reference

## GitHub Actions Patterns

### Basic Node.js CI

```yaml
name: CI
on: [push, pull_request]

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
      - run: npm run test
      - run: npm run build
```

### Matrix Testing

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci && npm test
```

### Deploy to Vercel

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

### Deploy to Cloud Run

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: app
          region: us-central1
          source: .
```

### Conditional Deployment

```yaml
jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    # ...

  deploy-production:
    if: github.ref == 'refs/heads/main'
    needs: [test, deploy-staging]
    # ...
```

## Pipeline Best Practices

### Fail Fast Order

```
1. Lint (fastest)
2. Type check
3. Unit tests
4. Build
5. Integration tests
6. E2E tests (slowest)
```

### Caching Strategy

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Secrets Management

```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}
```

Never:
- Hardcode secrets
- Log secret values
- Use secrets in PR from forks

### Artifact Storage

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage/
    retention-days: 7
```

## Branch Strategy

### Git Flow

```
main ←── release ←── develop ←── feature/*
                              ←── bugfix/*
```

### Trunk-Based

```
main ←── feature/* (short-lived, < 2 days)
```

### Environment Mapping

| Branch | Environment | Auto-deploy |
|--------|-------------|-------------|
| main | Production | Yes |
| develop | Staging | Yes |
| feature/* | Preview | Optional |
