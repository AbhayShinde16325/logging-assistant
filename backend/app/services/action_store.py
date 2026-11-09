"""Pending-action registry (task T-015).

Single source of truth for ProposedActions awaiting confirmation (docs/api-contracts.md
'Action lifecycle': PENDING → EXECUTED | REJECTED | EXPIRED, 24h expiry). Backend-owned — the agent
only *proposes*; client never supplies IDs or payloads.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from backend.app.models.domain import ActionStatus, ProposedAction
from backend.app.utils.ids import DEFAULT_CLOCK, Clock, parse_iso, to_iso

ACTION_TTL = timedelta(hours=24)


class ActionStore:
    def __init__(self, clock: Clock = DEFAULT_CLOCK) -> None:
        self._actions: dict[str, ProposedAction] = {}
        self.clock = clock
        self._lock = asyncio.Lock()
        self.requesters: dict[str, str] = {}   # action_id -> requester EMP id
        self.commands: dict[str, str] = {}     # action_id -> Command_Log row (CMD-…)

    def add(self, action: ProposedAction, *, requester_id: str | None = None,
            command_id: str | None = None) -> ProposedAction:
        self._actions[action.action_id] = action
        if requester_id:
            self.requesters[action.action_id] = requester_id
        if command_id:
            self.commands[action.action_id] = command_id
        return action

    def binding(self, action_id: str) -> tuple[str | None, str | None]:
        """(requester_id, command_id) recorded when the action was proposed."""
        return self.requesters.get(action_id), self.commands.get(action_id)

    def get(self, action_id: str) -> ProposedAction | None:
        action = self._actions.get(action_id)
        if action is None:
            return None
        if action.status == ActionStatus.PENDING:
            created = action.created_at
            if created is not None:
                if (self.clock.utcnow() - parse_iso(created)) > ACTION_TTL:
                    expired = self.mark(action_id, ActionStatus.EXPIRED)
                    return expired
        return action

    def mark(self, action_id: str, status: ActionStatus) -> ProposedAction | None:
        action = self._actions[action_id]
        updated = action.model_copy(
            update={
                "status": status,
                "executed_at": to_iso(self.clock.utcnow()) if status == ActionStatus.EXECUTED else None,
            }
        )
        self._actions[action_id] = updated
        return updated
