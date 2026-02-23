#!/usr/bin/env bash

shopt -s globstar
set -x

for f in def class call; do
  "./build/$f" \
    -o "$f.csv" \
    ./examples/simple/*.cpp \
    --root ./examples/simple \
    --build ./examples/simple/build \
    || exit 1
done
