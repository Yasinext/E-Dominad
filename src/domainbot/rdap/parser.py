from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domainbot.rdap.result import ParsedRdapDomain


class RdapParseError(ValueError):
    pass


def parse_domain_response(payload: dict[str, Any]) -> ParsedRdapDomain:
    if payload.get("objectClassName") != "domain":
        raise RdapParseError("RDAP response is not a domain object.")

    events = payload.get("events")
    entities = payload.get("entities")
    nameservers = payload.get("nameservers")

    return ParsedRdapDomain(
        ldh_name=_optional_str(payload.get("ldhName")),
        unicode_name=_optional_str(payload.get("unicodeName")),
        handle=_optional_str(payload.get("handle")),
        statuses=tuple(str(value) for value in payload.get("status", []) if value is not None),
        registration_date=_event_date(events, "registration"),
        expiration_date=_event_date(events, "expiration"),
        last_changed_date=_event_date(events, "last changed"),
        registrar_name=_registrar_name(entities),
        registrar_iana_id=_registrar_iana_id(entities),
        nameservers=tuple(
            str(item["ldhName"])
            for item in nameservers or []
            if isinstance(item, dict) and item.get("ldhName")
        ),
        rdap_conformance=tuple(
            str(value) for value in payload.get("rdapConformance", []) if value is not None
        ),
    )


def _event_date(events: Any, action: str) -> datetime | None:
    if not isinstance(events, list):
        return None
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("eventAction", "")).lower() != action:
            continue
        return _parse_datetime(event.get("eventDate"))
    return None


def _registrar_name(entities: Any) -> str | None:
    registrar = _registrar_entity(entities)
    if not registrar:
        return None
    vcard = registrar.get("vcardArray")
    if not isinstance(vcard, list) or len(vcard) < 2 or not isinstance(vcard[1], list):
        return None
    for item in vcard[1]:
        if isinstance(item, list) and len(item) >= 4 and item[0] == "fn":
            return _optional_str(item[3])
    return None


def _registrar_iana_id(entities: Any) -> str | None:
    registrar = _registrar_entity(entities)
    if not registrar:
        return None
    public_ids = registrar.get("publicIds")
    if not isinstance(public_ids, list):
        return None
    for item in public_ids:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).lower() in {"iana registrar id", "registrar id"}:
            return _optional_str(item.get("identifier"))
    return None


def _registrar_entity(entities: Any) -> dict[str, Any] | None:
    if not isinstance(entities, list):
        return None
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        roles = entity.get("roles")
        if isinstance(roles, list) and "registrar" in {str(role).lower() for role in roles}:
            return entity
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
