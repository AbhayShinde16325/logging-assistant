# Project Overview

## Elevator pitch

An AI-powered personal project management agent for a small co-located team: members talk to the
assistant in plain language (typed or spoken), it understands work activities, manages the shared
task list in Google Sheets, tracks activity, and proactively reminds people — always asking for
confirmation before it changes anything important.

## Problem

Three people currently coordinate work through chat messages and a shared spreadsheet:

- Tasks mentioned in chat get lost — nothing becomes a tracked record unless someone types it into
  the sheet.
- Deadlines and follow-ups rely on memory.
- Nobody reliably knows what others completed.

## Solution

One assistant that converts natural language into structured task operations on top of the shared
spreadsheet:

```text
User Input → AI Understanding → Structured Action → User Confirmation
→ Google Sheets Update → Activity Tracking → Reminder
```

## Users & team

| Actor | Role |
|---|---|
| Employee (3 in MVP) | Talks to the assistant, does tasks, may edit the sheet manually |
| Lead (also an employee) | Assigns work via chat or dashboard, reviews activity |

Developing team (labels used across the repo; see `tasks.md`):
- **Developer A** — Project Lead / AI agent + backend
- **Developer B** — Google Sheets + integrations
- **Developer C** — Frontend + voice

## MVP principles

1. **Confirmation before consequence** — the assistant proposes; the user confirms (unless the
   action is read-only).
2. **One source of truth** — Google Sheets; humans may edit it directly, so the app must detect
   manual changes (polling reconciliation).
3. **LLM reasons, application executes** — the model never writes to the sheet or authorizes actions;
   the backend validates everything.
4. **Replaceable parts** — model provider, transcription provider, and even the storage backend are
   abstractions, so the prototype can evolve later.
5. **Prototype first** — prefer a working end-to-end demo; do not build enterprise features.
6. **Free & local-first** — Ollama for inference, no paid APIs as mandatory dependencies.

## What the assistant must understand (from plain language)

- Task creation with title, deadline, assignee (e.g. "research competitor products by Wednesday",
  "assign the API integration task to Rahul").
- Task completion ("I completed the authentication module"), modification, deletion.
- Queries ("What are my pending tasks?", "Summarize what everyone worked on this week").
- Meeting scheduling notes and action items from pasted meeting notes.
- Reminder requests ("Remind me about the report two hours before the deadline").

## Where assistant abilities end (honesty rules)

- No autonomous decisions about authorization — validated IDs from the app, not from the model.
- No calendar integration or email in the MVP.
- No automatic meeting attendance/recording — only pasted notes or transcripts.
- Reminders fire only while the backend is running.

## Documents that define this project

| Topic | Document |
|---|---|
| Full requirement list | [`requirements.md`](requirements.md) |
| How modules fit together | [`architecture.md`](architecture.md) |
| Agent internals | [`agent-workflow.md`](agent-workflow.md) |
| Milestones & priority tiers | [`prototype-roadmap.md`](prototype-roadmap.md) |
| Division of work | [`../tasks.md`](../tasks.md) |
