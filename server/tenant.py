"""Which owner the current work is for.

A request knows its principal and a background worker knows a run's
owner; the model gateway, two layers down, knows neither. This context
variable carries the owner's subject to it, so a per-tenant model budget
can be charged to the right tenant (assessment B6). None means no owner
is known, which the budget treats as the local owner.
"""

import contextvars

current_owner = contextvars.ContextVar("agentic_os_current_owner", default=None)


def owner_or_local(value=None):
    return value or current_owner.get() or "local-owner"
