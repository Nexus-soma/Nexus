"""
Nexus Phone Bridge
A clean Python wrapper around ADB commands for Android device control.
Supports Android 11+ wireless pairing and standard ADB connections.
"""

import subprocess
import os
from typing import Optional


class PhoneBridge:
    """Controls an Android phone via ADB."""

    def __init__(self, device_ip: Optional[str] = None):
        self.device_ip = device_ip
        if device_ip:
            self.connect()

    # ─── Pairing (Android 11+) ─────────────────────

    def pair(self, pairing_ip: str, pairing_port: str, pairing_code: str) -> bool:
        """
        Pair with device using 6-digit code.
        Used for Android 11+ wireless debugging.
        The pairing IP/port are shown in the pairing dialog on the phone.
        """
        result = subprocess.run(
            ["adb", "pair", f"{pairing_ip}:{pairing_port}"],
            input=f"{pairing_code}\n",
            capture_output=True, text=True
        )
        return "Successfully paired" in result.stdout

    # ─── Connection ───────────────────────────────

    def connect(self, port: str = "5555") -> bool:
        """Establish wireless ADB connection."""
        if not self.device_ip:
            return False
        result = subprocess.run(
            ["adb", "connect", f"{self.device_ip}:{port}"],
            capture_output=True, text=True
        )
        return "connected" in result.stdout.lower()

    def disconnect(self, port: str = "5555") -> bool:
        """Disconnect from the device."""
        if not self.device_ip:
            return False
        subprocess.run(
            ["adb", "disconnect", f"{self.device_ip}:{port}"],
            capture_output=True, text=True
        )
        return True

    def is_connected(self) -> bool:
        """Check if device is currently connected."""
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True
        )
        if self.device_ip:
            return self.device_ip in result.stdout and "device" in result.stdout
        return False

    # ─── Screen Actions ────────────────────────────

    def tap(self, x: int, y: int) -> bool:
        """Tap the screen at given coordinates."""
        subprocess.run(
            ["adb", "shell", "input", "tap", str(x), str(y)],
            capture_output=True
        )
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe from (x1,y1) to (x2,y2)."""
        subprocess.run(
            ["adb", "shell", "input", "swipe",
             str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
            capture_output=True
        )
        return True

    def type_text(self, text: str) -> bool:
        """Type text into the currently focused field."""
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        subprocess.run(
            ["adb", "shell", "input", "text", escaped],
            capture_output=True
        )
        return True

    def press_key(self, keycode: int) -> bool:
        """Send a keyevent (3=Home, 4=Back, 26=Power, 84=Search)."""
        subprocess.run(
            ["adb", "shell", "input", "keyevent", str(keycode)],
            capture_output=True
        )
        return True

    # ─── App Control ───────────────────────────────

    def open_app(self, package_name: str) -> bool:
        """Open an app by its package name using monkey runner."""
        subprocess.run(
            ["adb", "shell", "monkey", "-p", package_name,
             "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True
        )
        return True

    def open_app_via_am(self, package_name: str, activity: str = ".Main") -> bool:
        """Open an app using am start (alternative method)."""
        subprocess.run(
            ["adb", "shell", "am", "start", "-n", f"{package_name}/{activity}"],
            capture_output=True
        )
        return True

    def open_dialer(self, number: str) -> bool:
        """Open dialer with a pre-typed number."""
        subprocess.run(
            ["adb", "shell", "am", "start", "-a",
             "android.intent.action.DIAL", "-d", f"tel:{number}"],
            capture_output=True
        )
        return True

    # ─── Information ───────────────────────────────

    def screenshot(self, save_path: str = "screenshot.png") -> bool:
        """Capture phone screen and save locally."""
        with open(save_path, "wb") as f:
            subprocess.run(
                ["adb", "exec-out", "screencap", "-p"],
                stdout=f
            )
        return os.path.exists(save_path)

    def get_battery_level(self) -> Optional[int]:
        """Return battery percentage."""
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "battery"],
            capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if "level:" in line:
                return int(line.split(":")[1].strip())
        return None

    def list_packages(self, filter_term: str = "") -> list:
        """List installed packages. Optional filter term."""
        cmd = ["adb", "shell", "pm", "list", "packages"]
        if filter_term:
            cmd.append(filter_term)
        result = subprocess.run(cmd, capture_output=True, text=True)
        packages = []
        for line in result.stdout.split("\n"):
            if line.startswith("package:"):
                packages.append(line.replace("package:", "").strip())
        return packages

    # ─── Utility ───────────────────────────────────

    def run_raw(self, command: str) -> str:
        """Run a raw adb shell command and return output."""
        result = subprocess.run(
            ["adb", "shell"] + command.split(),
            capture_output=True, text=True
        )
        return result.stdout


# ─── Quick Test ────────────────────────────────────
# ─── Interactive Test ────────────────────────────
if __name__ == "__main__":
    import sys

    bridge = PhoneBridge()

    print("\n📱 Nexus Phone Bridge - Interactive Setup")
    print("─" * 40)

    # Step 1: Get phone IP
    phone_ip = input("Enter phone IP address: ").strip()
    if not phone_ip:
        print("❌ No IP provided. Exiting.")
        sys.exit(1)

    bridge.device_ip = phone_ip

    # Step 2: Get the main port from wireless debugging screen
    phone_port = input("Enter wireless debugging port (from phone screen): ").strip()
    if not phone_port:
        phone_port = "5555"  # fallback

    # Step 3: Check if pairing is needed
    print("\n🔗 Checking connection...")
    if bridge.is_connected():
        print("✅ Already connected!")
    else:
        print("Not connected. Trying to connect...")
        if bridge.connect(port=phone_port):
            print("✅ Connected without pairing!")
        else:
            print("⚠️  Connection failed. Pairing may be needed.")
            pair_now = input("Do you want to pair? (y/n): ").strip().lower()

            if pair_now == "y":
                pairing_port = input("Enter pairing port (from pairing dialog): ").strip()
                pairing_code = input("Enter 6-digit pairing code: ").strip()

                print("🔐 Pairing...")
                if bridge.pair(phone_ip, pairing_port, pairing_code):
                    print("✅ Paired! Now connecting...")
                    if bridge.connect(port=phone_port):
                        print("✅ Phone connected!")
                    else:
                        print("❌ Connection failed after pairing.")
                        sys.exit(1)
                else:
                    print("❌ Pairing failed. Check the code and port.")
                    sys.exit(1)
            else:
                print("❌ Cannot connect without pairing. Exiting.")
                sys.exit(1)

    # Step 4: Confirm connection
    if not bridge.is_connected():
        print("❌ Something went wrong. Phone not connected.")
        sys.exit(1)

    print("\n✅ Phone connected successfully!")
    print("─" * 40)

    # Step 5: Run tests
    print("\n📋 Running tests...\n")

    print("👆 Tapping screen center...")
    bridge.tap(360, 800)

    print("📸 Taking screenshot...")
    bridge.screenshot("test_screenshot.png")
    print("   Saved as test_screenshot.png")

    battery = bridge.get_battery_level()
    print(f"🔋 Battery: {battery}%")

    pkgs = bridge.list_packages("whatsapp")
    if pkgs:
        print(f"📦 WhatsApp found: {pkgs[0]}")
    else:
        print("📦 WhatsApp: not installed")

    print("\n🎉 Phone bridge is working!")
    print("─" * 40)
    