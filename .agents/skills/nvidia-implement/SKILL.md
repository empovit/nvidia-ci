---
name: nvidia-implement
description: Implement NVIDIA verification automation when a ticket calls for test code, reusable testbed setup code, or CI job configuration.
---

# Implement verification automation

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md)
with a real Jira key. Report missing or inaccessible ticket context as blocked.

Use this skill when the ticket's definition of done includes code or
configuration. Manual-only verification follows the plan without this phase.

Read and reuse the ticket's goal, DOD, plan, and useful linked work, then inspect
existing tests, setup, and CI jobs. Confirm which test, reusable setup, or job
code is in scope; skip already delivered work.

Follow the guide's owning repository guidance and implementation/job ordering;
the owning repository's `AGENTS.md` remains authoritative. Use the shared
[operational agreement](../../../docs/feature-verification-workflow.md#operational-agreement)
before running setup automation or tests that change a live target.

Produce the scoped code or configuration changes. Run applicable checks and the
relevant OpenShift test when its planned testbed is available.
Running new setup automation may also produce the specific testbed needed for
verification; delivering code alone does not establish testbed readiness or a
behavioral pass. Finish with the shared
[closing summary](../../../docs/feature-verification-workflow.md#closing-summary),
leaving unverified DOD items explicit.
