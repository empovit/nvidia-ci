---
name: nvidia-verification
description: Start here to coordinate NVIDIA feature verification and automation for externally developed features, including planning, Jira, testbeds, tests, setup, and CI jobs.
---

# NVIDIA feature verification and automation

Start here. This is the main entry point for the
[NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md).

Read the required Jira ticket and reuse its goal, DOD, plan, and useful linked
work, regardless of who created it. Use the guide's
[phase routing](../../../docs/feature-verification-workflow.md#required-ticket-and-phase-routing)
to choose the next unmet need, not to restart completed phases or impose a
hierarchy. Report inaccessible ticket context as blocked.

For a new idea without a ticket, route to
[nvidia-verification-feature](../nvidia-verification-feature/SKILL.md) for
clarification and a draft; wait for a real Jira key before planning or execution.
Use breakdown only when independent tracking helps, and sync only for explicitly
authorized Jira writes.

For manual verification, follow the ticket's plan on an eligible testbed. Use
the shared [operational agreement](../../../docs/feature-verification-workflow.md#operational-agreement)
before live changes and [closing summary](../../../docs/feature-verification-workflow.md#closing-summary)
for results. Route code deliverables to the implementation skill; manual and
automation may run in either order, with certification only when requested.
