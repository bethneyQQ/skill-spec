---
name: "Skill-Spec: Proposal"
description: "Create a new skill spec through interactive requirements gathering and validation"
---

<!-- SKILL-SPEC:START -->
**Guardrails**
- Always read `skillspec/SKILL_AGENTS.md` first for conventions
- Collect requirements through conversation before generating spec.yaml
- Do NOT create empty templates - generate complete, valid specs
- Always validate with `skillspec validate --strict` before completing
- Use kebab-case for skill names (e.g., `extract-api-contract`)

**Arguments**
- `$ARGUMENTS` contains the skill name provided by the user

**Steps**

1. **Parse skill name**
   - Extract from `$ARGUMENTS`, validate kebab-case format
   - If no name provided, ask user for one

2. **Check existing skill**
   - Run `skillspec list` to see existing skills
   - Check if `skillspec/drafts/<name>` or `skillspec/skills/<name>` exists

3. **Collect: skill (Metadata)**
   ```
   What should '<name>' do? (one sentence, 10-200 chars)
   Who owns this skill?
   ```

   **v1.1 Enhanced Metadata** (ask these additional questions):
   ```
   What category? (documentation | analysis | generation | transformation | validation | orchestration)
   What complexity level? (low | standard | advanced)
   What tools/capabilities are required? (file_read, file_write, search, web_access, code_execution, api_call...)
   What roles/personas benefit from this skill? (developer, architect, technical-writer, qa-specialist...)
   ```

4. **Collect: triggers (NEW v1.1 - from Superpowers)**
   ```
   When should AI activate this skill? (use_when conditions)
   - "User requests..."
   - "Codebase lacks..."
   - "When X changes..."

   When should AI NOT use this skill? (do_not_use_when conditions)
   - "When translating existing..."
   - "For marketing content..."
   ```

5. **Collect: inputs**
   ```
   What inputs does this skill need?
   - name: snake_case
   - type: string | number | boolean | object | array
   - required: true | false
   - constraints: not_empty, max_length, pattern, enum...
   ```

6. **Collect: preconditions**
   ```
   What must be true before this skill runs?
   ```

7. **Collect: non_goals**
   ```
   What should this skill explicitly NOT do?
   ```

8. **Collect: boundaries (NEW v1.1 - from SuperClaude)**
   ```
   What WILL this skill do? (explicit capabilities)
   - "Extract documentation from code comments"
   - "Generate Markdown formatted output"

   What WILL NOT this skill do? (explicit limitations)
   - "Translate existing documentation"
   - "Infer undocumented behavior"
   ```

9. **Collect: decision_rules**
   ```
   What decisions does this skill make?
   - What conditions trigger different behaviors?
   - What's the default behavior?
   ```
   - MUST have one rule with `is_default: true`

10. **Collect: steps**
    ```
    What's the execution flow?
    ```

11. **Collect: behavioral_flow (NEW v1.1 - from SuperClaude, optional)**
    ```
    Want to describe high-level behavioral phases? (alternative/supplement to steps)

    Example phases:
    - analyze: Parse content, identify structure
    - generate: Create output based on analysis
    - validate: Verify completeness and accuracy

    For each phase: description + key_actions
    ```

12. **Collect: output_contract**
    ```
    What format should output be? (json | text | markdown | yaml)
    ```

13. **Collect: failure_modes**
    ```
    What error scenarios? (code: UPPER_SNAKE_CASE, retryable: bool)
    ```

14. **Collect: edge_cases**
    ```
    What edge cases? (empty input, malformed data, boundary values...)
    ```
    Generate for each:
    - case: descriptive name
    - expected: {status, code}
    - input_example: concrete input (optional but recommended)
    - covers_rule: which decision_rule this tests
    - covers_failure: which failure_mode this tests

