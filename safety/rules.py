class SafetyLevel:
    AUTO = "auto"
    NOTIFY = "notify"
    CONFIRM = "confirm"
    NEVER = "never"

class SafetyRules:
    def __init__(self):
        self.action_rules = {
            "system": {"go_home": "auto", "go_back": "auto", "screenshot": "auto", "read_screen": "auto"},
            "youtube": {"search": "notify", "play": "notify", "open": "auto"},
            "spotify": {"play": "notify", "search": "notify", "open": "auto"},
            "brave": {"search": "notify", "open": "auto"},
            "notes": {"write": "notify", "open": "auto"},
            "whatsapp": {"send_message": "confirm", "open": "auto"},
            "telegram": {"send_message": "confirm", "open": "auto"},
            "messages": {"send_message": "confirm", "open": "auto"},
            "dialer": {"call": "confirm", "open": "auto"},
            "camera": {"capture": "notify", "open": "auto"},
        }
        self.blacklist = ["settings", "com.android.settings", "authenticator", "com.google.android.apps.authenticator", "com.android.vending"]
        self.sensitive_keywords = ["bank", "wallet", "pay", "money", "password", "auth", "2fa", "authenticator", "finance", "binance", "paypal", "mpesa"]
    
    def check(self, app: str, action: str) -> str:
        for blocked in self.blacklist:
            if blocked in app.lower():
                return "never"
        for keyword in self.sensitive_keywords:
            if keyword in app.lower():
                return "never"
        app_rules = self.action_rules.get(app.lower(), {})
        if action in app_rules:
            return app_rules[action]
        if action in ["send_message", "send", "post", "share", "publish"]:
            return "confirm"
        if action in ["delete", "remove", "uninstall", "clear"]:
            return "never"
        return "notify"
    
    def is_allowed(self, app: str, action: str) -> bool:
        return self.check(app, action) != "never"
    
    def needs_confirmation(self, app: str, action: str) -> bool:
        return self.check(app, action) == "confirm"
