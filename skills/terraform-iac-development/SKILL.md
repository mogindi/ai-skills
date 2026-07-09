---
name: terraform-iac-development
description: Develop Terraform infrastructure artifacts with review-gated output, especially for Azure Linux VM requests and other internal platform IaC tasks. Use when asked to create Terraform while preserving security guardrails.
---

# Terraform IaC Development

Generate Terraform in the smallest useful scope for the requested infrastructure. Prefer clear provider/resource structure, explicit inputs, and secure defaults over broad module abstractions.

## Workflow

1. Confirm the requested infrastructure, cloud, environment, and required artifact path.
2. Generate Terraform without embedding passwords, API keys, private keys, or other secret material.
3. Use least-privilege networking defaults and avoid public management access unless explicitly requested and justified.
4. Include tester notes with formatting, validation, and policy commands that should be run.
5. Treat unresolved secret handling, public exposure, and missing validation evidence as blocking findings.
