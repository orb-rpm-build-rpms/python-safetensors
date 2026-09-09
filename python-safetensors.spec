Name:           python-safetensors
Version:        0.8.0
Release:        %autorelease
Summary:        Python bindings for the safetensors library

# Results of the Cargo License Check
#
# Apache-2.0
# Apache-2.0 OR MIT
# Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT
# MIT
# MIT OR Apache-2.0
# Unlicense OR MIT
# Zlib
License:        %{shrink:
    Apache-2.0 AND
    MIT AND
    Zlib AND
    (Apache-2.0 OR MIT) AND
    (Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT) AND
    (Unlicense OR MIT)
    }
SourceLicense:  Apache-2.0
# The PyPI package lives at https://pypi.org/project/safetensors/
# But the GitHub URL encompasses the entire project including the separately-packaged Rust crate
URL:            https://github.com/huggingface/safetensors
Source:         %{url}/archive/refs/tags/v%{version}/safetensors-%{version}.tar.gz
# Vendored Rust crate graph (bindings/python/vendor + its Cargo.lock),
# regenerated at build time by rust-sources.sh. F44 does not package the crate
# versions this release needs (starting with rust-safetensors 0.8.0 itself), so
# instead of the cargo buildrequires generator we build the whole graph offline
# from this tarball. See rust-sources.sh for how it is assembled.
Source1:        safetensors-%{version}-vendor.tar.xz

BuildRequires:  python3-devel
BuildRequires:  cargo-rpm-macros >= 24
# Test requirements
BuildRequires:  python3dist(pytest)
# https://github.com/huggingface/safetensors/pull/640
BuildRequires:  python3dist(fsspec)

# Exclude i686 because rust-safetensors does
ExcludeArch:    %{ix86}

# Define our own pytorch_arches macro until we have one system-wide.
%if %{undefined pytorch_arches}
%global pytorch_arches %{x86_64} %{arm64}
%endif

# Only include the torch extras on arches with PyTorch
%ifarch %{pytorch_arches}
%bcond torch 1
%else
%bcond torch 0
%endif

%global _description %{expand:
This library implements a new simple format for storing tensors safely
(as opposed to pickle) and that is still fast (zero-copy).}

%description %_description

%package -n python3-safetensors
Summary:        %{summary}

%description -n python3-safetensors %_description

%pyproject_extras_subpkg -n python3-safetensors numpy%{?with_torch:,torch}


%prep
# -a1 unpacks the vendor tarball (Source1) into the tree as
# bindings/python/vendor and restores bindings/python/Cargo.lock.
%autosetup -p1 -n safetensors-%{version} -a1
# The bundled ../../safetensors crate is kept: the binding crate depends on it
# by path, and cargo vendor leaves path deps in place, so no rust-safetensors
# Fedora crate is needed.
# Delete the miscellaneous stuff from the GitHub release bundle
rm -r attacks/ docs/ .github/ codecov.y* Dockerfile.* .dockerignore flake.* .gitignore Makefile RELEASE.md
# Copy (not move) the toplevel README under a conflict-free name for %doc. It is
# copied rather than renamed because the bundled crate's safetensors/README.md
# is a symlink to this ../README.md, and safetensors/src/lib.rs pulls it in via
# include_str!("../README.md") at compile time -- renaming it breaks that build.
cp README.md README-safetensors.md
# cargo_prep needs to be run where Cargo.toml lives. -v vendor builds the crate
# graph from bindings/python/vendor fully offline, replacing the cargo
# buildrequires generator.
cd bindings/python
%cargo_prep -v vendor
cd ../..


%generate_buildrequires
# The Rust deps come from the vendor tree, so the cargo buildrequires generator
# is intentionally absent; only the Python build backend requirements remain.
cd bindings/python/
%pyproject_buildrequires -x numpy%{?with_torch:,torch}
cd ../..

%build
cd bindings/python/
export RUSTFLAGS='%{build_rustflags}'
%pyproject_wheel
cd ../..


%install
%pyproject_install
# When saving the files, assert that a license file was found
%pyproject_save_files -l safetensors


%check
cd bindings/python/
# Omit submodules that require unpackaged extras / optional dependencies
%{pyproject_check_import %{shrink:
    --exclude 'safetensors.flax'
    --exclude 'safetensors.mlx'
    --exclude 'safetensors.paddle'
    --exclude 'safetensors.tensorflow'
    %{?!with_torch:--exclude 'safetensors.torch'}
    } }
# Test both the rust part of the bindings and the Python parts. The Rust deps
# (including dev-deps) come from the vendored tree, so this runs fully offline.
%cargo_test
# But only run the tests/ and not benches/ in Python
# Ignore tests that require unpackaged extras / optional dependencies
%if %{without torch}
ignore="${ignore-} --ignore=tests/test_multithreaded.py"
ignore="${ignore-} --ignore=tests/test_pread_backend.py"
ignore="${ignore-} --ignore=tests/test_pt_comparison.py"
ignore="${ignore-} --ignore=tests/test_pt_model.py"
ignore="${ignore-} --ignore=tests/test_simple.py"
%endif
ignore="${ignore-} --ignore=tests/test_flax_comparison.py"
ignore="${ignore-} --ignore=tests/test_tf_comparison.py"
%ifarch s390x
# On s390x architecture, test_serialize_file_releases_gil fails
# https://github.com/safetensors/safetensors/issues/812
ignore="${ignore-} --ignore=tests/test_threadable.py"
%endif
%pytest ${ignore-} tests/
cd ../..


%files -n python3-safetensors -f %{pyproject_files}
%doc README-safetensors.md bindings/python/README.md


%changelog
%autochangelog