15. **Collect: anti_patterns (NEW v1.1 - from Superpowers)**
    ```
    What mistakes might AI make when using this skill?
    - pattern: "Copying source code directly as documentation"
      why_bad: "Users need explanations, not code duplicates"
      correct: "Extract key info and describe in natural language"

    What rationalizations might AI use to skip rules?
    - excuse: "This feature is too simple to document"
      reality: "Simple features are easiest to document; skipping creates debt"

    What are red flags that indicate misuse?
    - "Attempting to generate docs without source code"
    - "Skipping the analysis phase"
    ```

16. **Collect: context (Optional)**
    ```
    Does this skill work with other skills?
    - works_with: [{skill: "other-skill", reason: "why"}]
    - prerequisites: what user needs to do first
    - scenarios: typical usage scenarios (name, trigger, description)
    ```

17. **Collect: examples (Optional)**
    ```
    Want to add usage examples?
    - name, scenario, trigger, input, output, explanation
    ```

18. **Collect: _meta (Optional)**
    ```
    Any meta configuration?
    - content_language: en | zh | auto
    - format: full | minimal
    - token_budget: target word count for SKILL.md (default: 500)
    ```

19. **Generate and Review**
    - Generate complete spec.yaml with all collected info
    - Include `spec_version: "skill-spec/1.1"`
    - Show spec to user in code block
    - Ask: "Does this look correct? Any adjustments?"
    - Make adjustments if requested

20. **Write spec.yaml**
    - Create directory: `skillspec/drafts/<name>/`
    - Write spec.yaml to the directory

21. **Run strict validation**
    ```bash
    skillspec validate <name> --strict
    ```

22. **Parse and explain validation results**
    For each error/warning, explain which layer:
    - **Layer 1 (Schema)**: Missing required fields, type mismatches
    - **Layer 2 (Quality)**: Forbidden patterns, vague language
    - **Layer 3 (Coverage)**: Uncovered failure modes, missing edge cases
    - **Layer 4 (Consistency)**: Cross-reference issues, broken step chains
    - **Layer 5 (Compliance)**: Policy violations (if configured)

23. **Provide fix suggestions**
    For each issue, suggest specific fixes:
    ```
    ERROR: Forbidden pattern "try to" detected

    Current:
      action: "Try to validate the input"

    Suggested fix:
      decision_rules:
        - id: validate_input
          when: "input != null"
          then: {action: validate}

    Apply this fix? [y/n]
    ```

24. **Auto-fix common issues**
    - Missing `is_default: true` on fallback rule
    - Missing edge cases for defined failure modes
    - Missing required sections with sensible defaults

25. **Re-validate until passing**
    - If fixes applied, re-run validation
    - Repeat until all errors resolved

26. **Show completion summary**
    ```
    Validation Summary:
    - Schema: PASS
    - Quality: PASS
    - Coverage: PASS
    - Consistency: PASS

    Proposal complete: skillspec/drafts/<name>/

    Next steps:
    1. Apply (generate SKILL.md): /skill-spec:apply <name>
    2. Deploy (publish): /skill-spec:deploy <name>
    ```

**Field Reference (v1.1)**

