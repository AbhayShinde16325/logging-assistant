"""Agent ↔ backend wiring (task T-014 selection point).

Provider selection per docs/agent-workflow.md §4:
- tests / APP_ENV=test → MockModelProvider (injected or inferred);
- `MODEL_PROVIDER=heuristic` → no provider (pure deterministic nodes);
- `MODEL_PROVIDER=ollama|auto` → OllamaProvider (the graph falls back to heuristics per §5 when
  it is unreachable at call time).
"""

from __future__ import annotations

from agent.app.graph import AgentGraph
from agent.app.models.providers import MockModelProvider, OllamaProvider
from backend.app.core.config import Settings


def build_agent_graph(settings: Settings, *, provider_override=None) -> AgentGraph:
    if provider_override is not None:
        return AgentGraph(provider=provider_override)
    mode = (settings.model_provider or "auto").lower()
    if settings.app_env == "test":
        return AgentGraph(provider=MockModelProvider())
    if mode in ("none", "heuristic", "deterministic"):
        return AgentGraph(provider=None)
    provider = OllamaProvider(settings)
    if mode == "auto" and not provider.is_available():
        return AgentGraph(provider=None)  # deterministic fallback (workflow doc §5)
    return AgentGraph(provider=provider)
