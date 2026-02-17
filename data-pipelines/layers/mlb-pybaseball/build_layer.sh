#!/bin/bash
# Build the Lambda Layer zip for mlb-pybaseball.
# This layer contains pybaseball + scipy (for the core-benchmarks Lambda).
# It is designed to be used alongside mlb-pipeline-common which provides
# pandas, numpy, pyarrow, requests, etc.
#
# Run this script from the layer directory:
#   cd data-pipelines/layers/mlb-pybaseball && ./build_layer.sh

set -e

LAYER_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$LAYER_DIR/build"
PY="$BUILD_DIR/python"

echo "Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$PY"

echo "Installing pybaseball and dependencies..."
python3.13 -m pip install pybaseball \
    -t "$PY" \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.13 \
    --implementation cp

echo "--- Size before stripping ---"
du -sm "$PY" | cut -f1 | xargs -I{} echo "{}MB"

echo "Removing packages already provided by mlb-pipeline-common layer..."
# These are in the other layer — remove to avoid duplication and save space
rm -rf "$PY/pandas" "$PY/pandas-"*.dist-info \
       "$PY/pyarrow" "$PY/pyarrow-"*.dist-info \
       "$PY/numpy" "$PY/numpy-"*.dist-info "$PY/numpy.libs" \
       "$PY/requests" "$PY/requests-"*.dist-info \
       "$PY/urllib3" "$PY/urllib3-"*.dist-info \
       "$PY/certifi" "$PY/certifi-"*.dist-info \
       "$PY/charset_normalizer" "$PY/charset_normalizer-"*.dist-info \
       "$PY/idna" "$PY/idna-"*.dist-info \
       "$PY/python_dateutil-"*.dist-info "$PY/dateutil" \
       "$PY/pytz" "$PY/pytz-"*.dist-info \
       "$PY/tzdata" "$PY/tzdata-"*.dist-info \
       "$PY/six.py" "$PY/six-"*.dist-info \
       2>/dev/null || true

echo "Removing matplotlib ecosystem (not needed for data-only usage)..."
rm -rf "$PY/matplotlib" "$PY/mpl_toolkits" "$PY/fontTools" "$PY/PIL" \
       "$PY/pillow.libs" "$PY/kiwisolver" "$PY/kiwisolver.libs" \
       "$PY/cycler" "$PY/contourpy" "$PY/pyparsing" "$PY/packaging" \
       "$PY/matplotlib-"*.dist-info "$PY/fonttools-"*.dist-info \
       "$PY/pillow-"*.dist-info "$PY/kiwisolver-"*.dist-info \
       "$PY/contourpy-"*.dist-info "$PY/cycler-"*.dist-info \
       2>/dev/null || true

echo "Stripping unused scipy subpackages (keeping _lib, special, stats)..."
for item in "$PY"/scipy/*/; do
    dir_name=$(basename "$item")
    case "$dir_name" in
        _lib|special|stats|__pycache__) ;;
        *) echo "  rm scipy/$dir_name"; rm -rf "$item" ;;
    esac
done

echo "Removing test suites..."
find "$PY" -type d \( -name "tests" -o -name "test" -o -name "testing" \) -print0 | xargs -0 rm -rf 2>/dev/null || true

echo "Removing __pycache__, .dist-info, docs, stubs, headers..."
find "$PY" -type d -name "__pycache__" -print0 | xargs -0 rm -rf 2>/dev/null || true
find "$PY" -name "*.pyc" -delete 2>/dev/null || true
find "$PY" -type d -name "*.dist-info" -print0 | xargs -0 rm -rf 2>/dev/null || true
find "$PY" -type d \( -name "doc" -o -name "docs" \) -print0 | xargs -0 rm -rf 2>/dev/null || true
find "$PY" -name "*.pyi" -delete 2>/dev/null || true
find "$PY" -name "*.h" -delete 2>/dev/null || true
find "$PY" -name "*.pxd" -delete 2>/dev/null || true
rm -rf "$PY/share" 2>/dev/null || true

echo "--- Size after stripping ---"
UNZIPPED_SIZE=$(du -sm "$BUILD_DIR" | cut -f1)
echo "${UNZIPPED_SIZE}MB (Lambda limit: 250MB)"

if [ "$UNZIPPED_SIZE" -gt 250 ]; then
    echo "WARNING: Still exceeds 250MB!"
    du -sm "$PY"/*/ | sort -rn | head -10
fi

echo "Creating zip..."
cd "$BUILD_DIR"
zip -rq "$LAYER_DIR/mlb-pybaseball.zip" python/

echo "Cleaning up build directory..."
rm -rf "$BUILD_DIR"

ZIP_SIZE=$(du -sh "$LAYER_DIR/mlb-pybaseball.zip" | cut -f1)
echo "Done! Layer zip: $LAYER_DIR/mlb-pybaseball.zip ($ZIP_SIZE)"
