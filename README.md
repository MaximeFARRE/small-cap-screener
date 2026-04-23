````md id="zj87l1"
# Project Name

Short one-sentence description of the project.

> Example: A desktop application to track personal finances, investments, and long-term goals.

---

## Features

- Main feature 1
- Main feature 2
- Main feature 3
- Optional advanced feature

---

## Screenshots

<!-- Add screenshots in /screenshots -->

### Main page

![Main page](screenshots/main-page.png)

### Example feature

![Feature example](screenshots/feature-example.png)

---

## Tech Stack

- Language:
- Framework:
- Database:
- Styling:
- Testing:
- Other tools:

Example:

```text id="g1szlw"
- Python
- PyQt6
- SQLite
- pytest
- GitHub Actions
````

---

## Project Structure

```text id="ndq7hi"
project-name/
├── src/
├── tests/
├── docs/
├── assets/
├── screenshots/
├── README.md
├── AGENTS.md
├── CLAUDE.md
└── CONTRIBUTING.md
```

---

## Architecture

```text id="jl0z3v"
UI / Components
        ↓
Services / Business Logic
        ↓
Repositories / Database / API
```

Rules:

* No business logic in UI files
* No database access in UI files
* Reuse services before creating new ones
* Keep responsibilities separated

More details: see `docs/ARCHITECTURE.md`

---

## Installation

### Clone the repository

```bash id="onx4st"
git clone <repository-url>
cd <repository-name>
```

### Setup

#### Python example

```bash id="lh2r4q"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Node.js example

```bash id="o3mdqu"
npm install
npm run dev
```

Replace these commands depending on the project.

---

## Usage

```bash id="7m3z3w"
# Example
python main.py
```

or

```bash id="dtx9xt"
npm run dev
```

Explain here how to launch and use the project.

---

## Roadmap

* [ ] Add feature X
* [ ] Improve performance
* [ ] Add tests
* [ ] Improve documentation

See `docs/ROADMAP.md` for more details.

---

## Contributing

Contributions are welcome.

Please read:

* `CONTRIBUTING.md`
* `AGENTS.md`
* `CLAUDE.md`

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

```
```
