from __future__ import annotations

from domainbot.domain.status import DomainStatus
from domainbot.rdap.verisign import VerisignRdapAdapter


def test_verisign_domain_url_encodes_path_value() -> None:
    adapter = VerisignRdapAdapter()

    assert adapter.domain_url("example.com") == "https://rdap.verisign.com/com/v1/domain/example.com"


def test_200_domain_is_registered() -> None:
    result = VerisignRdapAdapter().interpret_response(
        domain="example.com",
        http_status=200,
        payload={"objectClassName": "domain", "ldhName": "example.com"},
        attempt_count=1,
    )

    assert result.outcome == DomainStatus.REGISTERED


def test_404_is_not_found_in_registry() -> None:
    result = VerisignRdapAdapter().interpret_response(
        domain="missing-example.com",
        http_status=404,
        payload={"errorCode": 404},
        attempt_count=1,
    )

    assert result.outcome == DomainStatus.NOT_FOUND_IN_REGISTRY


def test_429_and_5xx_are_retryable() -> None:
    adapter = VerisignRdapAdapter()

    assert (
        adapter.interpret_response("example.com", 429, {"errorCode": 429}, 1).outcome
        == DomainStatus.RETRYABLE_ERROR
    )
    assert (
        adapter.interpret_response("example.com", 503, {"errorCode": 503}, 1).outcome
        == DomainStatus.RETRYABLE_ERROR
    )


def test_unexpected_200_json_is_parse_error() -> None:
    result = VerisignRdapAdapter().interpret_response(
        domain="example.com",
        http_status=200,
        payload={"objectClassName": "entity"},
        attempt_count=1,
    )

    assert result.outcome == DomainStatus.PARSE_ERROR
