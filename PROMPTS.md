You are a senior software engineer preparing this repository to be shown publicly on GitHub.

Goal:
Make the repository look clean, professional, and easy to understand without changing the actual project implementation.

Strict rules:
- Do NOT modify source code behavior
- Do NOT refactor the application
- Do NOT delete files automatically
- Do NOT aggressively reorganize the project
- Be conservative and minimal
- If a change is uncertain, only suggest it

Tasks:
1. Audit the repository structure
- Identify obvious unused, duplicate, temporary, or obsolete files
- Identify missing files such as README.md, .gitignore, LICENSE, CONTRIBUTING.md, AGENTS.md, CLAUDE.md, docs/
- Check whether the folder structure is understandable and professional
- Suggest only simple and safe improvements

2. Review repository hygiene
- Check .gitignore and suggest missing entries
- Check requirements.txt / package.json and suggest only obvious missing or obsolete dependencies
- Detect obvious bad file names such as final.py, test2.py, old_version, temp, etc.
- Suggest better names without renaming automatically

3. Rewrite or create documentation in English
Create or improve:
- README.md
- AGENTS.md
- CLAUDE.md
- docs/ARCHITECTURE.md if useful
- docs/DEVELOPMENT.md if useful

Documentation rules:
- Keep files short, practical, and repository-specific
- No generic AI wording or marketing language
- Focus on what the project does, how it is structured, and how to work on it
- Add 3 to 6 professional GitHub badges at the top of README
- Add contributors if they can be inferred, otherwise create a placeholder section

AGENTS.md should contain:
- repository structure
- commands to run/test/build
- engineering rules
- git workflow
- what an agent must never do

CLAUDE.md should contain:
- short operational rules for Claude or coding agents
- minimal, safe, targeted changes only
- never put business logic in UI
- respect architecture and naming conventions
- use small commits and work on feature branches

4. Output
Return only:
- short audit summary
- files to create or update
- suggested deletions only (do not delete automatically)
- complete content for the new documentation files
- optional .gitignore and requirements.txt updates

#########################################################
#######################################################
#########################################################

You are a professional software architect and technical writer.

Your task is to prepare this repository for a public GitHub portfolio.

Important:
- Preserve the current project exactly as it is
- Do not rewrite or heavily refactor code
- Do not remove dead code unless it is clearly safe and explicitly approved
- Focus on repository quality, documentation, and presentation

Process:
1. Analyze the repository and infer:
- project purpose
- tech stack
- folder structure
- current architecture
- whether the repo already looks professional or not

2. Produce a concise repository audit:
- files that are probably obsolete or useless
- missing documentation
- missing support files
- unclear names or structure
- missing .gitignore entries
- missing license, contributors, or screenshots section

3. Create or rewrite these files if needed:
- README.md
- AGENTS.md
- CLAUDE.md
- CONTRIBUTING.md
- docs/ARCHITECTURE.md
- docs/DEVELOPMENT.md

README requirements:
- project title
- one-sentence summary
- 3–6 clean GitHub badges
- project purpose
- main features
- technologies
- install and usage instructions
- repository tree overview
- contributors
- limitations
- optional screenshots/demo placeholder
- short roadmap if useful

AGENTS.md requirements:
- short and strict
- explain repository structure
- explain run/test/build commands
- explain git workflow and commit style
- explain architectural rules:
  - no business logic in UI
  - services separated from persistence
  - minimal and targeted changes only

CLAUDE.md requirements:
- very short
- operational instructions only
- behave like a professional engineer
- preserve architecture
- avoid broad refactors
- make small commits on dedicated branches

Writing style:
- Professional English
- Short and practical
- No unnecessary verbosity
- No fake claims or generic buzzwords

At the end, provide:
- final audit summary
- exact files to create or update
- exact optional file deletions
- full content of all documentation files
- recommended repository description
- 5 GitHub topics/tags