# SWE Workflow

The [swe-workflow](https://github.com/lydiym/swe-workflow) CLI is an open source coding assistant that runs in your terminal, similar to Claude Code.

**Key Features:**

- **Built-in Tools**: File operations (read, write, edit, glob, grep), shell commands, and subagent delegation
- **Customizable Skills**: Add domain-specific capabilities through a progressive disclosure skill system
- **Persistent Memory**: Agent remembers your preferences, coding style, and project context across sessions
- **Project-Aware**: Automatically detects project roots and loads project-specific configurations

## Quickstart

`swe-workflow` is a Python package that can be installed via pip or uv.

**Install via pip:**

```bash
pip install swe-workflow
```

**Or using uv (recommended):**

```bash
# Create a virtual environment
uv venv

# Install the package
uv pip install swe-workflow
```

**Run the agent in your terminal:**

```bash
swe-workflow
```

**Get help:**

```bash
swe-workflow help
```

**Common options:**

```bash
# Use a specific agent configuration
swe-workflow --agent mybot

# Use a specific model (auto-detects provider)
swe-workflow --model claude-sonnet-4-5-20250929
swe-workflow --model gpt-4o

# Auto-approve tool usage (skip human-in-the-loop prompts)
swe-workflow --auto-approve

```

Type naturally as you would in a chat interface. The agent will use its built-in tools, skills, and memory to help you with tasks.

## Model Configuration

The CLI supports OpenAI, Anthropic, Google, and OpenAI-compatible APIs. It automatically selects a provider based on which API keys are available. If multiple keys are set, it uses the first match in this order:

| Priority | API key                 | Default model                         |
| -------- | ----------------------- | ------------------------------------- |
| 1st      | `OPENAI_COMPATIBLE_URL` | `llama3` (with OpenAI-compatible API) |
| 2nd      | `OPENAI_API_KEY`        | `gpt-5-mini`                          |
| 3rd      | `ANTHROPIC_API_KEY`     | `claude-sonnet-4-5-20250929`          |
| 4th      | `GOOGLE_API_KEY`        | `gemini-3-pro-preview`                |

To use a different model, pass the `--model` flag:

```bash
# Cloud models
swe-workflow --model claude-opus-4-5-20251101
swe-workflow --model gpt-4o
swe-workflow --model gemini-2.5-pro

# OpenAI-compatible models
swe-workflow --openai-compatible-url http://localhost:11434/v1 --model qwen3-next
swe-workflow --openai-compatible-url http://localhost:11434/v1 --model devstrall-small-2
```

The CLI auto-detects the provider from the model name and requires the corresponding API key. The active model is displayed at startup.

**Model name conventions:**

- **OpenAI**: See [OpenAI Models Documentation](https://platform.openai.com/docs/models)
- **Anthropic**: See [Anthropic Models Documentation](https://docs.anthropic.com/en/docs/about-claude/models)
- **Google**: See [Google Gemini Models Documentation](https://ai.google.dev/gemini-api/docs/models/gemini)
- **OpenAI-Compatible APIs**: Use any model name directly when OpenAI-compatible settings are configured (e.g., via `--openai-compatible-url` or `OPENAI_COMPATIBLE_URL` environment variable)

## OpenAI-Compatible API Support

SWE-Workflow CLI now supports OpenAI-compatible APIs, allowing you to use private models with Ollama, LocalAI, vLLM, and other compatible servers.

### Quick Start with Ollama

1. **Install Ollama** from [ollama.ai](https://ollama.ai)
2. **Start Ollama server**: `ollama serve`
3. **Pull a model**: `ollama pull llama3`
4. **Run with OpenAI-compatible API**:

   ```bash
   export OPENAI_COMPATIBLE_URL=http://localhost:11434/v1
   swe-workflow --model ollama:llama3
   ```

   Or use the command line option directly:

   ```bash
   swe-workflow --openai-compatible-url http://localhost:11434/v1 --model llama3
   ```

### Configuration Options

**Environment Variables:**

```bash
# Required: URL for the OpenAI-compatible API
export OPENAI_COMPATIBLE_URL=http://localhost:11434/v1  # Ollama default

# Optional: API key (defaults to "sk-openai-compatible" if not set)
export OPENAI_COMPATIBLE_API_KEY=your-api-key-here


```

**Command Line Arguments:**

```bash
# Specify OpenAI-compatible API URL and model (recommended approach)
swe-workflow --openai-compatible-url http://localhost:11434/v1 --model llama3

# Or configure via environment variables and use model names directly
export OPENAI_COMPATIBLE_URL=http://localhost:11434/v1
swe-workflow --model llama3

# Alternative prefixes still work for backward compatibility
swe-workflow --model local:llama3
swe-workflow --model ollama:mistral
```

## Built-in Tools

The agent comes with the following built-in tools (always available without configuration):

| Tool          | Description                                       |
| ------------- | ------------------------------------------------- |
| `ls`          | List files and directories                        |
| `read_file`   | Read contents of a file                           |
| `write_file`  | Create or overwrite a file                        |
| `edit_file`   | Make targeted edits to existing files             |
| `glob`        | Find files matching a pattern (e.g., `**/*.py`)   |
| `grep`        | Search for text patterns across files             |
| `shell`       | Execute shell commands (local mode)               |
| `fetch_url`   | Fetch and convert web pages to markdown           |
| `task`        | Delegate work to subagents for parallel execution |
| `write_todos` | Create and manage task lists for complex work     |

> [!WARNING]
> **Human-in-the-Loop (HITL) Approval Required**
>
> Potentially destructive operations require user approval before execution:
>
> - **File operations**: `write_file`, `edit_file`
> - **Command execution**: `shell`
> - **External requests**: `fetch_url`
> - **Delegation**: `task` (subagents)
>
> Each operation will prompt for approval showing the action details. Use `--auto-approve` to skip prompts:
>
> ```bash
> swe-workflow --auto-approve
> ```

## Agent Configuration

Each agent has its own configuration directory at `~/.swe-workflow/<agent_name>/`, with default `agent`.

```bash
# List all configured agents
swe-workflow list

# Create a new agent
swe-workflow create <agent_name>
```

## Customization

There are two primary ways to customize any agent: **memory** and **skills**.

Each agent has its own global configuration directory at `~/.swe-workflow/<agent_name>/`:

```
~/.swe-workflow/<agent_name>/
  ├── AGENTS.md              # Auto-loaded global personality/style
  └── skills/               # Auto-loaded agent-specific skills
      ├── code-review/
      │   └── SKILL.md
      └── langgraph-docs/
          └── SKILL.md
```

Projects can extend the global configuration with project-specific instructions and skills:

```
my-project/
  ├── .git/
  └── .swe-workflow/
      ├── AGENTS.md          # Project-specific instructions
      └── skills/           # Project-specific skills
          └── custom-tool/
              └── SKILL.md
```

The CLI automatically detects project roots (via `.git`) and loads:

- Project-specific `AGENTS.md` from `[project-root]/.swe-workflow/AGENTS.md`
- Project-specific skills from `[project-root]/.swe-workflow/skills/`

Both global and project configurations are loaded together, allowing you to:

- Keep general coding style/preferences in global AGENTS.md
- Add project-specific context, conventions, or guidelines in project AGENTS.md
- Share project-specific skills with your team (committed to version control)
- Override global skills with project-specific versions (when skill names match)

### AGENTS.md files

`AGENTS.md` files provide persistent memory that is always loaded at session start. Both global and project-level `AGENTS.md` files are loaded together and injected into the system prompt.

**Global `AGENTS.md`** (`~/.swe-workflow/agent/AGENTS.md`)

- Your personality, style, and universal coding preferences
- General tone and communication style
- Universal coding preferences (formatting, type hints, etc.)
- Tool usage patterns that apply everywhere
- Workflows and methodologies that don't change per-project

**Project `AGENTS.md`** (`.swe-workflow/AGENTS.md` in project root)

- Project-specific context and conventions
- Project architecture and design patterns
- Coding conventions specific to this codebase
- Testing strategies and deployment processes
- Team guidelines and project structure

**How it works:**

- Loads memory files at startup and injects into system prompt as `<agent_memory>`
- Includes guidelines on when/how to update memory files via `edit_file`

**When the agent updates memory:**

- IMMEDIATELY when you describe how it should behave
- IMMEDIATELY when you give feedback on its work
- When you explicitly ask it to remember something
- When patterns or preferences emerge from your interactions

The agent uses `edit_file` to update memories when learning preferences or receiving feedback.

### Project memory files

Beyond `AGENTS.md`, you can create additional memory files in `.swe-workflow/` for structured project knowledge. These work similarly to [Anthropic's Memory Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool). The agent receives instructions on when to read and update these files.

**How it works:**

1. Create markdown files in `[project-root]/.swe-workflow/` (e.g., `api-design.md`, `architecture.md`, `deployment.md`)
2. The agent checks these files when relevant to a task (not auto-loaded into every prompt)
3. The agent uses `write_file` or `edit_file` to create/update memory files when learning project patterns

**Example workflow:**

```bash
# Agent discovers deployment pattern and saves it
.swe-workflow/
├── AGENTS.md           # Always loaded (personality + conventions)
├── architecture.md    # Loaded on-demand (system design)
└── deployment.md      # Loaded on-demand (deploy procedures)
```

**When the agent reads memory files:**

- At the start of new sessions (checks what files exist)
- Before answering questions about project-specific topics
- When you reference past work or patterns
- When performing tasks that match saved knowledge domains

**Benefits:**

- **Persistent learning**: Agent remembers project patterns across sessions
- **Team collaboration**: Share project knowledge through version control
- **Contextual retrieval**: Load only relevant memory when needed (reduces token usage)
- **Structured knowledge**: Organize information by domain (APIs, architecture, deployment, etc.)

### Skills

Skills are reusable agent capabilities that provide specialized workflows and domain knowledge. Example skills are provided in the `examples/skills/` directory:

- **code-review** - Automated code review workflow with best practices and error detection
- **langgraph-docs** - LangGraph documentation lookup and guidance

To use an example skill globally with the default agent, just copy them to the agent's skills global or project-level skills directory:

```bash
mkdir -p ~/.swe-workflow/agent/skills
cp -r examples/skills/code-review ~/.swe-workflow/agent/skills/
```

To manage skills:

```bash
# List all skills (global + project)
swe-workflow skills list

# List only project skills
swe-workflow skills list --project

# Create a new global skill from template
swe-workflow skills create my-skill

# Create a new project skill
swe-workflow skills create my-tool --project

# View detailed information about a skill
swe-workflow skills info code-review

# View info for a project skill only
swe-workflow skills info my-tool --project
```

To use skills (e.g., the langgraph-docs skill), just type a request relevant to a skill and the skill will be used automatically.

```bash
swe-workflow
"create a agent.py script that implements a LangGraph agent"
```

Skills follow Anthropic's [progressive disclosure pattern](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - the agent knows skills exist but only reads full instructions when needed.

1. **At startup** - SkillsMiddleware scans `~/.swe-workflow/agent/skills/` and `.swe-workflow/skills/` directories
2. **Parse metadata** - Extracts YAML frontmatter (name + description) from each `SKILL.md` file
3. **Inject into prompt** - Adds skill list with descriptions to system prompt: "Available Skills: code-review - Use for code review tasks..."
4. **Progressive loading** - Agent reads full `SKILL.md` content with `read_file` only when a task matches the skill's description
5. **Execute workflow** - Agent follows the step-by-step instructions in the skill file

## Development

### Running Tests

To run the test suite:

```bash
uv sync --all-groups

make test
```

### Running During Development

```bash
# From libs/swe-workflow directory
uv run swe-workflow

# Or install in editable mode
uv pip install -e .
swe-workflow
```

### Modifying the CLI

- **UI changes** → Edit `ui.py` or `input.py`
- **Add new tools** → Edit `tools.py`
- **Change execution flow** → Edit `execution.py`
- **Add commands** → Edit `commands.py`
- **Agent configuration** → Edit `agent.py`
- **Skills system** → Edit `skills/` modules
- **Constants/colors** → Edit `config.py`
