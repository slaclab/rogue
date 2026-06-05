# Agent Guidance

Before making code or documentation changes in this repository, read:

- `DEVELOPMENT.md`
- `tests/METHODOLOGY.md` when adding or changing tests

For substantial feature work, keep planning, progress, and handoff Markdown
under `docs/plans/<task-name>/`.

Follow the project guidance in those files over tool-specific defaults.

## Build Environment

Use a Miniforge-managed conda environment for local builds and tests. Before
creating anything new, look for an existing usable environment:

- For fuller setup instructions, see
  `docs/src/installing/miniforge_build.rst`.
- Find the conda installation instead of assuming a fixed path. First try
  `command -v conda`; if it exists, use `conda info --base` to find the base
  install and source `etc/profile.d/conda.sh` from that directory.
- If `conda` is not on `PATH`, check likely site-specific locations such as
  `$MINIFORGE_HOME`, `$CONDA_HOME`, `$HOME/miniforge3`, `$HOME/mambaforge`,
  `$HOME/miniconda3`, and `/opt/conda`. Source the first existing
  `etc/profile.d/conda.sh` found there.
- If no conda installation can be found, do not hard-code a new path. Ask the
  user where Miniforge is installed, or install Miniforge only when the user has
  approved that setup work.
- Check existing environments with `conda env list`.
- Prefer an existing `rogue_build` environment. If another conda environment is
  already active and appears to contain the required build dependencies, reuse
  it rather than creating a duplicate.
- Use the same conda environment for configure, build, install, pytest, and
  ctest commands.
- Do not create, update, remove, or otherwise mutate conda environments unless
  the user explicitly asks for that setup work or approves it after being told
  why it is needed.

If no suitable environment exists, ask the user before creating one. With
explicit approval, create one from the repository environment file:

```sh
# After conda has been located and initialized:
conda env create -n rogue_build -f conda.yml
conda activate rogue_build
```

If `rogue_build` already exists but may be stale, do not refresh it
automatically. Explain why an update appears necessary, such as missing
packages, solver conflicts, changed `conda.yml` requirements, or build failures
caused by environment drift. With explicit approval, refresh it with:

```sh
# After conda has been located and initialized:
conda env update -n rogue_build -f conda.yml
conda activate rogue_build
```

`mamba env update` is also acceptable when `mamba` is already available, but
prefer `conda env update` for the default agent workflow.

If the shell is not activated, use `conda run -n rogue_build <command>`.
Follow the build modes and CMake options in `DEVELOPMENT.md`; for ordinary
local validation, prefer the repo-local `build/` tree and source
`build/setup_rogue.sh` before running tests.

Create pull requests against `pre-release` unless explicitly directed
otherwise. PR descriptions should follow `.github/pull_request_template.md`.

Do not stage files or make git commits unless explicitly asked.
