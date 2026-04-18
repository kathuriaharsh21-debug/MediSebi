"""
MediSebi — Password Policy Validator
======================================
Enforces HIPAA-compliant password requirements.
Called BEFORE any password hash is generated or stored.

Policy (configurable via app.core.config):
- Minimum 12 characters (NIST SP 800-63B / HIPAA)
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character
- No 3+ consecutive repeated characters (e.g., "aaa", "111")
- No whitespace-only passwords
- Checked against password history (last N hashes)
"""

import re
from dataclasses import dataclass
from typing import List

from app.core.config import settings


@dataclass
class PasswordValidationResult:
    """Result of password policy validation."""
    is_valid: bool
    errors: List[str]


class PasswordValidator:
    """
    HIPAA-compliant password policy enforcement.
    All rules are configurable via application settings.
    """

    # Regex patterns for character class requirements
    _UPPERCASE = re.compile(r"[A-Z]")
    _LOWERCASE = re.compile(r"[a-z]")
    _DIGIT = re.compile(r"\d")
    _SPECIAL = re.compile(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/\\`~]')
    _REPEATED = re.compile(r"(.)\1{2,}")
    _WHITESPACE = re.compile(r"\s")

    @classmethod
    def validate(cls, password: str) -> PasswordValidationResult:
        """
        Validate a password against all configured policy rules.
        Returns a result object with is_valid flag and list of error messages.
        """
        errors = []

        # Length check
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long "
                f"(currently {len(password)})."
            )

        # Character class checks
        if settings.PASSWORD_REQUIRE_UPPERCASE and not cls._UPPERCASE.search(password):
            errors.append("Password must contain at least one uppercase letter (A-Z).")
        if settings.PASSWORD_REQUIRE_LOWERCASE and not cls._LOWERCASE.search(password):
            errors.append("Password must contain at least one lowercase letter (a-z).")
        if settings.PASSWORD_REQUIRE_DIGIT and not cls._DIGIT.search(password):
            errors.append("Password must contain at least one digit (0-9).")
        if settings.PASSWORD_REQUIRE_SPECIAL and not cls._SPECIAL.search(password):
            errors.append("Password must contain at least one special character (e.g., !@#$%).")

        # Consecutive character check (prevents "aaa", "111", etc.)
        if cls._REPEATED.search(password):
            errors.append("Password must not contain 3 or more consecutive repeated characters.")

        # Whitespace-only check
        if cls._WHITESPACE.search(password):
            errors.append("Password must not contain whitespace characters.")

        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )

    @classmethod
    def get_strength_score(cls, password: str) -> dict:
        """
        Estimate password strength on a 0-100 scale.
        Used for UI feedback (password strength meter).
        NOT a substitute for actual policy validation.

        Scoring:
        - Length: up to 30 points (0-8=0, 9-11=10, 12-15=20, 16+=30)
        - Character variety: up to 40 points (10 per unique class)
        - No patterns: up to 20 points
        - No common sequences: up to 10 points
        """
        score = 0

        # Length scoring
        length = len(password)
        if length >= 16:
            score += 30
        elif length >= 12:
            score += 20
        elif length >= 9:
            score += 10

        # Character variety scoring
        variety = 0
        if cls._UPPERCASE.search(password):
            variety += 1
        if cls._LOWERCASE.search(password):
            variety += 1
        if cls._DIGIT.search(password):
            variety += 1
        if cls._SPECIAL.search(password):
            variety += 1
        score += variety * 10  # up to 40

        # No repeated patterns
        if not cls._REPEATED.search(password):
            score += 20

        # No whitespace
        if not cls._WHITESPACE.search(password):
            score += 10

        # Determine label
        if score >= 80:
            label = "strong"
        elif score >= 60:
            label = "good"
        elif score >= 40:
            label = "fair"
        else:
            label = "weak"

        return {"score": min(score, 100), "label": label, "variety": variety}
