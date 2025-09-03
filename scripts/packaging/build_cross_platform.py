"""
Cross-platform build script with code signing support for TBR Deal Finder.
Handles building and signing applications for macOS, Windows, and Linux.
"""
import platform
import subprocess
import sys
from pathlib import Path

# Project configuration
PROJECT_NAME = "TBR Deal Finder"
PROJECT_IDENTIFIER = "com.tbrdeals.finder"
MAIN_SCRIPT = "tbr_deal_finder/gui/main.py"
ICON_FILE = "tbr_deal_finder/gui/assets/logo.png"
WINDOWS_ICON_FILE = "tbr_deal_finder/gui/assets/logo.ico"  # Windows needs .ico format

# Platform detection
CURRENT_PLATFORM = platform.system().lower()
IS_MACOS = CURRENT_PLATFORM == "darwin"
IS_WINDOWS = CURRENT_PLATFORM == "windows"
IS_LINUX = CURRENT_PLATFORM == "linux"

# Code signing configuration - Always use self-signing
if IS_MACOS:
    SIGNING_IDENTITY = "-"  # Ad-hoc signing (self-signed)
elif IS_WINDOWS:
    SIGNING_IDENTITY = "TBRDealFinder-SelfSigned"  # Self-signed certificate name
else:
    SIGNING_IDENTITY = ""  # Linux doesn't require signing


def check_signing_identity():
    """Check if signing identity is available for the current platform."""
    if IS_MACOS:
        print("✅ Using macOS ad-hoc signing (self-signed)")
        print("   Note: Users will see security warnings, but they're easy to bypass")
        return True
    elif IS_WINDOWS:
        return check_windows_self_signed_cert()
    else:
        print("ℹ️  No signing required for Linux builds")
        return True


def check_windows_self_signed_cert():
    """Check or create Windows self-signed certificate."""
    # Check if signtool is available first
    try:
        subprocess.run(["signtool"], capture_output=True, check=False)
    except FileNotFoundError:
        print("❌ SignTool not found. Install Windows SDK for code signing.")
        print("   Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
        return False
    
    cert_name = SIGNING_IDENTITY
    
    # Check if certificate already exists
    try:
        result = subprocess.run([
            "powershell", "-Command",
            f"Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object {{$_.Subject -like '*{cert_name}*'}}"
        ], capture_output=True, text=True, check=False)
        
        if cert_name in result.stdout:
            print(f"✅ Found existing self-signed certificate: {cert_name}")
            return True
    except Exception as e:
        print(f"⚠️  Could not check for existing certificate: {e}")
    
    # Create self-signed certificate
    print(f"🔐 Creating Windows self-signed certificate: {cert_name}")
    try:
        create_cmd = [
            "powershell", "-Command",
            f"""
            $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN={cert_name}' -KeyUsage DigitalSignature -FriendlyName '{cert_name}' -CertStoreLocation Cert:\\CurrentUser\\My -KeyLength 2048 -Provider 'Microsoft Enhanced RSA and AES Cryptographic Provider' -KeyExportPolicy Exportable -KeySpec Signature -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(3);
            Write-Output "Certificate created with thumbprint: $($cert.Thumbprint)"
            """
        ]
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        print("✅ Self-signed certificate created successfully")
        print(f"   {result.stdout.strip()}")
        print("   Note: Users will see security warnings, but they're easy to bypass")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create self-signed certificate: {e}")
        print(f"   Error output: {e.stderr}")
        print("💡 Try running as Administrator")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating certificate: {e}")
        return False


def build_with_pyinstaller():
    """Build using PyInstaller (cross-platform)."""
    print(f"🔨 Building with PyInstaller for {CURRENT_PLATFORM}...")
    
    # Determine the correct icon file
    if IS_WINDOWS and Path(WINDOWS_ICON_FILE).exists():
        icon_file = WINDOWS_ICON_FILE
    elif Path(ICON_FILE).exists():
        icon_file = ICON_FILE
    else:
        print("⚠️  No icon file found, building without icon")
        icon_file = None
    
    # Base PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", PROJECT_NAME.replace(" ", ""),
        "--add-data", f"tbr_deal_finder/queries{':' if not IS_WINDOWS else ';'}tbr_deal_finder/queries",
        "--add-data", f"tbr_deal_finder/gui/assets{':' if not IS_WINDOWS else ';'}tbr_deal_finder/gui/assets",
        "--hidden-import", "flet",
        "--hidden-import", "flet.web", 
        "--hidden-import", "flet.core",
        "--hidden-import", "flet_desktop",
        "--hidden-import", "plotly",
        "--distpath", "gui_dist",
        "--clean",  # Clean previous builds
        MAIN_SCRIPT
    ]
    
    # Add icon if available
    if icon_file:
        cmd.extend(["--icon", icon_file])
    
    # Platform-specific options
    if IS_MACOS:
        cmd.extend([
            "--windowed",  # No console window
            "--onedir",    # Create .app bundle
            "--osx-bundle-identifier", PROJECT_IDENTIFIER,
        ])
    elif IS_WINDOWS:
        cmd.extend([
            "--onefile",   # Single .exe file
            "--windowed",  # No console window
        ])
    elif IS_LINUX:
        cmd.extend([
            "--onefile",   # Single executable
        ])
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ PyInstaller build completed successfully for {CURRENT_PLATFORM}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller build failed: {e}")
        return False


