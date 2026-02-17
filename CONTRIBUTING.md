# Contributing to Altitude Early Warning

Welcome! This guide will help you set up, run, and contribute to the project.

## Quick Start
1. Clone the repo and enter the directory.
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install -e '.[dev,api]'
   # Or: python3 -m pip install -r requirements.txt
   ```
4. Build data and run tests:
   ```bash
   make build-data
   make test
   ```
5. Run the demo UI:
   ```bash
   ./scripts/run_demo_ui.sh
   ```

## How to Contribute
- Fork the repo and create a feature branch.
- Follow code comment and style guidelines (see DEVELOPER_GUIDE.md).
- Add or update tests for your changes.
- Submit a pull request with a clear description.

## Project Structure
- See DEVELOPER_GUIDE.md for code map and data schema.
- See DESIGN_GUIDE.md for UI/UX and design standards.

## Code of Conduct
- Be respectful and collaborative.
- See CODE_OF_CONDUCT.md (if present).

---
For more, see docs/DEMO_GUIDE.md and docs/RUNBOOK.md.
