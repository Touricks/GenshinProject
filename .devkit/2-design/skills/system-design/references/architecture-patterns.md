# Architecture Patterns Reference

## Monolith

**Structure**:
```
app/
├── src/
│   ├── controllers/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── config/
├── tests/
└── package.json
```

**Pros**: Simple deployment, easy debugging, lower latency
**Cons**: Scaling entire app, deployment coupling, tech lock-in

**Best for**: MVP, small teams (< 5 developers), simple domain

## Modular Monolith

**Structure**:
```
app/
├── modules/
│   ├── auth/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── models/
│   ├── billing/
│   └── notifications/
├── shared/
└── package.json
```

**Pros**: Clear boundaries, easier extraction to microservices
**Cons**: Discipline required, shared database

**Best for**: Growing applications, preparing for microservices

## Microservices

**Structure**:
```
services/
├── auth-service/
├── billing-service/
├── notification-service/
└── api-gateway/
```

**Pros**: Independent scaling, team autonomy, polyglot
**Cons**: Operational complexity, network latency, distributed debugging

**Best for**: Large teams, independent scaling needs, >10 developers

## Serverless

**Structure**:
```
functions/
├── api/
│   ├── users.ts
│   └── orders.ts
├── workers/
│   └── process-payment.ts
└── serverless.yml
```

**Pros**: Auto-scaling, pay-per-use, no server management
**Cons**: Cold starts, vendor lock-in, debugging difficulty

**Best for**: Variable load, event-driven, cost optimization

## Event-Driven Architecture

**Components**:
- Event producers
- Event bus (Kafka, RabbitMQ, SNS/SQS)
- Event consumers

**Patterns**:
- Event Sourcing: Store state as event sequence
- CQRS: Separate read/write models
- Saga: Distributed transactions

**Best for**: Decoupled systems, audit requirements, eventual consistency OK
