# TBR Deal Finder Build System
.PHONY: help install-deps build-mac build-mac-spec build-windows build-windows-docker build-linux build-all clean clean-all test-mac status

# Default target
help:
	@echo "TBR Deal Finder Build Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install-deps    Install build dependencies"
	@echo ""
	@echo "Building:"
	@echo "  make build-mac       Build self-signed macOS DMG ⭐"
	@echo "  make build-mac-spec  Build using .spec file (faster)"
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

# Install build dependencies
install-deps:
	@echo "📦 Installing build dependencies..."
	uv add pyinstaller
	@echo "✅ Dependencies installed"

# Build self-signed macOS DMG (recommended)
build-mac: install-deps
	@echo "🍎 Building self-signed macOS DMG..."
	uv run python $(BUILD_SCRIPT)
	@echo ""
	@echo "✅ Self-signed macOS DMG built successfully!"
	@echo "📦 Output: $(DIST_DIR)/TBRDealFinder.dmg"
	@ls -lh $(DIST_DIR)/*.dmg 2>/dev/null || true

# Build using existing .spec file (faster for development)
build-mac-spec: install-deps
	@if [ ! -f "TBRDealFinder.spec" ]; then \
		echo "❌ TBRDealFinder.spec not found. Run 'make build-mac' first to generate it."; \
		exit 1; \
	fi
	@echo "⚡ Building macOS DMG using .spec file..."
	uv run pyinstaller TBRDealFinder.spec
	@echo "📦 Creating DMG..."
	@if [ -d "$(DIST_DIR)/TBRDealFinder.app" ]; then \
		hdiutil create -volname "TBR Deal Finder" -srcfolder "$(DIST_DIR)/TBRDealFinder.app" -ov -format UDZO "$(DIST_DIR)/TBRDealFinder.dmg"; \
		echo "✅ macOS DMG built using .spec (faster)!"; \
		echo "📦 Output: $(DIST_DIR)/TBRDealFinder.dmg"; \
		ls -lh $(DIST_DIR)/*.dmg 2>/dev/null || true; \
	else \
		echo "❌ App bundle not found after PyInstaller build"; \
		exit 1; \
	fi

# Build Windows EXE (requires Windows or GitHub Actions)
build-windows: install-deps
	@echo "🪟 Building Windows EXE..."
	@if [ "$(shell uname -s)" = "MINGW32_NT" ] || [ "$(shell uname -s)" = "MINGW64_NT" ] || [ "$(shell uname -s)" = "CYGWIN_NT" ] || [ "$(shell echo $(OS))" = "Windows_NT" ]; then \
		echo "🪟 Building Windows EXE natively..."; \
		uv run python $(BUILD_SCRIPT); \
		echo "✅ Windows EXE built successfully!"; \
		echo "📦 Output: $(DIST_DIR)/TBRDealFinder.exe"; \
	else \
		echo "❌ Windows builds require a Windows environment"; \
		echo ""; \
		echo "💡 Recommended approach for Windows .exe:"; \
		echo "   🤖 Use GitHub Actions (reliable & automatic)"; \
		echo "      git tag v1.0.0"; \
		echo "      git push origin v1.0.0"; \
		echo ""; \
		echo "   📁 GitHub Actions workflow already configured:"; \
		echo "      .github/workflows/build-windows.yml"; \
		echo ""; \
		echo "   🖥️  Or build on actual Windows machine"; \
		echo "      Same command: make build-windows"; \
		exit 1; \
	fi

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
build-linux: install-deps
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
	rm -rf $(DIST_DIR)/*.app
	rm -rf $(DIST_DIR)/*.dmg
	rm -rf $(DIST_DIR)/*.exe
	rm -rf $(DIST_DIR)/TBRDealFinder
	rm -rf build/
	rm -rf dist/
	@echo "✅ Clean complete (kept .spec file)"

# Clean everything including .spec file
clean-all:
	@echo "🧹 Cleaning everything..."
	rm -rf $(DIST_DIR)/
	rm -rf build/
	rm -rf dist/
	rm -f *.spec
	@echo "✅ Complete clean finished"

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
