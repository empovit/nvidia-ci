---
name: nvidia-verification-feature
description: Define a Jira work item for verifying or automating an externally developed NVIDIA feature, including its definition of done.
---

# Define a verification feature

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md)
when the goal needs clarification, not as a required restart for existing work.

Use the feature description and related documents or Jira tickets to state the
functionality in scope. Identify whether the goal is manual verification,
automated testing, or both, and whether it serves certification.

Write a concise definition of done: which functionality must be checked, on
which target platform or hardware when known, and what deliverable or observed
result means the Jira ticket's goal has been achieved. Leave unknowns for
planning rather than filling them with assumptions.

For an automation goal, name the code or configuration to deliver: a test,
repeatable setup, or CI job, as applicable. A run can validate the deliverable.

If a ticket exists, read and reuse its goal, DOD, plan, and useful linked work.
Propose clarification only where needed; do not rewrite fields or require a
parent Feature to conform. Skip this phase if the appropriate ticket already
provides sufficient scope.

Without a ticket, clarify the idea and draft text for an appropriately scoped
issue. Use [nvidia-jira-sync](../nvidia-jira-sync/SKILL.md) for creation only
with explicit user authorization. Verification planning and execution must
wait for a real Jira key. Report blocked access rather than proceeding as if
no ticket were needed.
