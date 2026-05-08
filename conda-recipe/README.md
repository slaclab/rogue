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

# conda-forge submission notes

When submitting to conda-forge, the feedstock version of this recipe should:
1. Replace the `environ.get(...)` version with a hardcoded `{% set version = "x.y.z" %}`
2. Replace `path: ..` source with a GitHub release tarball URL and `sha256:`
3. Remove the `GIT_DESCRIBE_TAG` / `GITHUB_REF_NAME` fallback logic (version is hardcoded)
