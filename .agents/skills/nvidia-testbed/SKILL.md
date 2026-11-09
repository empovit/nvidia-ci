---
name: nvidia-testbed
description: Make one OpenShift test environment ready for a planned NVIDIA verification, including special or loaned hardware.
---

# Prepare a specific testbed

Use the [NVIDIA feature verification and automation workflow](../../../docs/feature-verification-workflow.md)
with a real Jira key and its existing scope and plan. Report missing or
inaccessible ticket context before proceeding.
Use the chosen testbed's tools unless the user selects another interface.

Use the plan's target versions, configuration, and hardware to find a suitable
existing OpenShift cluster or make one available. The `nvidia-ci` tests access
that cluster through `KUBECONFIG`; provisioning may happen in a CI job or
separately.

Use the planned [testbed source](../../../docs/feature-verification-workflow.md#testbed-sources-and-scenario-eligibility).
Confirm scenario eligibility separately from availability: check actual
hardware, software, and platform prerequisites, not just the source's label.
Bare-metal installations commonly use the OpenShift Assisted
Installer and a BMC, operated manually or using existing Redfish automation.
Establish hardware availability and any loan or VPN access (including NVIDIA's
lab when applicable). Use the shared
[operational agreement](../../../docs/feature-verification-workflow.md#operational-agreement)
before provisioning or changing a live environment.

The outcome is a usable environment for this verification. Record its actual
versions, hardware, and setup so manual and automated checks can share it.

If required access or prerequisites are unavailable, report which scenarios
remain blocked and what can proceed without them. Setup code alone does not
establish that the actual testbed is ready.

When the ticket calls for new reusable setup code, hand off to
[nvidia-implement](../nvidia-implement/SKILL.md) for that code deliverable.