def sign_application():
    """Sign the application for the current platform."""
    if IS_MACOS:
        return sign_macos_app()
    elif IS_WINDOWS:
        return sign_windows_exe()
    else:
        print("ℹ️  No signing required for Linux")
        return True


def sign_macos_app():
    """Sign macOS app bundle with ad-hoc signing."""
    app_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.app"
    if not app_path.exists():
        print(f"❌ macOS app bundle not found at {app_path}")
        return False
    
    print("🔐 Signing macOS app bundle with ad-hoc signing...")
    
    try:
        # First, remove any existing signatures that might conflict
        subprocess.run([
            "codesign", "--remove-signature", "--deep", str(app_path)
        ], check=False, capture_output=True)  # Don't fail if no signature exists
        
        # Sign all frameworks and libraries first (ad-hoc signing doesn't use timestamps)
        frameworks_dir = app_path / "Contents" / "Frameworks"
        if frameworks_dir.exists():
            for item in frameworks_dir.rglob("*"):
                if item.is_file() and (item.suffix in ['.dylib', '.so'] or 'framework' in str(item).lower()):
                    subprocess.run([
                        "codesign", "--force", "--sign", SIGNING_IDENTITY, str(item)
                    ], check=True, capture_output=True)
        
        # Sign all internal binaries
        internal_dir = app_path / "Contents" / "MacOS"
        if internal_dir.exists():
            for item in internal_dir.rglob("*"):
                if item.is_file() and item != internal_dir / f"{PROJECT_NAME.replace(' ', '')}":
                    subprocess.run([
                        "codesign", "--force", "--sign", SIGNING_IDENTITY, str(item)
                    ], check=False, capture_output=True)  # Don't fail on non-binary files
        
        # Create entitlements file for library validation bypass
        entitlements_path = Path("entitlements.plist")
        entitlements_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>'''
        entitlements_path.write_text(entitlements_content)
        
        # Sign the main executable with entitlements
        main_executable = app_path / "Contents" / "MacOS" / f"{PROJECT_NAME.replace(' ', '')}"
        subprocess.run([
            "codesign", "--force", "--sign", SIGNING_IDENTITY,
            "--entitlements", str(entitlements_path),
            str(main_executable)
        ], check=True)
        
        # Finally, sign the main app bundle with entitlements
        subprocess.run([
            "codesign", "--force", "--sign", SIGNING_IDENTITY,
            "--entitlements", str(entitlements_path),
            str(app_path)
        ], check=True)
        
        # Clean up entitlements file
        entitlements_path.unlink()
        
        print("✅ macOS app bundle signed successfully (ad-hoc)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ macOS app bundle signing failed: {e}")
        # Try a simpler signing approach as fallback
        try:
            print("🔄 Trying simpler signing approach...")
            subprocess.run([
                "codesign", "--force", "--deep", "--sign", SIGNING_IDENTITY, str(app_path)
            ], check=True)
            print("✅ macOS app bundle signed with simpler approach")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"❌ Fallback signing also failed: {e2}")
            return False


def sign_windows_exe():
    """Sign Windows executable with self-signed certificate."""
    exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.exe"
    if not exe_path.exists():
        print(f"❌ Windows executable not found at {exe_path}")
        return False
    
    print("🔐 Signing Windows executable with self-signed certificate...")
    
    cert_name = SIGNING_IDENTITY
    
    try:
        # First, try to find the certificate by subject name
        cmd = [
            "signtool", "sign",
            "/n", cert_name,         # Certificate subject name
            "/fd", "SHA256",         # Hash algorithm
            "/tr", "http://timestamp.digicert.com",  # Timestamp server
            "/td", "SHA256",         # Timestamp digest algorithm
            str(exe_path)
        ]
        
        subprocess.run(cmd, check=True)
        print("✅ Windows executable signed successfully (self-signed)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Self-signed signing failed, trying alternative method: {e}")
        
        # Alternative: Try to find certificate by store location
        try:
            cmd = [
                "signtool", "sign",
                "/s", "My",             # Certificate store
                "/n", cert_name,        # Certificate subject name
                "/fd", "SHA256",
                str(exe_path)
            ]
            
            subprocess.run(cmd, check=True)
            print("✅ Windows executable signed successfully (self-signed, alternative method)")
            return True
            
        except subprocess.CalledProcessError as e2:
            print(f"❌ Both signing methods failed: {e2}")
            print("💡 Certificate may not be properly installed in certificate store")
            return False


def create_distribution():
    """Create platform-specific distribution package."""
    if IS_MACOS:
        return create_macos_dmg()
    elif IS_WINDOWS:
        return create_windows_installer()
    elif IS_LINUX:
        return create_linux_appimage()
    else:
        print(f"⚠️  No distribution package creation for {CURRENT_PLATFORM}")
        return True


def create_macos_dmg():
    """Create a macOS DMG file."""
    print("📦 Creating macOS DMG...")
    
    app_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.app"
    dmg_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.dmg"
    
    if not app_path.exists():
        print(f"❌ macOS app bundle not found at {app_path}")
        return False
    
    # Remove existing DMG
    if dmg_path.exists():
        dmg_path.unlink()
    
    try:
        subprocess.run([
            "hdiutil", "create",
            "-volname", PROJECT_NAME,
            "-srcfolder", str(app_path),
            "-ov", "-format", "UDZO",
            str(dmg_path)
        ], check=True)
        
        print(f"✅ macOS DMG created: {dmg_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ macOS DMG creation failed: {e}")
        return False


def create_windows_installer():
    """Create Windows installer or prepare for distribution."""
    print("📦 Creating Windows installer...")
    
    exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.exe"
    if not exe_path.exists():
        print(f"❌ Windows executable not found at {exe_path}")
        return False
    
    # For now, just confirm the .exe exists and provide guidance
    exe_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
    print(f"✅ Windows executable ready: {exe_path} ({exe_size:.1f} MB)")
    print("💡 To create an installer, use tools like:")
    print("   • NSIS (Nullsoft Scriptable Install System)")
    print("   • Inno Setup")
    print("   • WiX Toolset")
    print("   • Or distribute the .exe directly")
    
    return True


def create_linux_appimage():
    """Create Linux AppImage (placeholder)."""
    print("📦 Creating Linux AppImage...")
    
    exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}"
    if not exe_path.exists():
        print(f"❌ Linux executable not found at {exe_path}")
        return False
    
    print(f"✅ Linux executable ready: {exe_path}")
    print("💡 To create an AppImage, use tools like:")
    print("   • AppImageBuilder")
    print("   • linuxdeploy")
    print("   • Or distribute the executable directly")
    
    return True


def sign_distribution():
    """Sign the distribution package for the current platform."""
    if IS_MACOS:
        return sign_macos_dmg()
    elif IS_WINDOWS:
        # Windows exe is already signed in sign_application()
        print("ℹ️  Windows executable already signed")
        return True
    else:
        print("ℹ️  No distribution signing required for Linux")
        return True


def sign_macos_dmg():
    """Sign the macOS DMG file."""
    if not SIGNING_IDENTITY:
        print("⚠️  Skipping macOS DMG signing (no identity)")
        return True
    
    dmg_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.dmg"
    if not dmg_path.exists():
        print(f"❌ macOS DMG not found at {dmg_path}")
        return False
    
    print("🔐 Signing macOS DMG...")
    
    try:
        # Ad-hoc signing doesn't support timestamps, so don't use --timestamp
        subprocess.run([
            "codesign", "--force", "--verify", "--verbose",
            "--sign", SIGNING_IDENTITY,
            str(dmg_path)
        ], check=True)
        
        print("✅ macOS DMG signed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ macOS DMG signing failed: {e}")
        return False


def verify_signatures():
    """Verify signatures for the current platform."""
    if not SIGNING_IDENTITY:
        print("ℹ️  No signatures to verify (unsigned build)")
        return
    
    print("🔍 Verifying signatures...")
    
    if IS_MACOS:
        verify_macos_signatures()
    elif IS_WINDOWS:
        verify_windows_signatures()
    else:
        print("ℹ️  No signature verification needed for Linux")


def verify_macos_signatures():
    """Verify macOS signatures."""
    app_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.app"
    dmg_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.dmg"
    
    if app_path.exists():
        try:
            result = subprocess.run([
                "codesign", "--verify", "--deep", "--strict", str(app_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ macOS app bundle signature verified")
            else:
                print(f"⚠️  macOS app bundle signature issues: {result.stderr}")
        except Exception as e:
            print(f"❌ Error verifying macOS app bundle: {e}")
    
    if dmg_path.exists():
        try:
            result = subprocess.run([
                "codesign", "--verify", "--strict", str(dmg_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ macOS DMG signature verified")
            else:
                print(f"⚠️  macOS DMG signature issues: {result.stderr}")
        except Exception as e:
            print(f"❌ Error verifying macOS DMG: {e}")


def verify_windows_signatures():
    """Verify Windows signatures."""
    exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.exe"
    
    if exe_path.exists():
        try:
            result = subprocess.run([
                "signtool", "verify", "/pa", str(exe_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Windows executable signature verified")
            else:
                print(f"⚠️  Windows executable signature issues: {result.stderr}")
        except Exception as e:
            print(f"❌ Error verifying Windows executable: {e}")


def main():
    """Main cross-platform build function with self-signing."""
    print(f"🚀 Building {PROJECT_NAME} for {CURRENT_PLATFORM} with self-signing")
    print("=" * 70)
    
    # Check prerequisites
    if not Path(MAIN_SCRIPT).exists():
        print(f"❌ Main script not found: {MAIN_SCRIPT}")
        return
    
    # Check signing setup
    can_sign = check_signing_identity()
    if not can_sign:
        if IS_MACOS:
            print("❌ macOS ad-hoc signing failed")
        elif IS_WINDOWS:
            print("❌ Windows self-signed certificate setup failed")
        else:
            print("ℹ️  Linux builds don't require signing")
        
        if IS_MACOS or IS_WINDOWS:
            print("   Proceeding without signing - users will see more security warnings")
    
    # Build the application
    print("🔨 Building application...")
    if not build_with_pyinstaller():
        print("❌ Build failed")
        return
    
    # Sign application
    if can_sign:
        print("🔐 Signing application...")
        if not sign_application():
            print("❌ Application signing failed")
            return
    
    # Create distribution package
    print("📦 Creating distribution package...")
    if not create_distribution():
        print("❌ Distribution package creation failed")
        return
    
    # Sign distribution package (macOS only)
    if can_sign and IS_MACOS:
        print("🔐 Signing distribution package...")
        if not sign_distribution():
            print("❌ Distribution package signing failed")
            return
    
    # Verify signatures
    if can_sign:
        verify_signatures()
    
    print("\n" + "=" * 70)
    print("🎉 Build completed successfully!")
    
    # Show output information
    show_build_output_info(can_sign)
    
    # Platform-specific next steps
    show_next_steps(can_sign)


def show_build_output_info(can_sign):
    """Show information about the built artifacts."""
    if IS_MACOS:
        dmg_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.dmg"
        if dmg_path.exists():
            size_mb = dmg_path.stat().st_size / (1024 * 1024)
            print(f"📦 macOS DMG: {dmg_path} ({size_mb:.1f} MB)")
    
    elif IS_WINDOWS:
        exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 Windows EXE: {exe_path} ({size_mb:.1f} MB)")
    
    elif IS_LINUX:
        exe_path = Path("gui_dist") / f"{PROJECT_NAME.replace(' ', '')}"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 Linux executable: {exe_path} ({size_mb:.1f} MB)")
    
    if can_sign:
        if IS_MACOS:
            print("🔐 Self-signed (ad-hoc) and ready for distribution")
        elif IS_WINDOWS:
            print("🔐 Self-signed (certificate) and ready for distribution")
        else:
            print("ℹ️  Ready for distribution (signing not required)")
    else:
        if IS_MACOS or IS_WINDOWS:
            print("⚠️  Unsigned - users will see more security warnings")
        else:
            print("ℹ️  Ready for distribution (signing not required)")


def show_next_steps(can_sign):
    """Show platform-specific next steps."""
    print("\n💡 Next steps:")
    
    if IS_MACOS:
        print("   • Upload DMG to GitHub releases or your distribution platform")
        if can_sign:
            print("   • Users can bypass security warnings easily (right-click → Open)")
        else:
            print("   • Test on a clean Mac to verify user experience")
    elif IS_WINDOWS:
        print("   • Upload EXE to GitHub releases or your distribution platform")
        if can_sign:
            print("   • Users will see manageable security warnings")
        else:
            print("   • Test on a clean Windows machine to verify user experience")
    elif IS_LINUX:
        print("   • Upload executable to GitHub releases or your distribution platform")
        print("   • Consider creating an AppImage for better portability")
    
    print("   • Test the installation process on target systems")


if __name__ == "__main__":
    main()