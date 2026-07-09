---
name: ai-skill-developer
description: Create or update AI skill folders in the dedicated ai-skills GitOps repository using a PR-only workflow. Use when asked to add, revise, validate, or publish reusable skills through Port governance.
---

# AI Skill Developer

Work only through a branch and pull request. Do not push directly to the default branch.

## Workflow

1. Clone the configured skills repository and create a branch named `ai-skill/<short-skill-name>-<run-id>`.
2. Create or update `skills/<skill-name>/SKILL.md` and only add `references/`, `scripts/`, or `assets/` when they directly support the skill.
3. Update `skills.yaml` with Port-facing metadata: stable Port identifier, description, status, required group, allowed models, approval flag, execution backend, source repo, source path, source ref, version, owner, and validation date.
4. Run the repository validator before committing.
5. Commit the branch with a concise message and open a pull request for human review.
6. Report the pull request URL and validation summary back to the Port action run.

## Guardrails

- Keep skill folder names lowercase and hyphenated.
- Keep `SKILL.md` frontmatter limited to `name` and `description`.
- Prefer references for detailed domain material and keep the main instructions concise.
- Do not include secret values, local credentials, generated caches, or unrelated documentation.
