#!/bin/bash
# Build the Lambda Layer zip for mlb-pipeline-common.
# Run this script from the layer directory:
#   cd data-pipelines/layers/mlb-pipeline-common && ./build_layer.sh
#
# The output zip can be deployed with:
#   aws lambda publish-layer-version \
#     --layer-name mlb-pipeline-common \
#     --zip-file fileb://mlb-pipeline-common.zip \
#     --compatible-runtimes python3.13

set -e

LAYER_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$LAYER_DIR/build"

echo "Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/python"

echo "Installing dependencies..."
python3.13 -m pip install pandas pyarrow requests MLB-StatsAPI pybaseball \
    -t "$BUILD_DIR/python" \
    --no-cache-dir \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.13 \
    --implementation cp

echo "Copying mlb_common package..."
cp -r "$LAYER_DIR/python/mlb_common" "$BUILD_DIR/python/"

echo "Creating zip..."
cd "$BUILD_DIR"
zip -r "$LAYER_DIR/mlb-pipeline-common.zip" python/ -x "*.pyc" "__pycache__/*"

echo "Cleaning up build directory..."
rm -rf "$BUILD_DIR"

ZIP_SIZE=$(du -sh "$LAYER_DIR/mlb-pipeline-common.zip" | cut -f1)
echo "Done! Layer zip: $LAYER_DIR/mlb-pipeline-common.zip ($ZIP_SIZE)"
