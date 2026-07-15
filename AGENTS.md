# Repository Guidelines

## Project Structure & Module Organization

`aesthepdf/` is the distributable Agent Skill. Its main entry point is `aesthepdf/scripts/render.py`, which converts Markdown through Pandoc and Chromium. Shared HTML, CSS, and Lua filters live in `aesthepdf/assets/`; each layout has `themes/<id>/style.css` and `theme.json`. Use `templates/*-sample.md` as executable examples, and keep bundled typefaces in `fonts/`. User-facing guidance is split across `SKILL.md`, `composition.md`, `examples.md`, and `reference.md`. Root `scripts/` contains maintenance utilities, while `images/` holds README artwork. Treat `aesthepdf_output/` as generated/scratch output, not source.

## Build, Test, and Development Commands

Run commands from the repository root:

```bash
pip install -r aesthepdf/scripts/requirements.txt
python -m playwright install chromium
python aesthepdf/scripts/render.py --list-themes
python aesthepdf/scripts/render.py aesthepdf/templates/academic-sample.md -o aesthepdf_output/academic.pdf --theme academic
```

Pandoc 3.x must also be available on `PATH`. The first two commands install Python and browser dependencies; `--list-themes` is a quick environment check; the final command performs an end-to-end render. There is no separate build step—the `aesthepdf/` directory is the shipped artifact.

## Coding Style & Naming Conventions

Follow the existing Python style: four-space indentation, type hints, `snake_case` functions and variables, and `UPPER_SNAKE_CASE` constants. Keep functions focused and use `pathlib.Path` for filesystem work. CSS uses two-space indentation, kebab-case classes/custom properties, and shared rules in `assets/`; theme-specific rules belong under `themes/<id>/`. Name new themes and sample files with lowercase kebab-case identifiers. Keep JSON valid and consistently indented with two spaces. No formatter or linter is currently configured, so preserve nearby style and avoid unrelated reformatting.

## Testing Guidelines

No automated test suite or coverage threshold exists yet. Validate renderer changes by rendering the affected sample template and opening the PDF to inspect the cover, table of contents, headers/footers, fonts, code, and theme components. Changes to shared assets or `render.py` should smoke-test all five templates. Keep generated PDFs under `aesthepdf_output/`.

## Commit & Pull Request Guidelines

History is small and uses concise, capitalized, descriptive subjects (for example, `Release v1.0: ...`). Keep commits scoped and use an imperative or outcome-focused subject; add a body when behavior or compatibility changes. Pull requests should explain the purpose, list affected themes/assets, include the exact verification commands, and link relevant issues. For visual changes, attach before/after page screenshots or PDFs and note any new fonts or external dependencies.