```yaml
spec_version: "skill-spec/1.1"

_meta:                              # optional
  content_language: en | zh | auto
  mixed_language_strategy: union | segment_detect | primary
  format: full | minimal            # NEW v1.1
  token_budget: 500                 # NEW v1.1: target word count for SKILL.md

skill:                              # required
  name: kebab-case                  # ^[a-z][a-z0-9]*(-[a-z0-9]+)*$
  version: "1.0.0"                  # semver
  purpose: string                   # 10-200 chars
  owner: string
  category: string                  # NEW v1.1: documentation|analysis|generation|...
  complexity: string                # NEW v1.1: low|standard|advanced
  tools_required: [string]          # NEW v1.1: file_read, file_write, search, web_access, etc.
  personas: [string]                # NEW v1.1: developer, architect, etc.

triggers:                           # NEW v1.1 (from Superpowers)
  use_when: [string]                # conditions that should trigger this skill
  do_not_use_when: [string]         # conditions when NOT to use

inputs:                             # required, min 1
  - name: snake_case                # ^[a-z][a-z0-9_]*$
    type: string|number|boolean|object|array
    required: boolean
    constraints: [...]              # optional: not_empty, max_length, pattern, enum
    domain: {...}                   # optional: {type: enum|range|pattern_set|boolean|any}
    description: string             # optional
    tags: [...]                     # optional: pii, sensitive, etc.

preconditions: [string]             # required, min 1
non_goals: [string]                 # required, min 1

boundaries:                         # NEW v1.1 (from SuperClaude)
  will: [string]                    # explicit capabilities
  will_not: [string]                # explicit limitations

decision_rules:                     # required
  _config:
    match_strategy: first_match|priority|all_match
    conflict_resolution: error|warn|first_wins
  rules:
    - id: snake_case
      priority: int >= 0
      is_default: boolean           # one rule MUST be default
      when: string|boolean|object
      then: {status, code, action, path, log}

steps:                              # required, min 1
  - id: snake_case
    action: string
    output: string                  # optional
    based_on: [string]              # optional
    condition: string               # optional

behavioral_flow:                    # NEW v1.1 (from SuperClaude), optional
  - phase: string                   # analyze, generate, validate, etc.
    description: string
    key_actions: [string]

output_contract:                    # required
  format: json|text|markdown|yaml|binary
  schema: {...}                     # JSON Schema

failure_modes:                      # required, min 1
  - code: UPPER_SNAKE_CASE          # ^[A-Z][A-Z0-9_]*$
    retryable: boolean
    description: string             # optional
    recovery_hint: string           # optional

edge_cases:                         # required, min 1
  - case: string
    description: string             # optional
    input: any                      # optional
    expected: {status, code}
    covers_rule: string             # optional
    covers_failure: string          # optional

anti_patterns:                      # NEW v1.1 (from Superpowers), optional
  mistakes:
    - pattern: string
      why_bad: string
      correct: string
  rationalizations:
    - excuse: string
      reality: string
  red_flags: [string]

context:                            # optional
  works_with: [{skill, reason}]
  prerequisites: [string]
  scenarios: [{name, trigger, description}]  # trigger is NEW v1.1

examples:                           # optional
  - name: string
    scenario: string                # NEW v1.1
    trigger: string                 # NEW v1.1
    input: any
    output: any
    explanation: string             # optional
```

**v1.1 New Sections Quick Reference**

| Section | Source | Purpose |
|---------|--------|---------|
| `triggers` | Superpowers | When to activate (use_when / do_not_use_when) |
| `boundaries` | SuperClaude | Will / will_not declarations |
| `behavioral_flow` | SuperClaude | High-level phases (alternative to steps) |
| `anti_patterns` | Superpowers | Mistakes, rationalizations, red_flags |

**Validation Layers Reference**

| Layer | What it checks | Common errors |
|-------|----------------|---------------|
| Layer 1: Schema | Structure, required fields, types | Missing sections, wrong types |
| Layer 2: Quality | Forbidden patterns, vague language | "try to", "as needed", "appropriate" |
| Layer 3: Coverage | Edge cases, failure mode coverage | Uncovered failure modes |
| Layer 4: Consistency | Cross-references, step chains | Broken based_on references |
| Layer 5: Compliance | Enterprise policies | Policy-specific violations |

**CLI Reference**

```bash
# Schema documentation (NEW)
skillspec schema                    # show all sections
skillspec schema <section>          # show specific section fields
skillspec schema --new-only         # show only v1.1 new sections

# Validation
skillspec validate <name> --strict
skillspec validate <name> --strict --format json

# Reports
skillspec report <name>
skillspec report <name> --quality
skillspec report <name> --coverage
skillspec report <name> --compliance
```
<!-- SKILL-SPEC:END -->
