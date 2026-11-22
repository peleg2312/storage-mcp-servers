#!/bin/sh
# Builds paas-kit-<git short sha>.zip: the paas-kit folder plus its offline payload (wheels, tiktoken data).
#   sh scripts/make-paas-kit.sh <payload dir> [out dir]
# <payload dir> holds:  headroom/*.whl (headroom-ai[proxy], cp312)   tiktoken/<sha1 of the encoding url> (cl100k_base,
#                       o200k_base, p50k_base, r50k_base)   rtk/rtk (rtk-ai/rtk v1.2.1, git apply paas-kit/rtk-patches/*.patch,
#                       cargo build --release --locked --target x86_64-unknown-linux-musl with CC=musl-gcc)
#                       hf/ only with WITH_KOMPRESS=1. The code-graph / fastapi-api / ponytail plugins (with their own
#                       wheels) come from brain/plugins.
# Get them on a machine with internet, e.g.:
#   pip download -d headroom --only-binary=:all: --python-version 3.12 --platform manylinux_2_28_x86_64 "headroom-ai[proxy]"
set -eu
PAY=${1:?usage: make-paas-kit.sh <payload dir> [out dir]}; OUT=${2:-.}
HERE=$(cd "$(dirname "$0")/.." && pwd)
for d in headroom tiktoken rtk; do [ -n "$(ls "$PAY/$d" 2>/dev/null)" ] || { echo "missing $PAY/$d"; exit 1; }; done
V=$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d)
T=$(mktemp -d); K=$T/paas-kit
cp -R "$HERE/paas-kit" "$K"
find "$K" -name __pycache__ -prune -exec rm -rf {} +
mkdir -p "$K/wheels"
cp -R "$PAY/headroom" "$K/wheels/headroom"
cp -R "$PAY/tiktoken" "$K/tiktoken"
cp -R "$PAY/rtk" "$K/rtk"            # rtk (static x86_64, rtk-ai/rtk v1.2.1 + rtk-patches/) + its LICENSE
[ -z "${WITH_KOMPRESS:-}" ] || cp -R "$PAY/hf" "$K/hf"   # optional: Kompress model (WITH_KOMPRESS=1); off by default
echo "$V" > "$K/VERSION"
# the paas Market plugins the kit adds to a VM whose brain does not carry them yet: taken from the brain (one copy)
mkdir -p "$K/brain-plugins"
for p in code-graph fastapi-api ponytail; do cp -R "$HERE/brain/plugins/$p" "$K/brain-plugins/$p"; done
chmod +x "$K/install.sh" "$K/uninstall.sh" "$K/bin/paas-kit" "$K/bin/rtk-hook" "$K/bin/rtk-pre" "$K/rtk/rtk"
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
(cd "$T" && rm -f "$OUT/paas-kit-$V.zip" && zip -qry "$OUT/paas-kit-$V.zip" paas-kit)
rm -rf "$T"
echo "$OUT/paas-kit-$V.zip ($(du -h "$OUT/paas-kit-$V.zip" | cut -f1))"
