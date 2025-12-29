---
name: "Skill-Spec: Proposal"
description: "Create a new skill spec through interactive requirements gathering and validation (v1.2 with agentskills.io support)"
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
   What should '<name>' do? (one sentence, 10-1024 chars for agentskills.io compatibility)
   Who owns this skill?
   ```

   **Enhanced Metadata** (ask these additional questions):
   ```
   What category? (documentation | analysis | generation | transformation | validation | orchestration)
   What complexity level? (low | standard | advanced)
   What roles/personas benefit from this skill? (developer, architect, technical-writer, qa-specialist...)
   ```

   **v1.2 agentskills.io Fields** (optional but recommended):
   ```
   What license? (SPDX identifier, e.g., Apache-2.0, MIT, or "LICENSE" for bundled file)
   Any environment requirements? (e.g., "Requires Python 3.9+", max 500 chars)
   Any custom metadata? (key-value pairs for additional properties)
   ```

4. **Collect: triggers (from Superpowers)**
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

8. **Collect: boundaries (from SuperClaude)**
   ```
   What WILL this skill do? (explicit capabilities)
   - "Extract documentation from code comments"
   - "Generate Markdown formatted output"

   What WILL NOT this skill do? (explicit limitations)
   - "Translate existing documentation"
   - "Infer undocumented behavior"
   ```

9. **Collect: tools_required (REQUIRED - Must Ask)**
   ```
   What tools does this skill need to accomplish its task?

   Questions to ask:
   1. Does this skill need to read files? (Read)
   2. Does this skill need to write/create files? (Write)
   3. Does this skill need to modify existing files? (Edit)
   4. Does this skill need to search for files? (Glob)
   5. Does this skill need to search file contents? (Grep)
   6. Does this skill need to run shell commands? If yes, which specific commands?
      - Examples: Bash(git:*), Bash(npm:*), Bash(python:*), Bash(docker:*)
   7. Does this skill need web access? (WebFetch, WebSearch)
   8. Does this skill need to ask the user questions? (AskUserQuestion)
   9. Does this skill use any MCP servers or custom tools? If yes, specify:
      - Tool name
      - What it does
      - Required parameters
   ```

   **Format (agentskills.io compatible):**
   - Simple tool: `Read`, `Write`, `Grep`
   - Scoped tool: `Bash(git:*)`, `Bash(npm:install)`
   - MCP tool: `mcp_server_name:tool_name`

   **This generates:**
   - `skill.tools_required`: List of tool categories (for documentation)
   - `skill.allowed_tools`: agentskills.io compatible tool list (for execution)

10. **Collect: decision_rules**
    ```
    What decisions does this skill make?
    - What conditions trigger different behaviors?
    - What's the default behavior?
    ```
    - MUST have one rule with `is_default: true`

11. **Collect: steps**
    ```
    What's the execution flow?
    ```

    **v1.2: Tool Bindings** (optional but recommended):
    ```
    Should any steps bind to specific tools?

    Example:
    - id: read_source
      action: "Read the source file"
      tool_binding:
        tool: Read
        params:
          file_path: "{{ input.source_path }}"

    Available standard tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebFetch, WebSearch
    ```

12. **Collect: tools (v1.2, Optional for custom MCP tools)**
    ```
    Does this skill need custom MCP tools not in the standard set?

    Example custom tool:
    - name: mcp_database_query
      description: "Execute SQL queries via MCP"
      params:
        - name: query
          type: string
          required: true
      requires_approval: true
    ```

13. **Collect: behavioral_flow (from SuperClaude, optional)**
    ```
    Want to describe high-level behavioral phases? (alternative/supplement to steps)

    Example phases:
    - analyze: Parse content, identify structure
    - generate: Create output based on analysis
    - validate: Verify completeness and accuracy

    For each phase: description + key_actions
    ```

14. **Collect: output_contract**
    ```
    What format should output be? (json | text | markdown | yaml)
    ```

15. **Collect: failure_modes**
    ```
    What error scenarios? (code: UPPER_SNAKE_CASE, retryable: bool)
    ```

16. **Collect: edge_cases**
    ```
    What edge cases? (empty input, malformed data, boundary values...)
    ```
    Generate for each:
    - case: descriptive name
    - expected: {status, code}
    - input_example: concrete input (optional but recommended)
    - covers_rule: which decision_rule this tests
    - covers_failure: which failure_mode this tests

17. **Collect: anti_patterns (from Superpowers)**
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

18. **Collect: context (Optional)**
    ```
    Does this skill work with other skills?
    - works_with: [{skill: "other-skill", reason: "why"}]
    - prerequisites: what user needs to do first
    - scenarios: typical usage scenarios (name, trigger, description)
    ```

19. **Collect: examples (Optional)**
    ```
    Want to add usage examples?
    - name, scenario, trigger, input, output, explanation
    ```

20. **Collect: _meta (Optional)**
    ```
    Any meta configuration?
    - content_language: en | zh | auto
    - format: full | minimal
    - token_budget: target word count for SKILL.md (default: 500)
    - agentskills_compat: enable strict agentskills.io validation? (true/false)
    - progressive_disclosure: token budgets for metadata/instructions/lines?
    ```

21. **Generate and Review**
    - Generate complete spec.yaml with all collected info
    - Include `spec_version: "skill-spec/1.2"`
    - Show spec to user in code block
    - Ask: "Does this look correct? Any adjustments?"
    - Make adjustments if requested

22. **Write spec.yaml**
    - Create directory: `skillspec/drafts/<name>/`
    - Write spec.yaml to the directory

23. **Lint YAML format** (CRITICAL - prevents format errors)
    ```bash
    skillspec lint <name>
    ```
    - If lint fails with YAML syntax error:
      - DO NOT proceed to validation
      - Re-read the spec.yaml file you just wrote
      - Fix the YAML syntax issues (usually indentation)
      - Re-write the fixed content
      - Run lint again until it passes
    - If lint passes, proceed to validation

24. **Run strict validation**
    ```bash
    skillspec validate <name> --strict
    ```

25. **Parse and explain validation results**
    For each error/warning, explain which layer:
    - **Layer 1 (Schema)**: Missing required fields, type mismatches
    - **Layer 2 (Quality)**: Forbidden patterns, vague language
    - **Layer 3 (Coverage)**: Uncovered failure modes, missing edge cases
    - **Layer 4 (Consistency)**: Cross-reference issues, broken step chains
    - **Layer 5 (Compliance)**: Policy violations (if configured)

26. **Provide fix suggestions**
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

27. **Auto-fix common issues**
    - Missing `is_default: true` on fallback rule
    - Missing edge cases for defined failure modes
    - Missing required sections with sensible defaults

28. **Re-validate until passing**
    - If fixes applied, re-run validation
    - Repeat until all errors resolved

29. **Show completion summary**
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

**Field Reference (v1.2)**

```yaml
spec_version: "skill-spec/1.2"

