# CI for conda package release

https://github.com/slaclab/ruckus/blob/main/.github/workflows/conda_build_lib.yml


# How to build rogue .conda package file and test it locally

1) Install and configure conda build tool

```bash
cd ${HOME}
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p ${HOME}/miniforge3
export PATH="${HOME}/miniforge3/bin:$PATH"
source ${HOME}/miniforge3/etc/profile.d/conda.sh
conda config --set always_yes yes
conda config --set channel_priority strict
conda install -n base conda-libmamba-solver
conda config --set solver libmamba
conda install conda-build anaconda-client
conda update -q conda conda-build
conda update --all
```

2) Build the .conda package

```bash
# Setup conda env
source ${HOME}/miniforge3/etc/profile.d/conda.sh

# Add conda toolchain's bin to $PATH
export PATH="${HOME}/miniforge3/bin:$PATH"

# Go to rogue clone dir
cd rogue

# Set the version tag (must match an existing GitHub release tag)
export GIT_DESCRIBE_TAG=$(git describe --tags --abbrev=0)

# Build the .conda file
conda build conda-recipe --output-folder bld-dir -c tidair-tag -c conda-forge
```

3) Test the .conda package locally

```bash
# Setup conda env
source ${HOME}/miniforge3/etc/profile.d/conda.sh

# Go to rogue clone dir
cd rogue

# Index your folder
conda index $PWD/bld-dir

# Create environment using the package name, not the file path
conda create -n test-rogue -c file:///$PWD/bld-dir -c conda-forge rogue

# Test env
conda activate test-rogue
python -c "import pyrogue; print(pyrogue.__version__)"
```

# Build matrix

`conda_build_config.yaml` declares the Python variants built for the
`tidair-tag` channel: py310, py311, py312, and py313. Running
`conda build conda-recipe` produces one `.conda` per variant.

# GLIBC compatibility floor

`meta.yaml` pins `sysroot_linux-64 2.28` in `requirements.build` (matches the
v6.12.0 recipe — targets Rocky 8 / RHEL 8 glibc 2.28 for broad compatibility).
This forces the conda-forge GCC to link against the `sysroot_linux-64-2.28`
CDT instead of the build runner's `/usr` glibc, capping
`librogue-core.so`'s glibc symbol-version floor at 2.28. Without this pin the
binary built on `ubuntu-24.04` requires `GLIBC_2.38` and fails to load on any
older system (Rocky 8/9, Ubuntu 22.04, etc.).

# Version convention

The `tidair-tag` channel uses the `v`-prefixed tag (e.g. `rogue-v6.13.0-py312_0.conda`).
`meta.yaml` reads `GIT_DESCRIBE_TAG` (or `GITHUB_REF_NAME` in CI) and forces a leading
`v` on the package version. `build.sh` then passes the same string to CMake as
`ROGUE_VERSION`, which the C++ `Version::init()` parser requires to start with `v`.

# conda-forge submission notes

When submitting to conda-forge, the feedstock copy of this recipe should:
1. Replace the `environ.get(...)` version logic with a hardcoded `{% set version = "x.y.z" %}` (no `v` prefix per conda-forge convention)
2. Replace `path: ..` source with a GitHub release tarball URL and `sha256:`
3. Remove the `GIT_DESCRIBE_TAG` / `GITHUB_REF_NAME` fallback logic (version is hardcoded)
4. Drop `conda_build_config.yaml` (conda-forge supplies global pinning)
5. Replace the explicit `sysroot_linux-64 2.28` line with `{{ stdlib('c') }}`.
   The conda-forge global pinning provides `c_stdlib`/`c_stdlib_version` and
   the lint requires the `stdlib()` jinja, not a bare `sysroot_linux-64` dep.

`build.sh` already handles both cases — it auto-prepends `v` when `PKG_VERSION`
lacks one, so it works unchanged in a conda-forge feedstock.
