---
name: terraform-security-review
description: Review Terraform infrastructure code for security risks, policy drift, unsafe network exposure, missing validation evidence, and remediation guidance. Use when asked to inspect Terraform or IaC changes before release.
---

# Terraform Security Review

Inspect Terraform inputs and planned changes before proposing remediation. Keep findings specific, cite file paths or resource names when available, and separate blocking security issues from advisory improvements.

## Workflow

1. Identify the Terraform scope, module boundaries, providers, and target environment.
2. Review resources for exposed management ports, permissive ingress, secret handling, identity scope, encryption, logging, and state risks.
3. Produce developer remediation notes that are actionable without rewriting unrelated infrastructure.
4. Provide validation notes describing commands, policy checks, or review evidence that should be run.
5. Mark unresolved security findings as blocking when they could expose credentials, public administration paths, privileged identities, or sensitive data.
