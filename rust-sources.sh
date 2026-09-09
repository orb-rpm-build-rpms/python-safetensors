#!/bin/sh
# rust-sources.sh - assemble the Rust "vendor" tarball for an offline build.
#
# rpm-build-assist runs every *sources.sh in the checked-out package directory
# after spectool has downloaded the online sources (here the GitHub archive).
# This project has no lookaside cache, so rather than have a maintainer run
# `cargo vendor` by hand and upload the result, we regenerate the vendor
# tarball on demand at build time.
#
# safetensors differs from the other vendored crates (llguidance, outlines-core)
# in two ways:
#   * the maturin/Cargo project lives under bindings/python, not the archive
#     root, and it has a path dependency on the bundled ../../safetensors crate;
#   * the GitHub archive ships NO Cargo.lock, so we cannot `--locked`. We let
#     `cargo vendor` resolve and write a fresh bindings/python/Cargo.lock, and
#     ship that lock alongside vendor/ in the tarball so the offline build is
#     self-consistent.
#
# The path dependency (../../safetensors) is left untouched by cargo vendor: the
# spec keeps the bundled crate in the tree, so no rust-safetensors Fedora crate
# is required. `%cargo_prep -v vendor` (run in bindings/python) then builds the
# whole crates.io graph from bindings/python/vendor with [net] offline = true.
set -eu

# The GitHub archive spectool just fetched, e.g. "safetensors-0.8.0.tar.gz".
# Exclude a previously generated "*-vendor.tar.*" so re-runs don't pick it up.
sdist=$(ls -1 ./*.tar.gz 2>/dev/null | grep -v -- '-vendor\.tar\.' | head -n1)
[ -n "$sdist" ] || { echo "rust-sources.sh: no source tarball found" >&2; exit 1; }

# "safetensors-0.8.0.tar.gz" -> "safetensors-0.8.0": the dir the archive unpacks
# to and the stem for the vendor tarball name the spec's Source1 expects.
stem=$(basename "$sdist" .tar.gz)
vendor_tarball="${stem}-vendor.tar.xz"

# Idempotent: nothing to do if a previous run already produced the tarball.
[ -e "$vendor_tarball" ] && { echo "rust-sources.sh: $vendor_tarball already present"; exit 0; }

# Work under the checkout dir (mounted, ample space) rather than /tmp; the
# vendor tree is large (tens of MB uncompressed).
workdir=$(mktemp -d "$PWD/.rust-vendor.XXXXXX")
trap 'rm -rf "$workdir"' EXIT

tar xzf "$sdist" -C "$workdir"
# cargo vendor must run where the binding crate's Cargo.toml lives. There is no
# committed Cargo.lock, so run without --locked; cargo writes Cargo.lock here.
( cd "$workdir/$stem/bindings/python" && cargo vendor vendor >/dev/null )

# Pack bindings/python/{vendor,Cargo.lock} relative to the archive root; %prep
# unpacks them back into bindings/python and %cargo_prep -v vendor (run there)
# points cargo at ./vendor using the shipped lock.
tar -C "$workdir/$stem" -cf - bindings/python/vendor bindings/python/Cargo.lock \
    | xz -T0 -3 > "$vendor_tarball"
echo "rust-sources.sh: wrote $vendor_tarball"
