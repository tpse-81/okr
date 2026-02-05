import re

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"


def is_valid_email(email: str) -> bool:
    return re.match(EMAIL_REGEX, email) is not None
