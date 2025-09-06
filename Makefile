# TBR Deal Finder Build System
.PHONY: help build-mac build-windows build-windows-docker build-linux build-all clean clean-all test-mac status create-cert

# Default target
help:
	@echo "TBR Deal Finder Build Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make create-cert     Create self-signed certificate (one-time setup) 🔐"
	@echo ""
	@echo "Building:"
	@echo "  make build-mac       Build self-signed macOS DMG ⭐"
	@echo "  make build-windows   Build Windows EXE (GitHub Actions) ⭐"
	@echo "  make build-linux     Build Linux executable"
	@echo "  make build-all       Build for current platform"
	@echo ""
	@echo "Testing:"
	@echo "  make test-mac        Test macOS DMG"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          Clean build artifacts (keeps .spec)"
	@echo "  make clean-all      Clean everything including .spec"
	@echo ""
	@echo "Current platform: $(shell uname -s)"

# Variables
PROJECT_NAME := TBR Deal Finder
DIST_DIR := gui_dist
BUILD_SCRIPT := scripts/packaging/build_cross_platform.py

# Build self-signed macOS DMG (recommended)
build-mac:
	@echo "🍎 Building app"
	uv run flet build macos --output ${DIST_DIR}/app/
	@echo ""
	@echo "📦 Creating self-signed macOS DMG for app"
	bash scripts/packaging/create_dmg.sh
	@echo "✅ Self-signed macOS DMG built successfully!"

# Build Windows EXE (requires Windows or GitHub Actions)
build-windows:
	@echo "🪟 Building Windows EXE..."
	uv run flet build windows --output ${DIST_DIR}/ --verbose

# Test macOS DMG
test-mac:
	@echo "🧪 Testing macOS DMG..."
	@if [ ! -f "$(DIST_DIR)/TBRDealFinder.dmg" ]; then \
		echo "❌ No DMG found. Run 'make build-mac' first."; \
		exit 1; \
	fi
	@echo "📂 DMG file info:" && \
		ls -lh $(DIST_DIR)/TBRDealFinder.dmg && \
		echo "🔍 Testing DMG mount..." && \
		hdiutil attach $(DIST_DIR)/TBRDealFinder.dmg -mountpoint /tmp/tbr_test -nobrowse && \
		echo "✅ DMG mounts successfully" && \
		ls -la /tmp/tbr_test/ && \
		hdiutil detach /tmp/tbr_test 2>/dev/null || \
		echo "❌ DMG mount failed"

# Build Linux executable (works on Linux)
build-linux:
	@echo "🐧 Building Linux executable..."
	@if [ "$(shell uname -s)" != "Linux" ]; then \
		echo "⚠️  Linux builds require Linux OS"; \
		echo "   Run this on Linux or use GitHub Actions for cross-platform builds"; \
		exit 1; \
	fi
	uv run python $(BUILD_SCRIPT)
	@echo ""
	@echo "✅ Linux executable built successfully!"
	@echo "📦 Output: $(DIST_DIR)/TBRDealFinder"
	@ls -lh $(DIST_DIR)/TBRDealFinder 2>/dev/null || true

# Build for current platform
build-all:
	@echo "🌍 Building for current platform..."
	@case "$(shell uname -s)" in \
		Darwin) \
			echo "On macOS - building self-signed DMG"; \
			$(MAKE) build-mac; \
			;; \
		Linux) \
			echo "On Linux - building executable"; \
			$(MAKE) build-linux; \
			;; \
		MINGW*|MSYS*|CYGWIN*) \
			echo "On Windows - building Windows EXE"; \
			$(MAKE) build-windows; \
			;; \
		*) \
			if [ "$(OS)" = "Windows_NT" ]; then \
				echo "On Windows - building Windows EXE"; \
				$(MAKE) build-windows; \
			else \
				echo "❌ Unsupported platform: $(shell uname -s)"; \
				echo "   Supported: macOS (with Docker), Windows, Linux"; \
				exit 1; \
			fi; \
			;; \
	esac

# Clean build artifacts (preserves .spec file for version control)
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf $(DIST_DIR)/
	rm -rf build/
	@echo "✅ Clean complete (kept .spec file)"

# Clean everything including .spec file
clean-all:
	@echo "🧹 Cleaning everything..."
	rm -rf $(DIST_DIR)/
	rm -rf build/
	rm -rf dist/
	rm -f *.spec
	@echo "✅ Complete clean finished"

# Create self-signed certificate for consistent code signing
create-cert:
	@echo "🔐 Creating self-signed certificate for consistent code signing..."
	@echo ""
	@bash scripts/create-self-signed-cert.sh

# Show build status
status:
	@echo "📊 Build Status:"
	@echo ""
	@echo "Platform: $(shell uname -s)"
	@echo "Build directory: $(DIST_DIR)/"
	@echo ""
	@echo "Built artifacts:"
	@if [ -d "$(DIST_DIR)" ]; then \
		ls -la $(DIST_DIR)/ 2>/dev/null || echo "  None found"; \
	else \
		echo "  Build directory doesn't exist"; \
	fi
	@echo ""
	@echo "Dependencies:"
	@uv tree --depth 1 | grep -E "(flet|pyinstaller)" || echo "  Not installed"
	@echo ""
	@echo "Code signing certificates:"
	@security find-identity -v -p codesigning 2>/dev/null | grep -E "(TBR Deal Finder|Developer ID)" || echo "  None found (will use ad-hoc signing)"
