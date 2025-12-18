# 📋 Skill-Spec: The Industrial-Grade Claude Skill Factory

**Turn Vague "Vibes" into Industrial-Grade, Interactive, Bulletproof Artifacts.**

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

### 🧠 The Core Philosophy

We believe in the "Do vs. Don't" paradigm:

| The Old Way (Vague Guidance) | The Skill-Spec Way (Specific Specs) |
|------------------------------|-------------------------------------|
| "Be helpful and concise." | **Forbidden Pattern Scan:** Reject "filler words". |
| "Handle errors." | **Mandatory Edge Cases:** Define logic for timeouts & bad data. |
| "Output the result." | **Output Contract:** Enforce strict JSON Schema. |

---

## ⚡ The Gap: Static Prompts vs. Living Skills

You don’t need another "system prompt." You need a **Tool**. Standard prompts are passive—they wait for input and hope for the best.

* **The "Yes-Man" Problem:** You ask for a critique; the AI just compliments you.
* **The Context Black Hole:** One complex request later, the AI forgets constraints.
* **Zero Interactivity:** The AI guesses what you mean instead of asking.

---

## 🏭 The Factory: We Build "Artifacts," Not Just Text.

**Skill-Spec** is your dedicated **Claude Skill Manufacturing Plant**. We treat Prompt Engineering as **Software Engineering**. You give us the raw intent; we manufacture a deployed **Interactive Skill** ready for your Claude Projects.

### 🎮 Why "Interactive" Matters?
A Skill-Spec generated skill isn't a passive responder; it is an **Active Partner**.

1.  **The Interviewer Mode:** If input is vague, the Skill halts execution and interviews *you*.
2.  **The Guardrail Enforcer:** It actively rejects inputs that violate the schema *before* processing.
3.  **The Step-by-Step Navigator:** It guides users through complex workflows.

---

## 🔥 Extreme Examples: From Vague to Industrial

See the difference between a "Chat" and a "Skill-Spec Artifact":

### Case 1: The Code Reviewer
| The "Vibes" Approach | The Skill-Spec Artifact |
| :--- | :--- |
| **User:** "Review this code." | **Trigger:** `run_architecture_audit` |
| **AI:** "Looks good! Maybe add comments." | **Protocol:**<br>1. **Scan:** Identify Dependency Inversion violations.<br>2. **Reject:** If no unit tests, **STOP** and request them.<br>3. **Output:** Generate Markdown table classifying risks.<br>4. **Interactive:** "Found security flaw. Want me to write a patch?" |

### Case 2: The PR/Marketing Writer
| The "Vibes" Approach | The Skill-Spec Artifact |
| :--- | :--- |
| **User:** "Write a press release." | **Trigger:** `generate_press_kit` |
| **AI:** *Writes generic fluff with emojis.* | **Protocol:**<br>1. **Interview:** "Who is the target audience? What is the USP?"<br>2. **Forbidden Patterns:** Ban words like "Revolutionary," "Game-changing."<br>3. **Critique:** Self-grade draft against viral hooks. |

---

## 🚀 Quick Start

Don't just write a prompt. Build a Skill.

### Installation

```bash
# Clone the repository
git clone https://github.com/bethneyQQ/skill-spec/skill-spec.git
cd skill-spec

# Install from source
pip install -e .
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
