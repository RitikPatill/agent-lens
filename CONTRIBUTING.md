# Contributing to AgentLens

Thanks for your interest. This guide gets you from zero to running tests in a few minutes.

---

## Prerequisites

- Python >= 3.11 (use `py -3.11` on Windows; `python3.11` on Linux/macOS)
- Node 18+
- [`uv`](https://github.com/astral-sh/uv) for Python dependency management (optional but recommended)

---

## Setup

```bash
make install        # installs Python packages + Node modules
```

On Windows without `uv`, install each package manually:

```bash
py -3.11 -m pip install -e "sdk/.[dev]"
py -3.11 -m pip install -e "server/.[dev]"
cd dashboard && npm install
```

---

## Running tests

```bash
# Python (28 SDK + 15 server + 3 example tests)
make test

# or individually:
py -3.11 -m pytest sdk/tests/ -v
py -3.11 -m pytest server/tests/ -v
py -3.11 -m pytest examples/tests/ -v

# JavaScript (24 vitest tests)
cd dashboard && npx vitest run
```

---

## Linting and formatting

```bash
make lint       # ruff check + eslint
make format     # ruff format + prettier
```

---

## Pre-commit hooks

```bash
pre-commit install
```

Hooks run `ruff` and `eslint` on staged files before each commit.

---

## Opening a PR

1. Branch from `main`: `git checkout -b feat/my-feature`
2. One feature or fix per PR — keep diffs reviewable.
3. Add tests for new behaviour; all existing tests must pass.
4. Update `README.md` if your change affects the public interface or quickstart.
5. Be respectful in reviews and discussions.

For a full picture of the codebase, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
