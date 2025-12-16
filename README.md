## 📋 Skill-Spec —— The Factory for Claude Skills

**Turn Vague "Vibes" into Industrial-Grade Agent Skills.**

---

## ⚡ The Problem: "It works on my machine... sometimes."

Building LLM Agents is easy. Building reliable LLM Agents is a nightmare. You know the drill:

- **Vague Instructions**: "Write a summary" leads to random results.
- **Fragile Logic**: The agent crashes on edge cases.
- **Spaghetti State**: Context gets lost in a sea of unstructured dictionaries.
- **Happy Path Only**: It works for the demo, but fails in production.

---

## 🛠️ The Solution: Engineering, not Alchemy.

Skill-Spec is the "Adult in the Room" for your AI workflow. It forces LLMs to adhere to strict Quality Standard Alignment. We don't just "prompt" models; we architect behaviors.

This is a framework for **Defensive Agent Engineering**.

---

## 🔥 Why Skill-Spec?

### 🛡️ The "Skill Architect" Protocol

Stop guessing. We transform natural language into rigorous specifications.

**From:** "Check the weather."

**To:** A 4-step execution plan with defined inputs, decision_rules, forbidden_patterns, and mandatory edge_case handling.

**The Result:** Zero Hallucination, 100% Schema Compliance.

---

## 🧠 The Core Philosophy

We believe in the "Do vs. Don't" paradigm:

| The Old Way (Vague Guidance) | The Skill-Spec Way (Specific Specs) |
|------------------------------|-------------------------------------|
| "Be helpful and concise." | Forbidden Pattern Scan: Reject "filler words". |
| "Handle errors." | Mandatory Edge Cases: Define logic for timeouts & bad data. |
| "Output the result." | Output Contract: Enforce strict JSON Schema. |

---

## 🚀 Quick Start

Don't just write a prompt. Build a Skill.

### Installation

```bash
# Clone the repository
git clone https://github.com/bethneyQQ/skill-spec/skill-spec.git
cd skill-spec

# Install from source
pip install -e
```

### Setup in Your Project

```bash
cd my-project
skillspec setup
```

This command automatically:
- Detects your AI tools (Claude Code, Cursor, Cline, Codex)
- Creates `skillspec/` directory structure
- Installs slash commands for interactive skill creation
- Creates `project.yaml` for configuration

### Create Your First Skill

In Claude Code (or your AI tool), type:

```
/skill-spec:proposal my-skill
```

The AI will:
1. Ask about purpose, inputs, decision rules, edge cases
2. Generate complete `spec.yaml` from your answers
3. Validate with `--strict` and save to `skillspec/drafts/my-skill/`

---

## ⚙️ How It Works

```
skillspec setup              # Initialize project
       |
       v
/skill-spec:proposal <name>  # AI-assisted creation + validation
       |
       v
/skill-spec:apply <name>     # Generate SKILL.md
       |
       v
/skill-spec:deploy <name>    # Publish skill
```

---

## 💬 Slash Commands (AI-Assisted)

| Command | Description |
|---------|-------------|
| `/skill-spec:proposal <name>` | Interactive skill creation + validation |
| `/skill-spec:apply <name>` | Generate SKILL.md from spec |
| `/skill-spec:deploy <name>` | deploy your skill to dir/ eg. .claude/skills |
| `/skill-spec:migrate <path>` | Migrate existing skill |

---

## 🖥️ Main CLI Commands

| Command | Description |
|---------|-------------|
| `skillspec setup` | Initialize project |
| `skillspec list` | List all skills |
| `skillspec validate <name> --strict` | Validate spec |
| `skillspec report <name>` | Quality report (text output) |
| `skillspec report <name> --format json` | Quality report (JSON output) |
| `skillspec report <name> --format markdown` | Quality report (Markdown output) |
| `skillspec convert-report <json>` | Convert JSON report to Markdown |

---

## 📁 Directory Structure

```
my-project/
+-- .claude/commands/skill-spec/   # Slash commands
+-- skillspec/
|   +-- drafts/                    # Work in progress
|   +-- skills/                    # Published
+-- project.yaml                   # Configuration
```

---

## 🎯 Design Goals

### Level 1: Platform Quality

- **Mandatory Section Taxonomy**: 8 Core + 1 Coverage sections
- **Forbidden Pattern Detection**: Catches vague language
- **Coverage Analysis**: Ensures complete specification
- **Consistency Validation**: Cross-references all components

### Level 2: User Quality

- **Structured Templates**: Pre-defined spec.yaml templates
- **Clear Validation Feedback**: Actionable error messages
- **Quality Reports**: Structural and behavioral coverage scores
- **Migration Tools**: Convert existing SKILL.md files

### Level 3: Enterprise Quality

- **Custom Policy Rules**: Organization-specific requirements
- **Tag Taxonomy**: Data classification (PII, financial, auth)
- **Compliance Validation**: GDPR, security rules
- **Audit Evidence**: Diary system for compliance audits
---

## ✅ Validation Layers

```
spec.yaml
    |
    v
Layer 1: Schema       # Structure, required fields
    |
    v
Layer 2: Quality      # Forbidden patterns
    |
    v
Layer 3: Coverage     # Edge cases, decision rules
    |
    v
Layer 4: Consistency  # Cross-references
    |
    v
Layer 5: Compliance   # Enterprise policies (optional)
```

---

## 🌐 Multi-Language Support

```bash
# Chinese output
skillspec --locale=zh validate my-skill

# Chinese patterns
skillspec --patterns=zh validate my-skill

# Combined patterns (strictest)
skillspec --patterns=union validate my-skill
```

Configuration in `project.yaml`:

```yaml
skill_spec:
  report_locale: en        # en | zh
  patterns_locale: union   # en | zh | union
  template_locale: en      # en | zh
```

---

## 📄 License

MIT
