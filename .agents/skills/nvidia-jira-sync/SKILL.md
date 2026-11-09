---
name: nvidia-jira-sync
description: Create or update the NVIDIA Jira hierarchy for a verification feature and its planned work when the user asks to track it.
---

# Sync verification work to Jira

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md),
ticket or proposed feature definition, plus a breakdown only if one is useful.
Read existing related tickets before proposing creation. Reuse their goals,
DOD, plans, and useful linked work. Ticket presence does not require a sync:
do not create duplicates, force a parent Feature, or rewrite fields merely to
fit this workflow. For proposed hierarchy changes, inspect supported issue
types and parent links rather than assuming the breakdown can be applied.

Before any Jira write, obtain explicit user authorization for the intended
creates, updates, links, comments, or transitions; a draft or breakdown is not
authorization. Use the guide's recommended interface or the user's choice.
Apply only the approved changes. Create a parent before children only when new
linked issues are needed. Verify the resulting keys, changed fields, and links;
return what was reused, changed, or left unapplied. Do not close a ticket while
its DOD remains unverified.

The user supplies Jira access.

If Jira access or necessary parent relationships cannot be confirmed, report
the blocker and unapplied changes. For an idea without a ticket, a draft is
allowed, but verification planning and execution wait for a real Jira key.
