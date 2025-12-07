# Prompt Portal C++ Backend - Makefile
# ====================================
# Convenience wrapper for CMake build

.PHONY: all clean debug release run help

BUILD_DIR = build
CMAKE = cmake
NPROC = $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

# Default target
all: debug

# Debug build
debug:
	@echo "Building debug version..."
	@mkdir -p $(BUILD_DIR)
	@cd $(BUILD_DIR) && $(CMAKE) .. -DCMAKE_BUILD_TYPE=Debug
	@cd $(BUILD_DIR) && $(CMAKE) --build . --parallel $(NPROC)
	@echo "Build complete: $(BUILD_DIR)/prompt_portal_cpp"

# Release build
release:
	@echo "Building release version..."
	@mkdir -p $(BUILD_DIR)
	@cd $(BUILD_DIR) && $(CMAKE) .. -DCMAKE_BUILD_TYPE=Release
	@cd $(BUILD_DIR) && $(CMAKE) --build . --parallel $(NPROC)
	@echo "Build complete: $(BUILD_DIR)/prompt_portal_cpp"

# Clean build directory
clean:
	@echo "Cleaning build directory..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete."

# Run the server (builds if needed)
run: debug
	@echo "Starting server..."
	@cd $(BUILD_DIR) && ./prompt_portal_cpp

# Run release version
run-release: release
	@echo "Starting server (release)..."
	@cd $(BUILD_DIR) && ./prompt_portal_cpp

# Help
help:
	@echo "Prompt Portal C++ Backend - Build Commands"
	@echo "==========================================="
	@echo ""
	@echo "  make          - Build debug version"
	@echo "  make debug    - Build debug version"
	@echo "  make release  - Build release version"
	@echo "  make clean    - Remove build directory"
	@echo "  make run      - Build and run (debug)"
	@echo "  make run-release - Build and run (release)"
	@echo "  make help     - Show this help"
	@echo ""

