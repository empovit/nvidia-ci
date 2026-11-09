# NVIDIA feature verification and automation workflow

This repository tests NVIDIA features developed elsewhere. Use this workflow to
plan and deliver manual verification, automated tests, reusable setup, or CI
jobs. The work may begin with manual verification or go directly to
automation. Either path may serve certification.
Most features need OpenShift on the target hardware. `nvidia-ci` contains the
tests; the [OpenShift CI configuration](https://github.com/openshift/release/tree/main/ci-operator/config/rh-ecosystem-edge/nvidia-ci)
defines the jobs that run them.

## Entry point and repository guidance

Use the `nvidia-verification` skill as the default entry point for NVIDIA
feature verification and automation. Invoke a phase skill directly only when
the user has already defined the phase and scope.

Before implementation, follow the owning repository's agent instructions:

- In `nvidia-ci`, read `AGENTS.md` for repository commands, layout, and test
  mechanics. `CLAUDE.md` imports that file rather than maintaining a second copy.
- For NVIDIA CI jobs in `openshift/release`, read that repository's root
  `AGENTS.md`. Normally, implement and validate automation in `nvidia-ci`
  first, then add or update a job there to invoke that automation.

## Recommended agent tools

These are defaults for agent interaction. Use the user's chosen interface when
specified, such as the Jira API instead of `jira`. The user supplies credentials
and access, including `KUBECONFIG`, VPN, and target hardware access.

| System | Recommended tool or interface |
|---|---|
| NVIDIA Jira | `jira -p NVIDIA` |
| GitHub repositories, pull requests, and CI job definitions | `gh`; `git` for local checkouts |
| OpenShift clusters | `oc` with `KUBECONFIG` |
| Cloud testbeds | The provider CLI: `aws`, `gcloud`, or `az` |

## Required ticket and phase routing

A real Jira ticket is required for work through this workflow, whether created
by a human, other tooling, or these skills. Read and reuse the appropriate
ticket's goal, definition of done (DOD), plan, and useful hierarchy or artifacts.
Infer the entry point from that state and skip already satisfied phases. Do not
require a new parent Feature, decomposition, duplicate ticket, or field rewrite
just to fit the workflow. Report blocked Jira access; it is not a no-ticket path.

For a new idea without a ticket, the feature phase may clarify the goal and
draft a proposed ticket. Creation requires explicit user authorization. Wait for
a real Jira key before verification planning or execution. Ticket presence is
mandatory; CREATE, UPDATE, and decomposition are separate, optional actions.
All Jira writes, including comments and transitions, need explicit user
authorization for the intended changes.

| Need | Skill |
|---|---|
| Clarify an idea or ticket goal | [nvidia-verification-feature](../.agents/skills/nvidia-verification-feature/SKILL.md) |
| Fill gaps in the verification plan | [nvidia-verification-plan](../.agents/skills/nvidia-verification-plan/SKILL.md) |
| Propose independently tracked work, only if useful | [nvidia-verification-breakdown](../.agents/skills/nvidia-verification-breakdown/SKILL.md) |
| Apply authorized Jira changes | [nvidia-jira-sync](../.agents/skills/nvidia-jira-sync/SKILL.md) |
| Prepare one actual environment | [nvidia-testbed](../.agents/skills/nvidia-testbed/SKILL.md) |
| Deliver test, reusable setup, or CI code | [nvidia-implement](../.agents/skills/nvidia-implement/SKILL.md) |

These are routes, not mandatory sequential gates. Manual verification follows
the plan without a coding phase; automation can also come first. Testbed and
implementation work can overlap when new setup automation creates the needed
environment. Apply certification criteria only when certification is the goal.

## Testbed sources and scenario eligibility

A testbed may come from hardware in the team's lab; hardware loaned by another
team or company; automated cloud setup through a CI job; or ad-hoc cloud setup.
Reuse an existing environment from any of these sources when suitable.
Availability and source do not establish scenario eligibility: confirm the
chosen scenario's hardware, software, and platform prerequisites, including
applicable [repository supported setups](../README.md#supported-setups).

## Operational agreement

Before live changes, agree on the target, allowed disruptive or billable
actions, and cleanup or retention. Execute within that scope without asking
at every step; pause for agreement only when the target or scope must change.
This is a short agreement, not an additional workflow phase or Jira write grant.

## Closing summary

Close manual and automation work with one short summary: what was delivered or
checked; the actual setup and relevant versions (or that no environment was
used); passed, failed, blocked, or not-run outcomes with evidence; and remaining
DOD items. Distinguish automation delivered from behavior verified. Unrun or
unsupported checks do not establish a pass; keep unverified DOD items explicit.
Meeting the DOD does not itself authorize closing or updating the Jira ticket.

## Example requests

- “Use `$nvidia-verification-feature` to define verification work for
  **[feature link]** and draft its definition of done.”
- “Use `$nvidia-verification-plan` to plan delivery for **[Jira ticket]**,
  starting with existing documentation, tests, and CI jobs.”
- “Use `$nvidia-verification-breakdown` to propose Jira tickets for the plan,
  then `$nvidia-jira-sync` to create them.”
- “Use `$nvidia-implement` for **[automation ticket]** to add the test or setup
  automation described by its definition of done.”
- “Use `$nvidia-verification` for **[Jira ticket]** to refine its goal, plan
  verification, and follow any applicable implementation work.”
