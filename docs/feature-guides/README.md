# VisualSprint Feature Guides

This folder is a learning map for the VisualSprint codebase.

It is written for a developer who built parts of the product with agents and later wants to understand how the whole system works from code, contracts, APIs, and deployment wiring.

Use these guides when you want to answer:

- what each feature does
- which files implement it
- which API routes and methods are involved
- how frontend state moves through the backend
- where deterministic services stop and agents begin
- how Elastic memory, reports, actions, and deployment fit together

## How To Read These Guides

Start with [system-overview.md](./system-overview.md), then read the feature area you are working on.

Recommended order:

1. [System overview](./system-overview.md)
2. [Meeting lifecycle](./meeting-lifecycle.md)
3. [Browser capture pipeline](./browser-capture-pipeline.md)
4. [Live workspace and frontend state](./live-workspace-and-frontend.md)
5. [Agent runtime and ADK agents](./agent-runtime-and-adk-agents.md)
6. [Elastic memory and knowledge search](./elastic-memory-and-search.md)
7. [Final reports and action recommendations](./reports-and-actions.md)
8. [Contracts and data models](./contracts-and-data-models.md)
9. [Deployment and configuration](./deployment-and-configuration.md)
10. [Testing and debugging](./testing-and-debugging.md)

## Main Architecture In One Page

VisualSprint is a meeting-intelligence product.

The product captures browser meeting activity, turns chunks into transcript and screen context, reasons over that context with agents, writes durable meeting outputs, indexes historical outcomes into Elastic, and generates a final report plus approval-based action recommendations.

The main code boundaries are:

- `apps/web`: Next.js frontend, browser capture UI, live workspace, report, actions, and knowledge search.
- `services/api`: FastAPI control plane. It owns deterministic meeting state, capture lifecycle, persistence, report assembly, Elastic write-back, and action approval/execution.
- `services/agents`: FastAPI adapter for reasoning, summary, and action agents. It can run local fallbacks or call configured Google-managed runtimes.
- `services/ingest`: Upload reservation and transcript-processing boundary.
- `services/media`: Media-processing and screen-event boundary.
- `packages/contracts`: Shared TypeScript contracts used by the frontend and mirrored by Python Pydantic models.
- `infra/cloud-run`: Cloud Run service definitions and deployment helpers.

## The Most Important Rule

The agent is not the whole product.

The API service is the deterministic control plane. The agents should reason over already-assembled context and return structured outputs. The API decides when to persist, index, finalize, approve, and execute.

That separation is what keeps the system understandable.
