# PowerKPI_AI

> **AI-powered skills and workload definitions for the PowerKPI agent**

PowerKPI_AI is the central repository for defining, organizing, and sharing the **SKILLS** that power the PowerKPI AI agent. The `main` branch holds the general-purpose skill definitions that any branch can import and extend for specific workloads or debug scenarios.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [How to Download / Clone This Repo](#how-to-download--clone-this-repo)
- [Using Skills](#using-skills)
- [Creating Branch-Specific Skills](#creating-branch-specific-skills)
- [Contributing](#contributing)

---

## Overview

PowerKPI_AI organizes AI agent capabilities into **SKILLS** — structured, reusable definitions that describe what the agent can do and how it should behave across different workloads. Each skill covers:

- **Purpose** – what the skill does
- **Trigger conditions** – when the skill should activate
- **Inputs & Outputs** – what data it consumes and produces
- **Steps** – the reasoning or action steps the agent follows
- **Integration points** – which PowerKPI components it interacts with

The `main` branch contains the **general-purpose skill library** shared across all workloads. Individual feature branches extend or customize these skills for specialized scenarios (e.g., specific debug workflows, customer-specific configurations).

---

## Repository Structure

```
PowerKPI_AI/
├── README.md                   ← You are here
└── skills/
    ├── README.md               ← Skills system overview & index
    ├── general_skills.md       ← General PowerKPI workload skill definitions
    ├── skills_template.md      ← Template for creating new skills
    └── custom/
        └── debug_skills.md     ← Example: branch-specific debug skills (imports from general)
```

When creating a new feature or debug branch, add a folder under `skills/custom/` (or create a new subdirectory) and import/reference the general skills you need.

---

## How to Download / Clone This Repo

### Prerequisites

- [Git](https://git-scm.com/downloads) installed on your machine
- (Optional) [GitHub CLI](https://cli.github.com/) for easier authentication

### Clone via HTTPS

```bash
git clone https://github.com/tonyintel010626/PowerKPI_AI.git
cd PowerKPI_AI
```

### Clone via SSH

```bash
git clone git@github.com:tonyintel010626/PowerKPI_AI.git
cd PowerKPI_AI
```

### Clone via GitHub CLI

```bash
gh repo clone tonyintel010626/PowerKPI_AI
cd PowerKPI_AI
```

### Download as ZIP (no Git required)

1. Navigate to the repository on GitHub: `https://github.com/tonyintel010626/PowerKPI_AI`
2. Click the green **Code** button
3. Select **Download ZIP**
4. Extract the ZIP to your preferred location

### Fetching a Specific Branch

To work on or inspect a specific skills branch:

```bash
# After cloning, switch to a specific branch
git checkout <branch-name>

# Or clone a specific branch directly
git clone --branch <branch-name> https://github.com/tonyintel010626/PowerKPI_AI.git
```

---

## Using Skills

Skills are defined as Markdown documents inside the `skills/` directory. Each skill file contains structured sections that the PowerKPI AI agent reads at runtime to determine how to perform a workload.

To use the general skills in this repo:

1. Clone the repository (see above)
2. Browse `skills/general_skills.md` for the full catalog of available skills
3. Reference a skill by its **Skill ID** when configuring the AI agent

Example reference in your agent configuration:

```yaml
# agent-config.yaml
skills:
  - source: main          # pull from main branch general skills
    id: PKPI-SKL-001       # KPI Data Retrieval
  - source: main
    id: PKPI-SKL-003       # Anomaly Detection
```

---

## Creating Branch-Specific Skills

Feature branches can **import** general skills from `main` and then **extend or override** them for specific needs (e.g., debug workflows, customer environments).

### Steps

1. **Create a new branch** from `main`:
   ```bash
   git checkout main
   git pull
   git checkout -b feature/my-debug-skills
   ```

2. **Create a custom skills file** under `skills/custom/`:
   ```bash
   cp skills/skills_template.md skills/custom/my_debug_skills.md
   ```

3. **Reference general skills** at the top of your custom file using the `imports` header:
   ```markdown
   ## Imports
   - `main::PKPI-SKL-001`  # KPI Data Retrieval
   - `main::PKPI-SKL-004`  # Log Analysis
   ```

4. **Define your customizations** below the imports, overriding or extending as needed.

5. **Push your branch** and open a PR when ready:
   ```bash
   git add skills/custom/my_debug_skills.md
   git commit -m "Add custom debug skills for <scenario>"
   git push origin feature/my-debug-skills
   ```

See `skills/custom/debug_skills.md` for a full worked example.

---

## Contributing

1. Fork the repository and clone your fork locally
2. Create a new branch: `git checkout -b feature/your-skill`
3. Add or update skill definitions following the format in `skills/skills_template.md`
4. Commit your changes with a descriptive message
5. Push to your fork and open a Pull Request against `main`

All new general-purpose skills belong in `skills/general_skills.md`. Workload-specific or debug-specific skills go in `skills/custom/` on a dedicated branch.

