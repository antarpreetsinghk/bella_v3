# 📦 Bella V3 Package-Level Architecture

## Overview

Bella V3 follows a modular package-based architecture with comprehensive CloudWatch monitoring at each layer. This document outlines the package structure, dependencies, and monitoring integration.

## 🏗️ Package Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         🔍 CloudWatch Monitoring Layer                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │   📊 Metrics    │ │   📋 Logs       │ │      🚨 Alarms             │ │
│  │   Collection    │ │   Aggregation   │ │   & Notifications         │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                            🌐 Application Layer                        │
│                                                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │   📱 API        │ │   👥 Admin      │ │      🏠 Home                │ │
│  │   Routes        │ │   Dashboard     │ │   & Health                  │ │
│  │                 │ │                 │ │                             │ │
│  │ • /twilio/*     │ │ • /admin/*      │ │ • /                         │ │
│  │ • /appointments │ │ • Authentication│ │ • /healthz                  │ │
│  │ • /users        │ │ • Data Views    │ │ • /metrics                  │ │
│  │ • /assistant    │ │ • Export Tools  │ │                             │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
│           │                   │                         │               │
└─────────────────────────────────────────────────────────────────────────┘
            │                   │                         │
┌─────────────────────────────────────────────────────────────────────────┐
│                          🧠 Business Logic Layer                       │
│                                                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │   🤖 Services   │ │   📋 Core       │ │      🗃️ CRUD               │ │
│  │   Package       │ │   Package       │ │   Operations                │ │
│  │                 │ │                 │ │                             │ │
│  │ • LLM Service   │ │ • Config        │ │ • User CRUD                 │ │
│  │ • Canadian NLP  │ │ • Metrics       │ │ • Appointment CRUD          │ │
│  │ • Booking       │ │ • Logging       │ │ • Session Management        │ │
│  │ • Google Cal    │ │ • Business Rules│ │                             │ │
│  │ • Alerting      │ │ • Performance   │ │                             │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
│           │                   │                         │               │
└─────────────────────────────────────────────────────────────────────────┘
            │                   │                         │
┌─────────────────────────────────────────────────────────────────────────┐
│                           💾 Data Layer                                │
│                                                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │   🗄️ Database   │ │   📊 Models     │ │      🔄 Session             │ │
│  │   Package       │ │   Package       │ │   Management                │ │
│  │                 │ │                 │ │                             │ │
│  │ • PostgreSQL    │ │ • User Model    │ │ • Database Sessions         │ │
│  │ • Connection    │ │ • Appointment   │ │ • Redis Cache               │ │
│  │ • Migration     │ │ • Base Classes  │ │ • Dashboard Sessions        │ │
│  │ • Health Check  │ │ • Relationships │ │                             │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
            │                   │                         │
┌─────────────────────────────────────────────────────────────────────────┐
│                        🌍 External Integration Layer                   │
│                                                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │   📞 Twilio     │ │   🤖 OpenAI     │ │      ☁️ AWS                 │ │
│  │   Voice API     │ │   GPT-4 API     │ │   Infrastructure            │ │
│  │                 │ │                 │ │                             │ │
│  │ • Voice Calls   │ │ • NLP Processing│ │ • ECS Fargate               │ │
│  │ • Speech-to-Text│ │ • Canadian Ext. │ │ • RDS PostgreSQL            │ │
│  │ • Call Routing  │ │ • Artifact Filter│ │ • CloudWatch Monitoring     │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📦 Package Details

### 1. API Package (`app/api/`)

**Namespace**: `Bella/API`

**Responsibilities**:
- RESTful API endpoints
- Request/response handling
- Authentication middleware
- Route organization

**Key Modules**:
```
app/api/
├── routes/
│   ├── twilio.py           # Voice webhook handling
│   ├── appointments.py     # Appointment management
│   ├── users.py           # User management
│   ├── assistant.py       # AI booking endpoints
│   ├── admin_dashboard.py # Admin interface
│   └── home.py           # Health & metrics
├── auth.py               # Authentication logic
└── __init__.py          # API configuration
```

**CloudWatch Metrics**:
- `RequestCount` - Total API requests
- `ResponseTime` - Average response latency
- `ErrorRate` - HTTP error percentage
- `TwilioWebhookLatency` - Voice processing time
- `AdminLoginCount` - Dashboard access tracking

**Dependencies**: → Services, Core, CRUD, Database

---

### 2. Services Package (`app/services/`)

**Namespace**: `Bella/Services`

**Responsibilities**:
- External API integrations
- Business service implementations
- AI/ML processing services
- Caching and optimization

**Key Modules**:
```
app/services/
├── llm.py                    # OpenAI GPT-4 integration
├── canadian_extraction.py   # Canadian-specific NLP
├── booking.py               # Appointment booking logic
├── google_calendar.py       # Calendar integration
├── alerting.py              # Production alerting
├── business_metrics.py      # Business KPI tracking
├── cost_optimization.py     # AWS cost management
├── circuit_breaker.py       # Fault tolerance
├── whisper_stt.py          # Speech-to-text processing
└── session.py              # Session management
```

**CloudWatch Metrics**:
- `OpenAIAPILatency` - AI processing time
- `OpenAITokenUsage` - Token consumption tracking
- `ExtractionAccuracy` - Name/phone extraction success
- `CalendarIntegrationLatency` - Google Calendar response time
- `CacheHitRate` - Redis cache performance
- `ArtifactFilteringEffectiveness` - Speech artifact removal

**Dependencies**: → Core, Database, External APIs

---

### 3. Core Package (`app/core/`)

**Namespace**: `Bella/Core`

**Responsibilities**:
- Application configuration
- Logging and metrics infrastructure
- Business rule enforcement
- Performance monitoring

**Key Modules**:
```
app/core/
├── config.py          # Environment configuration
├── logging.py         # Structured logging setup
├── metrics.py         # Performance metrics collection
├── business.py        # Business rules & validation
├── performance.py     # Performance monitoring
└── errors.py         # Error handling & types
```

**CloudWatch Metrics**:
- `SystemHealth` - Overall system status
- `BusinessRuleViolations` - Rule enforcement failures
- `ConfigurationErrors` - Config validation issues
- `PerformanceDegradation` - System slowdown detection
- `CircuitBreakerState` - Fault tolerance status

**Dependencies**: → Database (config only)

---

### 4. Database Package (`app/db/`)

**Namespace**: `Bella/Database`

**Responsibilities**:
- Database connection management
- Data model definitions
- Migration handling
- Health monitoring

**Key Modules**:
```
app/db/
├── models/
│   ├── user.py           # User data model
│   └── appointment.py    # Appointment data model
├── base.py              # Database configuration
└── session.py          # Connection management
```

**CloudWatch Metrics**:
- `ConnectionPoolUsage` - Database connection utilization
- `QueryLatency` - SQL query response time
- `TransactionCount` - Database transaction volume
- `DatabaseErrors` - Connection/query failures
- `MigrationStatus` - Schema migration health

**Dependencies**: → PostgreSQL RDS

---

### 5. CRUD Package (`app/crud/`)

**Namespace**: `Bella/CRUD`

**Responsibilities**:
- Data access layer implementation
- Database operation abstraction
- Query optimization
- Data validation

**Key Modules**:
```
app/crud/
├── user.py           # User database operations
└── appointment.py    # Appointment database operations
```

**CloudWatch Metrics**:
- `CRUDOperationLatency` - Database operation time
- `DataValidationErrors` - Input validation failures
- `QueryOptimizationImpact` - Performance improvements

**Dependencies**: → Database, Models

---

### 6. Schemas Package (`app/schemas/`)

**Namespace**: `Bella/Schemas`

**Responsibilities**:
- API request/response validation
- Data serialization
- Type safety enforcement

**Key Modules**:
```
app/schemas/
├── user.py           # User API schemas
├── appointment.py    # Appointment API schemas
└── assistant.py      # AI booking schemas
```

**CloudWatch Metrics**:
- `SchemaValidationErrors` - Input validation failures
- `SerializationLatency` - Data conversion time

**Dependencies**: → None (pure validation)

---

## 🔄 Package Interaction Flow

### Voice Booking Flow
```
📞 Twilio Call → API/twilio.py → Services/llm.py → Services/canadian_extraction.py
                      ↓
CRUD/appointment.py → Database/models → Services/google_calendar.py
                      ↓
CloudWatch Metrics → Core/metrics.py → Services/alerting.py
```

### Admin Dashboard Flow
```
🌐 Admin User → API/admin_dashboard.py → CRUD/user.py & CRUD/appointment.py
                      ↓
Database/session.py → Database/models → Core/logging.py
                      ↓
CloudWatch Metrics → Services/business_metrics.py
```

### Health Monitoring Flow
```
⚕️ Health Check → API/home.py → Core/metrics.py → Database/base.py
                      ↓
Services/alerting.py → CloudWatch Alarms → SNS Notifications
```

## 📊 CloudWatch Integration Architecture

### Metric Collection Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Package       │───▶│   Core/Metrics  │───▶│   CloudWatch    │
│   Operations    │    │   Collector     │    │   Namespace     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                       │
                                │                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Services/     │───▶│   Background    │    │   Alarms &      │
│   Alerting      │    │   Worker        │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Log Aggregation Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Package       │───▶│   Core/Logging  │───▶│   CloudWatch    │
│   Operations    │    │   Structured    │    │   Log Groups    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                       │
                                │                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Correlation   │    │   Request       │    │   Log Insights  │
│   IDs           │    │   Context       │    │   Queries       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚨 Monitoring & Alerting Strategy

### Package-Level Alarms

**Critical Alarms** (Immediate Response):
- API error rate > 5%
- Database connection pool > 80%
- OpenAI API latency > 5s
- Speech recognition accuracy < 85%

**Warning Alarms** (Investigation Required):
- API response time > 2s
- Cache hit rate < 70%
- Name extraction accuracy < 90%
- Session creation failures

**Info Alarms** (Trend Monitoring):
- Call volume changes > 50%
- Token usage increase > 30%
- Dashboard load time > 1s

### Dashboard Organization

**Executive Dashboard**:
- Overall system health
- Business KPIs
- Cost metrics
- SLA status

**Technical Dashboard**:
- Package-level metrics
- Error rates by component
- Performance trends
- Resource utilization

**Operations Dashboard**:
- Active alerts
- Deployment status
- Infrastructure health
- Security events

## 🔧 Development Best Practices

### Package Design Principles

1. **Single Responsibility**: Each package has one clear purpose
2. **Dependency Inversion**: Higher-level packages depend on abstractions
3. **Monitoring First**: All operations generate metrics and logs
4. **Error Handling**: Graceful degradation with proper alerting
5. **Configuration**: Environment-aware with validation

### Monitoring Implementation

1. **Instrument Everything**: Every function that matters gets metrics
2. **Contextual Logging**: Correlation IDs and structured data
3. **Alert on Symptoms**: Monitor user-facing impacts, not just technical metrics
4. **Dashboard Hierarchy**: Different views for different audiences
5. **Runbook Automation**: Alerts include remediation steps

### Testing Strategy

1. **Unit Tests**: Individual package component testing
2. **Integration Tests**: Package interaction validation
3. **Performance Tests**: Monitoring system validation
4. **Chaos Engineering**: Fault injection and recovery testing

## 📈 Scaling Considerations

### Horizontal Scaling
- Stateless package design enables container scaling
- Database connection pooling manages resource limits
- Cache layers reduce database load

### Monitoring Scaling
- CloudWatch metrics auto-scale with usage
- Log retention policies manage storage costs
- Alert suppression prevents notification storms

### Performance Optimization
- Package-level caching strategies
- Database query optimization
- External API circuit breakers
- Resource pool management

## 🔒 Security Architecture

### Package-Level Security
- API authentication at entry points
- Service-to-service authentication
- Database connection encryption
- Secrets management through environment variables

### Monitoring Security
- Access logs for audit trails
- Security event alerting
- Anomaly detection for unusual patterns
- Compliance reporting capabilities

---

This package-level architecture provides a scalable, maintainable, and observable foundation for Bella V3's AI-powered dental appointment system.