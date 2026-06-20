# VisualSprint

VisualSprint is a meeting-intelligence agent for engineering teams. It captures live meeting audio and shared-screen context, reasons across the conversation with Gemini, checks organizational memory across past meetings through Elastic, and produces structured outputs: decisions, commitments, blockers, open questions, and a final evidence-backed report.

The product goal is not a better transcript. The goal is a trustworthy system of record for what the team actually decided, why, who owns the follow-up, and whether the same problem has appeared before.

> **Hackathon:** Built new for the **Google Cloud Rapid Agent Hackathon**, **Elastic** partner track. Powered by **Gemini 3** + **Google Cloud Agent Builder**, integrating the **Elastic MCP server**. Runs on the **web** platform. Submission deadline **June 11, 2026, 2:00 PM PDT**.

---

## Centerpiece

The **post-meeting evidence-backed report is the hero deliverable.** The live dashboard is a supporting proof surface that shows the report assembling in real time. This ordering keeps the live path simple (push deltas as they are produced) while the report path owns correctness and completeness. Every design decision below favors report trustworthiness.

---

## Mandatory Rules Compliance

Every hard requirement from the official [rules](https://rapid-agent.devpost.com/rules), mapped to how VisualSprint satisfies it.

| Mandatory rule | How VisualSprint complies |
| --- | --- |
| Functional agent **powered by Gemini and Google Cloud Agent Builder** | Orchestrator/Reasoning Agent and Summary Agent built in Google Agent Builder, reasoning on **Gemini 3**, with an optional approval-based action review layer for downstream suggestions. |
| Integrates a **partner MCP server** | Memory retrieval runs through the **Elastic MCP server** (Elastic Agent Builder tools), authenticated by Elasticsearch API key. |
| **Reasoning, planning, action** beyond chat | Per-chunk multimodal reasoning, memory-grounded relation labeling, tool-driven persistence, and end-of-meeting synthesis — a multi-step agent, not a chatbot. |
| **One** official partner track selected | **Elastic.** |
| **Google Cloud used exclusively** for cloud needs; no competing services | All cloud infra is Google Cloud (Cloud Run, Cloud SQL, GCS, Pub/Sub, Memorystore). Elastic is the chosen partner product and is used for memory only. |
| **Only Google Cloud AI + partner built-in AI**; all other AI prohibited | Reasoning/vision = **Gemini 3** (Google). Transcription = **Google Cloud Speech-to-Text**. Semantic memory = **Elastic ELSER** (partner built-in). No third-party AI. |
| Runs on **web, Android, or iOS** | Web app (Next.js). |
| **Newly created** during the contest period; no extending prior work | Repository created new for this hackathon. |
| **Public, open-source repo** with a detectable, visible **OSI-approved** license that does not limit commercial use | Public repo under **Apache-2.0** (`LICENSE` at repo root). |
| **Hosted project URL** | Web app + API deployed on Cloud Run. |
| **Text description**: features, technologies, data sources, findings/learnings | Provided in this README and the Devpost entry. |
| **Demo video** ≤ 3 min, public on YouTube/Vimeo, English or subtitled, shows the project functioning | Planned per submission checklist. |
| **Devpost form** complete; team ≤ 4, all listed | Tracked in submission checklist. |

---

## AI Services Compliance (explicit)

The rules permit only Google Cloud AI tools plus the chosen partner's built-in AI. VisualSprint's AI surface is therefore constrained to:

| Capability | Service | Why compliant |
| --- | --- | --- |
| Reasoning / synthesis | **Gemini 3** (Agent Builder) | Google Cloud AI |
| Visual evidence understanding | **Gemini 3 multimodal** | Google Cloud AI |
| Speech-to-text | **Google Cloud Speech-to-Text** | Google Cloud AI |
| Semantic / hybrid memory search | **Elastic ELSER** + ES\|QL | Partner built-in AI |

No OpenAI, Anthropic, Hugging Face, or other third-party models are used anywhere in the pipeline.

---

## Project Status

This repository is in the early implementation stage. It currently contains:

* scaffolding for a service-oriented monorepo (`apps/`, `services/`, `packages/`, `infra/`, `docs/`)
* the Apache-2.0 license, base editor/ignore config, and this architecture documentation

The foundational product code (web shell, shared contracts, FastAPI control plane) is the next slice. Blob upload, real transcription, Elastic-backed memory, and the Google Agent Builder agents are upcoming slices. This README describes the target architecture the implementation follows.

---

## What VisualSprint Does

* capture browser-based meeting audio and shared-screen context
* process recordings in time-based chunks
* generate timestamped transcript segments with speaker context (deterministic STT service)
* detect visual evidence such as code, terminals, diagrams, errors, and slides (Gemini multimodal)
* identify decisions, commitments, blockers, and open questions, deduplicated across chunks
* compare current outputs against past meeting history via Elastic semantic retrieval
* render a live dashboard during the meeting
* generate a structured final report immediately after the meeting ends

### Capture support note

VisualSprint is currently a web app, so browser security rules matter:

* browser-based meetings are the cleanest supported path
* another browser tab can only be captured if the user explicitly shares that tab
* an external desktop app such as Zoom can only be observed if the user explicitly shares that window or the whole screen
* the product should not depend on hidden access to desktop apps

See [capture-constraints-and-plan.md](./docs/capture-constraints-and-plan.md) for the detailed support model and roadmap.

---

## Architecture Principles

1. **Deterministic backend owns orchestration; agents own interpretation.** Capture, chunking, transcription, frame extraction, uploads, retries, state transitions, persistence, access control, and dashboard transport are deterministic services. Agents only interpret content, retrieve history, resolve ambiguity, and assemble structured intelligence. The backend drives the chunk pipeline — the managed agent is not the scheduler.
2. **Transcription and frame extraction are services, not agents.** STT and frame extraction are deterministic ML/media steps; only reasoning over their output is agentic. This keeps deterministic work out of the managed agent layer.
3. **One multimodal reasoning call per chunk.** Transcript interpretation, visual reasoning, and decision/commitment/blocker/question extraction collapse into a single Gemini 3 multimodal call per chunk — fewer handoffs, lower latency, one schema, fewer failure modes.
4. **The output schema is the contract.** Structured output is the product. The JSON schema in `packages/contracts` is defined first and is the shared contract between the agent, the Elastic index, and the dashboard.
5. **Memory is a specified retrieval step.** The Elastic memory layer is the core differentiator and is fully specified below — index, ELSER semantics, the MCP retrieval contract, and match relation labels.
6. **Running meeting state carries across chunks.** A running state object (open decisions/blockers/commitments) is fed into each chunk call so the model updates and deduplicates instead of re-emitting. This is what makes "live" coherent.
7. **Connector-normalized ingestion.** All sources normalize into one downstream pipeline.
8. **Multi-tenant-ready, tenant-scoped memory** from the start, even where the first implementation is single-user.

---

## System Components

### Deterministic services (our repository)

| Service | Responsibility |
| --- | --- |
| `apps/web` | Product UI, browser capture, live dashboard, report view |
| `services/api` | Control plane: meeting/chunk lifecycle, state, dashboard transport (SSE), agent tool endpoints |
| `services/ingest` | Capture intake, chunk lifecycle, signed uploads, retries, Speech-to-Text |
| `services/media` | Frame extraction, media transformation, derived assets |
| `packages/contracts` | Shared output schema and event contracts (defined first) |
| `packages/sdk` | Reusable client/service integrations |

### Agent layer (Google Agent Builder + Gemini 3)

The production core is **two main agents** plus one optional high-value review layer. Everything earlier drafts called an "agent" is either a deterministic service (transcription, extraction) or a focused reasoning step.

| Agent | When it runs | Responsibility |
| --- | --- | --- |
| **Orchestrator / Reasoning Agent** | per chunk | Receives assembled chunk context as input, performs the Gemini 3 multimodal Insight reasoning, calls the **Elastic MCP** memory tool, and calls backend tools to persist outputs. This is the agent that satisfies the Gemini + Agent Builder + partner-MCP requirement. |
| **Summary Agent** | at meeting close | Composes the final evidence-backed report from all accumulated structured outputs, visual context, reasoning results, and historical matches. |
| **Action Recommendation / Escalation Review** | after reasoning or after summary, before external actions | Reviews structured outputs, ranks urgency and confidence, and produces approval-based suggestions for Jira, Slack, escalation, or manual review. It does not send externally without human approval. |

> **Why not five subagents?** Splitting transcript, vision, and reasoning into separate agents adds latency and failure surface without adding capability — for one chunk the reasoning task is one thing: *given this transcript window + these frames + current meeting state, what changed?* That is one multimodal call. The extra layer only earns its keep where the task is genuinely different: approval-based action recommendation and escalation review.

---

## Processing Pipeline

```text
capture ──► chunk ──► [Speech-to-Text]   ─┐
                      [frame extraction]  ─┴─► assemble chunk context
                                              (transcript window + key frames
                                               + running meeting state)
                                                        │
                                                        ▼
                                          Orchestrator/Reasoning Agent
                                          (1 Gemini 3 multimodal Insight call)
                                                        │
                                                        ▼
                                          Elastic memory retrieval (ELSER, via MCP)
                                                        │
                                                        ▼
                                          persist outputs + index to Elastic
                                          + update running state
                                                        │
                                                        ▼
                                          push delta to dashboard (SSE)
                                                        │
                              ┌─────────────────────────┘
                              ▼ (on meeting close)
                       Summary Agent ──► final report
                              │
                              ▼
            Action Recommendation / Escalation Review
                              │
                              ▼
             portal suggestions ──► human approval ──► Jira / Slack send
```

### Data-flow rules

* **Chunk context is passed *into* the agent as input.** The agent does not call back to fetch chunk context the backend already holds. It calls back only for what it cannot be handed: Elastic memory (via MCP) and persistence/finalize (via backend tools). This removes the backend→agent→backend round trip.
* **Running meeting state** (current open records with their IDs) is included in each chunk call so the model emits *updates* (`new` / `update` / `resolve`) rather than duplicates.
* **Cross-chunk continuity** is maintained by the deterministic backend (it owns the running state object), not by a stateless managed agent.

---

## Output Contract (defined first)

Structured output is the product, so its schema is the foundational artifact in `packages/contracts`. All agent output, all Elastic documents, and all dashboard rendering key off it.

```jsonc
{
  "id": "string",                 // stable id; reused across chunks for updates
  "tenant_id": "string",
  "meeting_id": "string",
  "type": "decision | commitment | blocker | open_question",
  "summary": "string",            // one-line canonical statement
  "detail": "string",
  "status": "open | updated | resolved | reopened",
  "owner": "string | null",       // commitments / blockers
  "evidence": [
    { "chunk_id": "string", "t_start": 0, "t_end": 0,
      "transcript_ref": "string | null", "frame_ref": "string | null" }
  ],
  "memory_matches": [             // populated by the Elastic MCP retrieval step
    { "source_meeting_id": "string",
      "score": 0.0,
      "relation": "new | recurring | reopened | resolved_previously",
      "snippet": "string" }
  ],
  "first_seen_chunk": "string",
  "last_updated_chunk": "string"
}
```

* Types are differentiated by `type` plus a few type-specific fields (e.g. `owner`/`due` for commitments, `severity` for blockers).
* `memory_matches[]` with a `relation` label is what powers "this blocker was raised two sprints ago" and "this decision was reopened without closure."
* The same `id` reused across chunks (with `status` transitions) prevents duplicate/fragmented outputs in the live view.

---

## Memory Layer (Elastic) — the differentiator, fully specified

Cross-meeting memory is VisualSprint's strongest differentiator and the reason for the Elastic track. Following the official [Elastic track resources](https://rapid-agent.devpost.com/details/elastic-resources), it is built on **Elasticsearch Serverless**, **ELSER**, and **Elastic Agent Builder** tools exposed via the **Elastic MCP server**.

### Write / index strategy (deterministic backend)

* Every finalized structured output is indexed into a **tenant-scoped Elasticsearch Serverless** index as it is persisted by the backend (keeping writes deterministic per principle 1).
* **Index fields:** `tenant_id`, `meeting_id`, `type`, `summary`, `detail`, `status`, `owner`, `created_at`, plus an **ELSER** semantic field over `summary` + key `detail`. ELSER runs automatically, so no separate embedding model is needed (and none would be allowed by the AI-tooling rule).

### Retrieval contract (Elastic Agent Builder tool, via MCP)

A custom **Elastic Agent Builder tool** (`search_prior_outcomes`) is defined with an ES\|QL / hybrid-semantic query and exposed to Google Agent Builder through the Elastic MCP server. For each candidate output in a chunk, the Reasoning Agent calls it:

1. Query the tenant-scoped index with **hybrid search** (ELSER semantic + BM25 keyword).
2. Return matches above a configured score threshold.
3. The agent assigns a `relation` to each match:
   * `new` — no match above threshold
   * `recurring` — strong match to a prior open/active record
   * `reopened` — strong match to a record previously `resolved`
   * `resolved_previously` — match indicating the issue was already closed

Every query is scoped by `tenant_id`, so organizations sharing the platform never see each other's history. This MCP-backed retrieval is the partner-integration requirement in action.

---

## Live Dashboard and Report Experience

### Transport

The dashboard updates over **Server-Sent Events (SSE)** from `services/api`. After each chunk is persisted, the backend pushes a state delta (new/updated/resolved records + memory matches). SSE is chosen for its simple, one-directional server→browser flow; WebSocket remains an option if bidirectional control is later needed. Transient live state (stream cursors, in-flight coordination) lives in Memorystore (Redis).

### Live dashboard sections

* top meeting bar: name, elapsed time, participant context, end control
* live metrics row: decisions, commitments, blockers, visual events
* decisions panel with evidence references
* commitments and blockers panel with ownership and risk flags
* Elastic memory-match strip highlighting recurring/reopened history
* live transcript feed with timestamps linked to visual moments

### Final report view (the hero)

On meeting close the Summary Agent produces, and the UI consolidates:

* decision log
* commitment list with owners
* blocker list
* open questions
* memory-linked historical conflicts/repeats (from `memory_matches[]`)
* evidence-backed reasoning context (links to transcript + frames)

---

## Data and Storage Architecture

Core entities (multi-tenant-ready): `Organization`, `Workspace`, `User`, `Meeting`, `MeetingParticipant`, `CaptureSession`, `SourceConnector`, `MediaChunk`, `TranscriptSegment`, `ScreenEvent`, `DecisionRecord`, `CommitmentRecord`, `BlockerRecord`, `OpenQuestion`, `MemoryMatch`, `FinalReport`.

| Store | Holds |
| --- | --- |
| Cloud SQL (PostgreSQL) | system-of-record entities, tenant boundaries, meeting state, structured outputs, reports |
| Google Cloud Storage | raw media, extracted frames, thumbnails, derived assets |
| Memorystore (Redis) | transient live state, stream cursors, in-flight coordination |
| Elasticsearch Serverless | searchable historical intelligence, ELSER semantic memory, hybrid matching |
| Secret Manager | Elasticsearch API key and other secrets |

Every historical lookup is tenant-scoped.

---

## Connector Strategy

* `browser_live_capture` — first connector
* `recording_upload` — future
* `document_link` — future

The first-class connector path should stay browser-tab-first. Desktop app scenarios such as Zoom are supported through user-approved window or full-screen sharing, not hidden app access.

All connectors normalize into the same downstream pipeline so transcript analysis, visual reasoning, memory lookup, and reporting do not need per-source architectures.

---

## Google Cloud + Elastic Stack

* **Frontend:** Next.js, React, Tailwind CSS (web platform)
* **Backend services:** FastAPI / Python on **Cloud Run**
* **Reasoning:** **Gemini 3** via **Google Agent Builder**
* **Speech-to-text:** Google Cloud Speech-to-Text
* **System of record:** Cloud SQL for PostgreSQL
* **Object storage:** Google Cloud Storage
* **Event processing:** Pub/Sub
* **Ephemeral live state:** Memorystore (Redis)
* **Secrets:** Secret Manager
* **Historical memory:** Elasticsearch Serverless + ELSER + Elastic Agent Builder (MCP)

### What lives in Agent Builder vs. our repo

**Google Agent Builder (portal):** the Orchestrator/Reasoning Agent and Summary Agent; Gemini 3 model selection per step; instructions, guardrails, Responsible-AI safety settings; the Elastic MCP tool connection; connections to our backend tool endpoints; preview, iteration, deployment.
The same layer can optionally host an approval-based Action Recommendation / Escalation Review subflow for high-confidence Jira or Slack suggestions.

**Our repository:** browser capture (`apps/web`); control plane and tool endpoints (`services/api`); ingestion + Speech-to-Text and media/frame extraction; Elastic indexing/write-back; state persistence, uploads, retries, SSE transport; domain contracts, report shaping, product UI.

### Backend tool endpoints the agent calls

Kept minimal and deterministic — the agent is handed chunk context as input; these cover only what it cannot be handed:

* `register_outputs` — persist decisions/commitments/blockers/open questions for a chunk (and index to Elastic)
* `get_meeting_state` — fetch current running state (only when not already in the prompt)
* `finalize_report` — trigger/persist the final report at meeting close
* `create_action_suggestions` — optional deterministic endpoint to persist portal-facing Jira, Slack, escalation, or manual-review suggestions
* `approve_and_send_action` — optional deterministic endpoint that sends approved actions to Jira or Slack
* (memory search is the **Elastic MCP** tool, not a backend endpoint)

---

## Agent Builder + Elastic MCP Setup Plan

Verified against the official [resources](https://rapid-agent.devpost.com/resources) and [Elastic track resources](https://rapid-agent.devpost.com/details/elastic-resources).

**Google Cloud**

1. Create a no-cost trial (cloud.google.com/free) and request the **$100 hackathon credits** form; enable billing.
2. Enable services: Gemini / Agent Builder (Gemini Enterprise), Cloud Run, Cloud SQL, Cloud Storage, Pub/Sub, Memorystore, Secret Manager, Speech-to-Text.

**Elastic**

3. Create a free **Elasticsearch Serverless** project at cloud.elastic.co.
4. Enable **Agent Builder** in Kibana; create the index and ELSER mapping; define the `search_prior_outcomes` tool (ES\|QL / hybrid semantic).
5. Generate an Elasticsearch **API key**; store it in **Secret Manager**.

**Agent Builder (Google)**

6. Create the Gemini Enterprise app (top-level agent container).
7. Build the **Orchestrator/Reasoning Agent**: select Gemini 3; instructions cover chunk-by-chunk analysis, the required output schema, running-state updates, and tool-calling rules.
8. Build the **Summary Agent** for end-of-meeting report synthesis.
9. Optionally add the **Action Recommendation / Escalation Review** layer for high-value downstream suggestions and approval gating.
10. **Point Google Agent Builder at the Elastic MCP server endpoint** (authenticated by the Elasticsearch API key); require a memory lookup before any output is labeled `new`, `recurring`, or `resolved`.
11. Connect backend tools (`register_outputs`, `get_meeting_state`, `finalize_report`, and optional approval-gated action endpoints).
12. Preview in the Agent Builder playground with sample meeting inputs; verify tool selection and output stability; configure Responsible-AI safety settings.
13. Deploy; connect the agent to the product UI. The web app and backend drive meeting creation, capture, and display; the agent provides intelligence outputs.

---

## Judging Criteria Alignment

The four official criteria are equally weighted. VisualSprint targets each directly:

| Criterion | How VisualSprint scores |
| --- | --- |
| **Technological Implementation** — quality of Google Cloud + Partner integration | Clean deterministic/agentic split; Gemini 3 multimodal reasoning; real Elastic ELSER hybrid memory through the MCP server; Cloud Run deployment. |
| **Design** — UX thoughtfulness | Live dashboard with evidence-linked panels and a polished post-meeting report as the hero surface. |
| **Potential Impact** — effect on the community | A trustworthy team system-of-record that catches recurring blockers and reopened decisions — a real engineering-workflow pain. |
| **Quality of the Idea** — creativity/uniqueness | Cross-meeting memory ("seen this blocker before?") is what transcript tools cannot do; the differentiator is the idea, not a wrapper on summaries. |

---

## Implementation Phases

1. **Contracts and foundation** — define the output schema in `packages/contracts` first; repo standards, Google Cloud + Elastic environment, base API.
2. **Live capture and ingestion** — browser capture, chunk uploads, meeting lifecycle, running-state object.
3. **Transcript and vision pipeline** — Speech-to-Text service, frame extraction service, structured intermediate records.
4. **Reasoning + memory** — per-chunk Gemini 3 Insight call; Elasticsearch index + ELSER; the `search_prior_outcomes` MCP tool; relation labeling.
5. **Agent layer** — Orchestrator/Reasoning Agent and Summary Agent in Agent Builder; wire Elastic MCP and backend tools.
6. **Action review layer** — approval-based Jira, Slack, escalation, and manual-review suggestions.
7. **Dashboard and report** — SSE transport, live panels, final report view with evidence linking.
8. **Submission** — hosted Cloud Run URL, public repo, 3-min video, Devpost entry.

---

## Submission Checklist

* [ ] Functional agent powered by **Gemini 3** and **Google Cloud Agent Builder**
* [ ] **Elastic MCP server** integrated (Elastic Agent Builder tool, API-key auth)
* [ ] Reasoning, planning, and action beyond simple chat
* [ ] **Elastic** partner track selected
* [ ] Google Cloud used exclusively; only Google Cloud AI + Elastic built-in AI
* [ ] Runs on the **web** platform
* [ ] Project **newly created** during the contest period
* [ ] Public repo with **Apache-2.0** (OSI-approved, visible at root)
* [ ] **Hosted project URL** (Cloud Run)
* [ ] **Text description**: features, technologies, data sources, findings/learnings
* [ ] **Demo video** ≤ 3 min, public on YouTube/Vimeo, English or subtitled, shows it functioning
* [ ] **Devpost form** complete; team ≤ 4 members, all listed
* [ ] All materials finalized before **June 11, 2026, 2:00 PM PDT**

---

## Open Questions

* Should VisualSprint remain fully open-source under Apache-2.0, or should the public repo stay open while future proprietary production modules live in separate private repositories? (Note: the rules require the submitted, non-proprietary code to be under an OSI-approved license that does not limit commercial use — Apache-2.0 satisfies this.)

---

## Repository Layout

```text
apps/
  web/            # product UI, browser capture, dashboard, report view
services/
  api/            # control plane + agent tool endpoints + SSE transport
  ingest/         # capture intake, chunking, Speech-to-Text, uploads, retries
  media/          # frame extraction, media transforms, derived assets
packages/
  contracts/      # output schema + event contracts (defined first)
  sdk/            # reusable clients/integrations
infra/            # infrastructure + deployment assets
docs/             # supplementary documentation
```

---

## Official Sources

* [Hackathon overview](https://rapid-agent.devpost.com/)
* [Hackathon rules](https://rapid-agent.devpost.com/rules)
* [Hackathon resources](https://rapid-agent.devpost.com/resources)
* [Partner update](https://rapid-agent.devpost.com/updates/43941-the-challenge-is-live-meet-your-partners)
* [Elastic track resources](https://rapid-agent.devpost.com/details/elastic-resources)
* [Hackathon FAQ](https://rapid-agent.devpost.com/details/faq)
* [Google Cloud free trial](https://cloud.google.com/free)
* [Google Cloud $100 credits form](https://forms.gle/xfv9vQzfRfNCCVbG7)
* [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
* [Google Agent Builder guide](https://cloud.google.com/products/agent-builder)
* [Agent Runtime overview](https://cloud.google.com/vertex-ai/docs/generative-ai/reasoning-engine/overview)
* [Gemini Enterprise agents overview](https://docs.cloud.google.com/gemini/enterprise/docs/agents-overview)
* [Elastic Agent Builder MCP server docs](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/mcp-server/)
* [Cloud Run quickstart](https://cloud.google.com/run/docs/quickstarts)
* [Secret Manager](https://cloud.google.com/secret-manager/docs)

---

## License

VisualSprint is open source under the [Apache License 2.0](LICENSE) (SPDX: `Apache-2.0`), an OSI-approved license that permits commercial use.
