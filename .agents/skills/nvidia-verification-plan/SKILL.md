---
name: nvidia-verification-plan
description: Analyze existing NVIDIA CI work and plan a feature's manual or automated verification, with a ticket-specific definition of done.
---

# Plan feature verification and automation

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md)
to fill planning gaps for an existing Jira key. Read and reuse the ticket's
goal, DOD, plan, and useful linked artifacts; skip already satisfied work. If
the ticket is missing or inaccessible, report the blocker before planning.

First review the feature documents and related Jira tickets, the relevant
tests and helpers in this repository, and the
[NVIDIA CI job definitions](https://github.com/openshift/release/tree/main/ci-operator/config/rh-ecosystem-edge/nvidia-ci).
Summarize existing coverage, reusable work, and gaps. The test code lives here;
CI job definitions can provision or use an OpenShift cluster and run the tests.
State when a source cannot be accessed; separate known requirements from open
questions. When CI job changes look likely, inspect the NVIDIA CI configs and
plan the job that will invoke the automation. Follow the guide's owning
repository guidance when the plan reaches code or job changes.

Write a brief plan covering:

1. **Scope:** Name the Jira key and reference its goal and DOD rather than
   redefining them. Ask only about gaps that affect the plan.
2. **Existing state:** Note relevant documents, related Jira work, existing
   tests and helpers, and CI jobs. Identify what is already covered or usable.
3. **Scenarios:** For each behavior, state the action, observable expected
   result, chosen method, and evidence to collect. Note gaps rather than
   assuming an unverified behavior passes.
4. **Testbed:** Select from the shared
   [testbed sources](../../../docs/feature-verification-workflow.md#testbed-sources-and-scenario-eligibility).
   Confirm scenario-specific hardware, software, platform, and version
   prerequisites separately from availability, loan, or access constraints.
   Distinguish the actual environment needed from reusable setup code to deliver.
5. **Reuse:** Identify setup, workloads, checks, or evidence collection that
   can serve both manual and automated paths. Point to existing repository
   helpers when applicable.
6. **Delivery:** Outline work needed for manual checks, test code, automated
   setup, or a CI job, as applicable. Include how the deliverable will be
   validated and any dependency that blocks the definition of done.
   If certification is the goal, include the supplied criteria and required
   evidence; ask for missing criteria instead of inventing them.
7. **Tracking, if useful:** Delegate decomposition to
   [nvidia-verification-breakdown](../nvidia-verification-breakdown/SKILL.md)
   only when separate tracking helps. Reuse useful existing tickets and
   hierarchy; a breakdown proposal does not authorize Jira writes.

Use a compact scenario table and short sections. Save the plan where the user
requests, or present it in the conversation when no location is specified.
