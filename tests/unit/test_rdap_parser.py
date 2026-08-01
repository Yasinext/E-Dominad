from __future__ import annotations

from domainbot.rdap.parser import parse_domain_response


def test_parse_domain_response_with_optional_fields() -> None:
    parsed = parse_domain_response(
        {
            "objectClassName": "domain",
            "ldhName": "example.com",
            "handle": "123",
            "status": ["client transfer prohibited"],
            "events": [
                {"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2030-01-01T00:00:00Z"},
            ],
            "entities": [
                {
                    "roles": ["registrar"],
                    "vcardArray": ["vcard", [["fn", {}, "text", "Example Registrar"]]],
                    "publicIds": [{"type": "IANA Registrar ID", "identifier": "9999"}],
                }
            ],
            "nameservers": [{"ldhName": "ns1.example.com"}],
            "rdapConformance": ["rdap_level_0"],
        }
    )

    assert parsed.ldh_name == "example.com"
    assert parsed.registrar_name == "Example Registrar"
    assert parsed.registrar_iana_id == "9999"
    assert parsed.nameservers == ("ns1.example.com",)
    assert parsed.registration_date is not None
    assert parsed.registration_date.tzinfo is not None


def test_parse_domain_response_tolerates_missing_optional_fields() -> None:
    parsed = parse_domain_response({"objectClassName": "domain", "ldhName": "example.com"})

    assert parsed.ldh_name == "example.com"
    assert parsed.registrar_name is None
    assert parsed.nameservers == ()
