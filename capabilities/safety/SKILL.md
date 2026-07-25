---
name: safety
description: Toolless safety and refusal capability for forbidden live trading, credential, approval-bypass, and policy-unsafe requests.
---

# Safety Capability

Use this capability for forbidden live trading, broker credential, approval-bypass, or unsafe policy requests. It is intentionally toolless.

## Allowed tools

No tools are allowed for this capability.

## Context contract

Use policy rules, forbidden intent classifier output, and the agent instruction boundary. Do not call tools while refusing live orders, credential disclosure, approval bypass, or unclassified actions.

## Response contract

Return `SafetyRefusalResponse` with a short refusal, the violated boundary, and a safe paper-only alternative when one exists.
