# Cloud Deployment Reference

## Vercel

**Best for**: Next.js, static sites, serverless functions

### Setup

```bash
npm i -g vercel
vercel login
vercel link
```

### Deploy

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

### Configuration (vercel.json)

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    "DATABASE_URL": "@database-url"
  }
}
```

### Environment Variables

```bash
vercel env add DATABASE_URL production
vercel env pull .env.local
```

---

## Railway

**Best for**: Full-stack apps, databases, Redis

### Setup

```bash
npm i -g @railway/cli
railway login
railway init
```

### Deploy

```bash
railway up
```

### Configuration (railway.json)

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/health"
  }
}
```

### Database

```bash
railway add --database postgres
railway connect postgres
```

---

## Fly.io

**Best for**: Global edge deployment, containers

### Setup

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch
```

### Deploy

```bash
fly deploy
```

### Configuration (fly.toml)

```toml
app = "my-app"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 3000
  force_https = true

[[services]]
  internal_port = 3000
  protocol = "tcp"

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

### Scaling

```bash
fly scale count 3
fly scale vm shared-cpu-2x
```

---

## Google Cloud Run

**Best for**: Serverless containers, auto-scaling

### Setup

```bash
gcloud auth login
gcloud config set project PROJECT_ID
```

### Deploy

```bash
# From source
gcloud run deploy SERVICE \
  --source . \
  --region us-central1

# From container
gcloud run deploy SERVICE \
  --image gcr.io/PROJECT/IMAGE \
  --region us-central1 \
  --allow-unauthenticated
```

### Configuration

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
        - image: gcr.io/PROJECT/IMAGE
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: "1"
              memory: "512Mi"
```

---

## AWS ECS (Fargate)

**Best for**: Enterprise, existing AWS infrastructure

### Task Definition

```json
{
  "family": "my-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "xxx.dkr.ecr.region.amazonaws.com/app:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Deploy with Copilot

```bash
copilot init
copilot deploy
```

---

## Comparison Matrix

| Feature | Vercel | Railway | Fly.io | Cloud Run | ECS |
|---------|--------|---------|--------|-----------|-----|
| Setup time | 5 min | 5 min | 10 min | 15 min | 30+ min |
| Databases | ❌ | ✅ | ✅ | ❌ | ❌ |
| Edge | ✅ | ❌ | ✅ | ❌ | ❌ |
| Custom Docker | ❌ | ✅ | ✅ | ✅ | ✅ |
| Free tier | ✅ | ✅ | ✅ | ✅ | Limited |
| Enterprise | ✅ | ❌ | ❌ | ✅ | ✅ |
