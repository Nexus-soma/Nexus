#!/usr/bin/env python3
"""
Nexus Setup Wizard
One-command onboarding. Detects everything, configures everything.
"""

import subprocess
import sys
import os
import json

def print_header():
    print("\n" + "=" * 60)
    print("   🌌  N E X U S   S E T U P")
    print("   Your Cross-Device AI Companion")
    print("=" * 60)

def check_python():
    print("\n[1/5] Checking Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print("   ❌ Python 3.10+ required.")
    return False

def check_adb():
    print("\n[2/5] Checking ADB...")
    result = subprocess.run(["which", "adb"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✅ ADB found: {result.stdout.strip()}")
        return True
    print("   ❌ ADB not found. Install Android Debug Bridge.")
    print("   Arch: sudo pacman -S android-tools")
    print("   Ubuntu: sudo apt install adb")
    return False

def install_deps():
    print("\n[3/5] Installing Python dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("   ✅ Dependencies installed.")
        return True
    print(f"   ⚠️  Some dependencies may have failed.")
    return True

def setup_phone():
    print("\n[4/5] Connecting phone...")
    print("   Enable Wireless Debugging on your Android phone:")
    print("   Settings → Developer Options → Wireless Debugging → ON")
    print()
    
    ip = input("   Phone IP address: ").strip()
    port = input("   Wireless debugging port: ").strip()
    
    if ip and port:
        result = subprocess.run(
            ["adb", "connect", f"{ip}:{port}"],
            capture_output=True, text=True
        )
        if "connected" in result.stdout.lower():
            print(f"   ✅ Connected to {ip}:{port}")
            return ip, port
        else:
            print(f"   ⚠️  Could not connect. You can configure later.")
    return ip, port

def setup_config(ip, port):
    print("\n[5/5] Creating configuration...")
    
    name = input("   What should Nexus call you? ").strip() or "builder"
    
    config = {
        "phone_ip": ip or "",
        "phone_port": port or "",
        "user_name": name,
        "llm_model": "qwen2.5:0.5b"
    }
    
    with open("nexus_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"   ✅ Configuration saved.")
    
    print("\n" + "=" * 60)
    print(f"   Welcome home, {name}.")
    print(f"   Nexus is ready.")
    print(f"   Run: python brain/orchestrator.py")
    print(f"   Or add to your shell: alias nexus='cd $(pwd) && python brain/orchestrator.py'")
    print("=" * 60 + "\n")

def main():
    print_header()
    
    if not check_python():
        sys.exit(1)
    
    if not check_adb():
        print("   ⚠️  Continuing without ADB. Phone control won't work.")
    
    install_deps()
    ip, port = setup_phone()
    setup_config(ip, port)
    
    print("   Next steps:")
    print("   1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    print("   2. Pull a model: ollama pull qwen2.5:0.5b")
    print("   3. Run Nexus: python brain/orchestrator.py")
    print()

if __name__ == "__main__":
    main()
EOFcat > setup.py << 'EOF'
#!/usr/bin/env python3
"""
Nexus Setup Wizard
One-command onboarding. Detects everything, configures everything.
"""

import subprocess
import sys
import os
import json

def print_header():
    print("\n" + "=" * 60)
    print("   🌌  N E X U S   S E T U P")
    print("   Your Cross-Device AI Companion")
    print("=" * 60)

def check_python():
    print("\n[1/5] Checking Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print("   ❌ Python 3.10+ required.")
    return False

def check_adb():
    print("\n[2/5] Checking ADB...")
    result = subprocess.run(["which", "adb"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✅ ADB found: {result.stdout.strip()}")
        return True
    print("   ❌ ADB not found. Install Android Debug Bridge.")
    print("   Arch: sudo pacman -S android-tools")
    print("   Ubuntu: sudo apt install adb")
    return False

def install_deps():
    print("\n[3/5] Installing Python dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("   ✅ Dependencies installed.")
        return True
    print(f"   ⚠️  Some dependencies may have failed.")
    return True

def setup_phone():
    print("\n[4/5] Connecting phone...")
    print("   Enable Wireless Debugging on your Android phone:")
    print("   Settings → Developer Options → Wireless Debugging → ON")
    print()
    
    ip = input("   Phone IP address: ").strip()
    port = input("   Wireless debugging port: ").strip()
    
    if ip and port:
        result = subprocess.run(
            ["adb", "connect", f"{ip}:{port}"],
            capture_output=True, text=True
        )
        if "connected" in result.stdout.lower():
            print(f"   ✅ Connected to {ip}:{port}")
            return ip, port
        else:
            print(f"   ⚠️  Could not connect. You can configure later.")
    return ip, port

def setup_config(ip, port):
    print("\n[5/5] Creating configuration...")
    
    name = input("   What should Nexus call you? ").strip() or "builder"
    
    config = {
        "phone_ip": ip or "",
        "phone_port": port or "",
        "user_name": name,
        "llm_model": "qwen2.5:0.5b"
    }
    
    with open("nexus_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"   ✅ Configuration saved.")
    
    print("\n" + "=" * 60)
    print(f"   Welcome home, {name}.")
    print(f"   Nexus is ready.")
    print(f"   Run: python brain/orchestrator.py")
    print(f"   Or add to your shell: alias nexus='cd $(pwd) && python brain/orchestrator.py'")
    print("=" * 60 + "\n")

def main():
    print_header()
    
    if not check_python():
        sys.exit(1)
    
    if not check_adb():
        print("   ⚠️  Continuing without ADB. Phone control won't work.")
    
    install_deps()
    ip, port = setup_phone()
    setup_config(ip, port)
    
    print("   Next steps:")
    print("   1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    print("   2. Pull a model: ollama pull qwen2.5:0.5b")
    print("   3. Run Nexus: python brain/orchestrator.py")
    print()

if __name__ == "__main__":
    main()
