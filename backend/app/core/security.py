"""Optional shared-token auth (scaffold — see docs/api-contracts.md "Auth").

MVP is an internal prototype: when API_BEARER_TOKEN is set, protected routes require
`Authorization: Bearer <token>`; when empty, no auth is enforced.
NOT production-grade security — documented in root AGENTS.md / README.
"""

from __future__ import annotations
