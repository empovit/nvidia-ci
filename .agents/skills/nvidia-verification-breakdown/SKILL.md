---
name: nvidia-verification-breakdown
description: Turn an NVIDIA feature verification plan into a small Jira-ready hierarchy of planning and delivery work.
---

# Break down verification work

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md)
only when separate tracking would help an existing Jira ticket. Read its goal,
DOD, plan, and useful hierarchy or artifacts first. Report missing or
inaccessible ticket context as blocked rather than inventing replacement work.

Use the ticket's definition of done and available verification plan. The NVIDIA
project currently uses Feature → Epic → Story/Task → Sub-task links; reuse an applicable existing
parent or epic and propose only the levels the work needs. An appropriately
scoped existing ticket can stand alone; do not force a new parent Feature or
duplicate tickets.

Propose separate tickets only for work that benefits from independent
tracking: planning, testbed preparation, manual verification, test automation,
CI job changes, or certification, as applicable. These are possibilities, not
a required checklist.

For each ticket, give a short goal, definition of done, proposed parent if needed,
and any existing Jira key. Show how proposed work contributes to the source ticket's
definition of done. Development here means test code, setup, or CI work; the
externally developed product feature is outside this workflow unless the user
explicitly includes it.

For automation tickets, name the test code, setup automation, or CI job in
scope as the deliverable.

Return a compact proposal showing reused tickets and only needed additions.
This is not authorization to create, update, or reparent Jira issues.

## Next step

Recommend [nvidia-jira-sync](../nvidia-jira-sync/SKILL.md) when the hierarchy
is ready and the user explicitly authorizes the intended writes. If the breakdown
exposes an unresolved feature or testbed decision, return to
[nvidia-verification-plan](../nvidia-verification-plan/SKILL.md) first.