_meta:                              # optional
  content_language: en | zh | auto
  mixed_language_strategy: union | segment_detect | primary
  format: full | minimal
  token_budget: 500                 # target word count for SKILL.md
  agentskills_compat: false         # v1.2: enable agentskills.io validation
  progressive_disclosure:           # v1.2: token budgets (agentskills.io pattern)
    metadata_tokens: 100            # ~100 tokens for metadata
    instructions_tokens: 2000       # <5000 tokens for instructions
    max_lines: 500                  # <500 lines for SKILL.md

skill:                              # required
  name: kebab-case                  # 1-64 chars, ^[a-z][a-z0-9]*(-[a-z0-9]+)*$
  version: "1.0.0"                  # semver
  purpose: string                   # 10-1024 chars (agentskills.io: 'description')
  owner: string
  category: string                  # documentation|analysis|generation|...
  complexity: string                # low|standard|advanced
  tools_required: [string]          # file_read, file_write, search, web_access, etc.
  personas: [string]                # developer, architect, etc.
  # v1.2 agentskills.io fields
  license: string                   # SPDX identifier (e.g., "Apache-2.0", "MIT")
  compatibility: string             # environment requirements (max 500 chars)
  allowed_tools: [string]           # pre-approved tools (experimental)
  metadata: {key: value}            # custom properties

triggers:                           # from Superpowers
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

boundaries:                         # from SuperClaude
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
    tool_binding:                   # v1.2: optional concrete tool binding
      tool: string                  # tool name (Read, Write, Bash, Grep, etc.)
      params: {key: value}          # parameters, supports {{ input.var }} syntax
      timeout: int                  # optional, 1000-600000 ms
      on_error: string              # fail | skip | retry | <FAILURE_CODE>

tools:                              # v1.2: optional, for custom MCP tools
  - name: string                    # tool name
    description: string             # what the tool does
    params:                         # tool parameters
      - name: string
        type: string|number|boolean|object|array
        required: boolean
        description: string
        default: any
    returns: string                 # return value description
    requires_approval: boolean      # default: false
    sandbox_safe: boolean           # default: true

behavioral_flow:                    # from SuperClaude, optional
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

anti_patterns:                      # from Superpowers, optional
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
  scenarios: [{name, trigger, description}]

examples:                           # optional
  - name: string
    scenario: string
    trigger: string
    input: any
    output: any
    explanation: string             # optional
```

**v1.2 New Fields Quick Reference (agentskills.io)**

| Field | Location | Purpose |
|-------|----------|---------|
| `license` | skill | SPDX license identifier |
| `compatibility` | skill | Environment requirements (max 500 chars) |
| `allowed_tools` | skill | Pre-approved tools for execution |
| `metadata` | skill | Custom key-value properties |
| `agentskills_compat` | _meta | Enable strict agentskills.io validation |
| `progressive_disclosure` | _meta | Token budgets for disclosure levels |
| `tool_binding` | steps[] | Concrete tool binding for step execution |
| `tools` | root | Custom MCP tool definitions |

**Standard Tools Reference**

Available tools for `tool_binding` (no declaration needed):

| Tool | Category | Description |
|------|----------|-------------|
| `Read` | File System | Read file contents |
| `Write` | File System | Write content to file |
| `Edit` | File System | Replace text in file |
| `Glob` | Search | Find files by pattern |
| `Grep` | Search | Search file contents |
| `Bash` | Execution | Execute shell commands |
| `Task` | Execution | Launch sub-agent |
| `WebFetch` | Web | Fetch URL content |
| `WebSearch` | Web | Search the web |
| `AskUserQuestion` | Interaction | Ask user questions |
| `TodoWrite` | Interaction | Manage task list |
| `NotebookEdit` | Notebook | Edit Jupyter cells |

**v1.1 Sections Quick Reference**

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
