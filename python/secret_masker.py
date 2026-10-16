"""Robot Framework library that masks secrets in every log message.

Importing it (from auth_keywords.robot) makes it active for every suite that uses
the shared keywords, whether run by the runners or directly with robot.
"""
import os
import re

MASK = "********"

# Patterns for values that appear in requests and responses
PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/=]+"),
    re.compile(r"""((?:['"]|\b)(?:access_token|id_token|refresh_token|client_secret|password)['"]?\s*[:=]\s*['"]?)[^'"&,}\s]+"""),
    re.compile(r"(\$\{(?:token|ACCESS_TOKEN|authorization)\}\s*=\s*)\S+"),
]
SECRET_ENV_VARS = ("CLIENT_SECRET", "API_PASSWORD", "COMPATIBILITY_COOKIE")


class secret_masker:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self
        self._known = set()

    def _secrets(self):
        values = {os.environ.get(name, "") for name in SECRET_ENV_VARS} | self._known
        return sorted((v for v in values if len(v) >= 6), key=len, reverse=True)

    def mask(self, text):
        for secret in self._secrets():
            text = text.replace(secret, MASK)
            for part in secret.split(";"):
                part = part.strip()
                if "=" in part and len(part.split("=", 1)[1]) >= 6:
                    text = text.replace(part.split("=", 1)[1], MASK)
        for pattern in PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + MASK, text)
        return text

    def log_message(self, message):
        # Remember issued tokens so they are masked wherever they appear later
        for match in re.finditer(r"['\"]access_token['\"]\s*:\s*['\"]([^'\"]+)", message.message or ""):
            self._known.add(match.group(1))
        message.message = self.mask(message.message or "")
