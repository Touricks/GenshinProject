# Tech Stack Comparison Reference

## Frontend Frameworks

| Framework | Learning Curve | Performance | Ecosystem | Best For |
|-----------|---------------|-------------|-----------|----------|
| **Next.js** | Medium | Excellent | Large | Full-stack, SSR |
| **React (Vite)** | Medium | Excellent | Large | SPA, custom setup |
| **Vue** | Low | Excellent | Medium | Quick prototypes |
| **Svelte** | Low | Excellent | Growing | Performance-critical |
| **Angular** | High | Good | Large | Enterprise apps |

## Backend Frameworks

| Framework | Language | Performance | Best For |
|-----------|----------|-------------|----------|
| **FastAPI** | Python | Excellent | ML/AI, async APIs |
| **Express** | Node.js | Good | Simple APIs, JS teams |
| **NestJS** | Node.js | Good | Enterprise Node |
| **Django** | Python | Good | Admin-heavy, rapid dev |
| **Go (Gin)** | Go | Excellent | High performance |
| **Rust (Actix)** | Rust | Excellent | Maximum performance |

## Databases

| Database | Type | Scaling | Best For |
|----------|------|---------|----------|
| **PostgreSQL** | Relational | Vertical + Read replicas | General purpose, JSON |
| **MySQL** | Relational | Vertical + Read replicas | Web applications |
| **MongoDB** | Document | Horizontal | Flexible schema |
| **Redis** | Key-Value | Cluster | Caching, sessions |
| **ClickHouse** | Column | Horizontal | Analytics |
| **Supabase** | PostgreSQL + Auth | Managed | Rapid development |
| **PlanetScale** | MySQL | Serverless | Scale MySQL |

## Cloud Platforms

| Platform | Complexity | Cost Model | Best For |
|----------|------------|------------|----------|
| **Vercel** | Low | Per-request | Next.js, static |
| **Railway** | Low | Usage-based | Full-stack |
| **Fly.io** | Medium | Usage-based | Global edge |
| **AWS** | High | Complex | Enterprise scale |
| **GCP** | High | Complex | ML/Data |
| **Azure** | High | Complex | Microsoft ecosystem |

## Auth Solutions

| Solution | Complexity | Cost | Best For |
|----------|------------|------|----------|
| **Supabase Auth** | Low | Free tier | Supabase users |
| **Clerk** | Low | Per-user | Quick integration |
| **Auth0** | Medium | Per-user | Enterprise features |
| **NextAuth.js** | Medium | Free | Next.js custom |
| **Keycloak** | High | Self-hosted | Enterprise, on-prem |

## Decision Matrix Template

```
Feature/Need         | Option A | Option B | Option C
---------------------|----------|----------|----------
Learning curve       | ⭐⭐⭐    | ⭐⭐      | ⭐
Performance          | ⭐⭐      | ⭐⭐⭐    | ⭐⭐⭐
Ecosystem            | ⭐⭐⭐    | ⭐⭐      | ⭐
Team familiarity     | ⭐⭐⭐    | ⭐        | ⭐⭐
Cost                 | ⭐⭐      | ⭐⭐⭐    | ⭐⭐
---------------------|----------|----------|----------
Total                | 13       | 11       | 10
```
