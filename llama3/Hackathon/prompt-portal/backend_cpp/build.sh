#!/bin/bash
# Prompt Portal C++ Backend - Build Script (Linux/macOS)
# ======================================================

set -e

BUILD_TYPE="Debug"
BUILD_DIR="build"
CLEAN=false
RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --release)
            BUILD_TYPE="Release"
            shift
            ;;
        --run)
            RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "================================================"
echo "  Prompt Portal C++ Backend - Build Script"
echo "================================================"
echo ""

# Check for required tools
echo "[1/5] Checking prerequisites..."

# Check CMake
if command -v cmake &> /dev/null; then
    CMAKE_VERSION=$(cmake --version | head -n1)
    echo "  CMake: $CMAKE_VERSION"
else
    echo "  ERROR: CMake not found. Please install CMake 3.16+"
    echo "  Ubuntu/Debian: sudo apt install cmake"
    echo "  macOS: brew install cmake"
    exit 1
fi

# Check for compiler
if command -v g++ &> /dev/null; then
    GCC_VERSION=$(g++ --version | head -n1)
    echo "  Compiler: $GCC_VERSION"
elif command -v clang++ &> /dev/null; then
    CLANG_VERSION=$(clang++ --version | head -n1)
    echo "  Compiler: $CLANG_VERSION"
else
    echo "  ERROR: No C++ compiler found."
    echo "  Ubuntu/Debian: sudo apt install build-essential"
    echo "  macOS: xcode-select --install"
    exit 1
fi

# Install SQLite development files if needed (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! dpkg -l libsqlite3-dev &> /dev/null 2>&1; then
        echo "  Note: You may need to install libsqlite3-dev"
        echo "  sudo apt install libsqlite3-dev"
    fi
fi

# Clean if requested
if [ "$CLEAN" = true ] && [ -d "$BUILD_DIR" ]; then
    echo ""
    echo "[2/5] Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    echo "  Build directory cleaned."
fi

# Create build directory
echo ""
echo "[3/5] Creating build directory..."
mkdir -p "$BUILD_DIR"
echo "  Build directory ready."

# Configure with CMake
echo ""
echo "[4/5] Configuring with CMake ($BUILD_TYPE)..."
cd "$BUILD_DIR"
cmake .. -DCMAKE_BUILD_TYPE="$BUILD_TYPE"
echo "  Configuration complete."

# Build
echo ""
echo "[5/5] Building project..."
cmake --build . --config "$BUILD_TYPE" --parallel $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
echo "  Build complete!"

cd ..

echo ""
echo "================================================"
echo "  Build Successful!"
echo "================================================"
echo ""
echo "Executable location:"
echo "  $BUILD_DIR/prompt_portal_cpp"
echo ""
echo "To run the server:"
echo "  cd $BUILD_DIR"
echo "  ./prompt_portal_cpp"
echo ""

# Run if requested
if [ "$RUN" = true ]; then
    echo "Starting server..."
    cd "$BUILD_DIR"
    ./prompt_portal_cpp
fi

