from __future__ import annotations

import re

ROOT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
DOMAIN_RE = re.compile(r"^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.com$")


class ValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalize_root(root: str) -> str:
    normalized = root.strip().lower()
    validate_root(normalized)
    return normalized


def normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower()
    validate_domain(normalized)
    return normalized


def validate_root(root: str) -> None:
    if not root:
        raise ValidationError("empty_root", "Domain kökü boş olamaz.")
    if any(token in root for token in (".", "/", "\\", ":", "?", "#", "@")):
        raise ValidationError("invalid_root", "Domain kökü URL veya nokta içeremez.")
    if not ROOT_RE.fullmatch(root):
        raise ValidationError("invalid_root", "Domain kökü geçersiz.")


def validate_domain(domain: str) -> None:
    if not domain:
        raise ValidationError("empty_domain", "Domain boş olamaz.")
    if any(token in domain for token in ("/", "\\", ":", "?", "#", "@")):
        raise ValidationError("invalid_domain", "URL, path, port veya query kabul edilmez.")
    if not DOMAIN_RE.fullmatch(domain):
        raise ValidationError("invalid_domain", "Yalnizca tek etiketli .com domain kabul edilir.")


def ensure_final_domain_length(root: str, numeric_suffix: str = "") -> None:
    label = f"{root}{numeric_suffix}"
    if len(label) > 63:
        raise ValidationError("domain_too_long", "Domain etiketi en fazla 63 karakter olabilir.")
