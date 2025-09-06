
#!/bin/bash
# Create a simple DMG using built-in macOS tools
# 
# Code Signing Support:
# - Local development: Uses ad-hoc signing (no setup required)
# - CI/Release: Set CODESIGN_IDENTITY to use proper certificate
# - GitHub Actions: Secrets automatically configure CODESIGN_IDENTITY
# 
# Examples:
#   Local:     ./create_dmg.sh  (uses ad-hoc signing)
#   Release:   CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAM_ID)" ./create_dmg.sh

DIST_DIR="gui_dist"
APP_NAME="TBR Deal Finder"
DMG_NAME="TBR-Deal-Finder-${VERSION#v}-mac"
VOLUME_NAME="TBR Deal Finder"
SOURCE_APP="${DIST_DIR}/app/${APP_NAME}.app"
OUTPUT_DMG="${DIST_DIR}/${DMG_NAME}.dmg"

echo "📋 Using version: ${VERSION}"
echo "📦 DMG name will be: ${DMG_NAME}.dmg"

# Determine signing approach
if [ -z "$CODESIGN_IDENTITY" ]; then
    # Default to ad-hoc signing for local development
    CODESIGN_IDENTITY="-"
    SIGNING_MODE="ad-hoc (default - see docs/code-signing.md for consistent signing setup)"
elif [ "$CODESIGN_IDENTITY" = "-" ]; then
    SIGNING_MODE="ad-hoc (explicit)"
    echo "🔐 Code signing mode: ad-hoc"
else
    SIGNING_MODE="certificate: $CODESIGN_IDENTITY"
    echo "🔐 Code signing mode: cert"
fi

# Create directories
mkdir -p dmg_temp

# Check if app bundle exists and apply signing
echo "🔍 Checking app bundle..."
if [ -d "${SOURCE_APP}" ]; then
    echo "📱 App bundle found: ${SOURCE_APP}"
    
    # Always sign with the determined identity (handles both fresh builds and re-signing)
    echo "🖊️  Applying code signature..."
    codesign --sign "$CODESIGN_IDENTITY" --deep --force "${SOURCE_APP}"
    
    if [ $? -eq 0 ]; then
        echo "✅ Code signature applied successfully"
        
        # Verify the signature
        echo "🔍 Verifying signature..."
        codesign --verify --verbose=2 "${SOURCE_APP}" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ Signature verification passed"
        else
            echo "⚠️  Signature verification had issues, but should still work for distribution"
        fi
    else
        echo "❌ Code signing failed!"
        if [ "$CODESIGN_IDENTITY" != "-" ]; then
            echo "💡 Falling back to ad-hoc signing..."
            codesign --sign - --deep --force "${SOURCE_APP}"
            if [ $? -eq 0 ]; then
                echo "✅ Ad-hoc signature applied as fallback"
            else
                echo "❌ Even ad-hoc signing failed. Continuing anyway..."
            fi
        else
            echo "❌ Ad-hoc signing failed. This may cause issues with app distribution."
        fi
    fi
else
    echo "❌ App bundle not found: ${SOURCE_APP}"
    echo "💡 Make sure you've run 'make build-mac' or 'flet build macos' first"
    exit 1
fi

# Copy app to temp directory
cp -R "${SOURCE_APP}" "dmg_temp/"

# Create a symbolic link to Applications
ln -s /Applications "dmg_temp/Applications"

# Create DMG
hdiutil create -volname "${VOLUME_NAME}" \
  -srcfolder dmg_temp \
  -ov \
  -format UDZO \
  "${OUTPUT_DMG}"

# Cleanup
rm -rf dmg_temp

echo "DMG created at: ${OUTPUT_DMG}"