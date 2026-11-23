# Fleet Control Tower Platform — Master Architecture & Implementation Blueprint

**Project Name:** Fleet Control Tower & Operational Intelligence Platform  
**Target Domain:** Ready Mix Concrete (RMC) Logistics & Heavy Fleet Operations  
**Architecture Author:** Lead Enterprise Solution & Platform Architecture Team  
**Architecture Status:** FROZEN  
**Version:** v1.0.0  
**Lifecycle:** Governing Architecture  

---

> ### ⚠️ Governance Statement
> **This document is the single source of truth for all future implementation work.**  
> Every implementation, code review, pull request, migration, frontend page, backend service, API, worker, dashboard, report, AI component, telemetry component, and database schema MUST strictly comply with this blueprint.  
> **Architectural drift is not permitted** unless an approved Architecture Decision Record (ADR) explicitly updates this document through the formal Architecture Change Process.

---

## Executive Summary & Navigation Index

This Master Architecture Blueprint governs the design, engineering standards, database schema, domain modeling, and deployment topology for the next-generation **Fleet Control Tower Platform**. Built specifically for high-throughput Ready Mix Concrete (RMC) logistics, the platform delivers end-to-end operational visibility, ERP sync pipelines, trip lifecycle tracking, queue & holding analytics, telemetry ingestion, and AI-driven predictive insights.

### Document Roadmap

1. [Executive Vision & Operational Data Principles](#1-executive-vision--operational-data-principles)
2. [Non-Functional Requirements & SLAs](#2-non-functional-requirements--slas)
3. [Architecture Decision Records (ADRs)](#3-architecture-decision-records-adrs)
4. [Architecture Change Management Process](#4-architecture-change-management-process)
5. [High-Level System Architecture](#5-high-level-system-architecture)
6. [Backend Clean Architecture](#6-backend-clean-architecture)
7. [Frontend Feature-Based Modular Architecture](#7-frontend-feature-based-modular-architecture)
8. [Database Architecture & Compatibility Contract](#8-database-architecture--compatibility-contract)
9. [API Design Standards & Standard Envelope](#9-api-design-standards--standard-envelope)
10. [Domain Model & Event Architecture](#10-domain-model--event-architecture)
11. [ERP Integration Subsystem Delivery Strategy](#11-erp-integration-subsystem-delivery-strategy)
12. [Telemetry & Telemetry Replay Engine](#12-telemetry--telemetry-replay-engine)
13. [AI & Operational Intelligence Framework](#13-ai--operational-intelligence-framework)
14. [Security Architecture & RBAC](#14-security-architecture--rbac)
15. [Observability, Logging & Metrics](#15-observability-logging--metrics)
16. [Deployment, Infrastructure & CI/CD](#16-deployment-infrastructure--cicd)
17. [Directory Structure Specification](#17-directory-structure-specification)
18. [End-to-End Vertical Slice Strategy & 25-Step Gate](#18-end-to-end-vertical-slice-strategy--25-step-gate)
19. [Phase & Workstream Governance](#19-phase--workstream-governance)
20. [Platform Acceptance & Signoff Rules](#20-platform-acceptance--signoff-rules)

---

## 1. Executive Vision & Operational Data Principles

Ready Mix Concrete (RMC) is a highly perishable commodity with an operational lifespan of 90–120 minutes from batching to discharge. Unplanned holding times, plant batching bottlenecks, transit delays, and inefficient site queuing drastically increase slump loss, concrete rejection rates, fuel wastage, and customer penalties.

### 1.1 Core Platform Capabilities
* **Control Tower Dashboard & Site Analytics**: Real-time aggregate overview across multiple concrete batching plants, customer job sites, and fleet sub-fleets.
* **ERP Ingestion Subsystem**: Canonical pipeline supporting Excel, CSV, SAP, and REST APIs for batching tickets, dispatch orders, and customer schedules with strict validation.
* **Trip Lifecycle & Digital Twin**: Event-driven tracking of order states: *Scheduled -> Batched -> Loaded -> Departed Plant -> Arrived Site -> Batching/Pouring -> Completed -> Returned*.
* **Queue, Holding & Retention Analytics**: Automated detection of bottlenecks at plant loading queues and site unloading points to charge waiting time penalties accurately.
* **Timeline Replay**: High-resolution playback of vehicle positions, engine telemetry, drum rotation, and status transitions for operational audits.
* **AI Operational Intelligence**: Predictive ETA models, slump loss risk estimation, intelligent site dispatch throttle recommendations, and automated feedback loops.

---

## 2. Non-Functional Requirements & SLAs

| Category | Requirement Target | Enforcement Mechanism |
| :--- | :--- | :--- |
| **API Latency (p95)** | < 100 ms for operational REST endpoints | Redis caching, indexed SQL queries, DB connection pooling |
| **Telemetry Throughput** | 10,000 events/sec burst ingestion | Async background ingestion worker, batch DB inserts |
| **Availability Target** | 99.95% Uptime | Multi-container Linux deployment, health probes, zero-downtime migrations |
| **Data Retention** | 7 years operational audit log retention | PostgreSQL partitioning by month/year |
| **Frontend FPS** | 60 FPS under continuous canvas updates | Canvas-based rendering, optimized TanStack Query caching |

---

## 3. Architecture Decision Records (ADRs)

### ADR 001: Backend Framework — FastAPI with Python 3.13+
* **Decision**: Adopt FastAPI and Python 3.13+ for the core application server.
* **Rationale**: High performance async I/O via `asyncio` and Pydantic v2 validation. Python's ecosystem seamlessly bridges backend domain logic with future AI/ML pipelines (PyTorch/Scikit-learn/Polars).

### ADR 002: Database Engine — PostgreSQL 16+ & pgcrypto UUID Strategy
* **Decision**: Strictly PostgreSQL 16+ with `pgcrypto` (`gen_random_uuid()`) and PostGIS. SQLite is strictly prohibited in dev/staging/prod. Deprecate `uuid-ossp` in favor of `pgcrypto` for faster native UUID generation.
* **Rationale**: Native JSONB support, PostGIS spatial indexing for fleet geofences, row-level locking, robust partitioning for millions of dispatch records, and Alembic compatibility.

### ADR 003: Core State & Async Processing — Redis & Taskiq
* **Decision**: Use Redis for distributed caching, web-socket pub/sub, and background job queuing.
* **Rationale**: Prevents long-running ERP parses or report generations from blocking API request-response loops.

---

## 8. Database Architecture & Compatibility Contract

### 8.1 Database Compatibility Contract (Mandatory)
Future ERP, AI, Telemetry, and Analytics modules **MUST ONLY** depend on the public database infrastructure defined in Workstream 0.2.
Downstream modules **MAY NOT**:
* Modify `BaseEntity`, `AuditEntity`, or `VersionedEntity` definitions.
* Modify the `UnitOfWork` async transaction lifecycle or repository interfaces.
* Bypass session context managers to invoke inline `session.commit()` calls.
* Modify core database conventions without an approved Architecture Decision Record (ADR).

---

## 17. Directory Structure Specification

```
fleet-operational-intelligence-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   │   ├── database.py
│   │   │   ├── exceptions.py
│   │   │   └── config.py
│   │   ├── domain/
│   │   ├── services/
│   │   ├── models/
│   │   │   └── base.py
│   │   ├── repositories/
│   │   │   └── base.py
│   │   └── schemas/
│   ├── alembic/
│   └── tests/
├── frontend/
└── scripts/
```

---
**Approved By:** Lead Architecture & Platform Engineering Board  
**Document Revision:** 1.0.0 (Governing Architecture Baseline — FROZEN)
