from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rdw.config import load_config
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping, load_yaml_mapping_text

ARTIFACT_REQUEST_SCHEMA = "rdw-artifact-request/v1"
ARTIFACT_RECEIPT_SCHEMA = "rdw-artifact-receipt/v1"

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])(?:\s+|$)")
_CTA_RE = re.compile(
    r"\b(?:would|could|can|open to|happy to|glad to|interested in|hear how|"
    r"share more|send over|chat|conversation|connect|talk)\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https://\S+", re.IGNORECASE)
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "because",
    "being",
    "from",
    "have",
    "into",
    "more",
    "role",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "through",
    "with",
    "work",
    "your",
}


def validate_artifact_file(path: Path, *, root: Path | None = None) -> YamlMapping:
    return validate_artifact_request(load_yaml_mapping(path), root=root)


def validate_artifact_text(
    text: str, *, source: str = "<stdin>", root: Path | None = None
) -> YamlMapping:
    return validate_artifact_request(load_yaml_mapping_text(text, source=source), root=root)


def validate_artifact_request(request: YamlMapping, *, root: Path | None = None) -> YamlMapping:
    config = load_config("artifacts.yaml", root)
    profiles = _mapping(config.get("artifact_profiles"))
    artifact_type = _text(request.get("artifact_type"))
    profile = _mapping(profiles.get(artifact_type))
    checks: list[YamlValue] = []

    _check(
        checks,
        "schema",
        request.get("schema_version") == ARTIFACT_REQUEST_SCHEMA,
        f"schema_version must be {ARTIFACT_REQUEST_SCHEMA}",
    )
    _check(
        checks, "artifact_id", bool(_text(request.get("artifact_id"))), "artifact_id is required"
    )
    _check(
        checks,
        "artifact_profile",
        bool(profile),
        f"unknown artifact_type: {artifact_type or '<empty>'}",
    )
    _check(checks, "channel", bool(_text(request.get("channel"))), "channel is required")
    _check(checks, "intent", bool(_text(request.get("intent"))), "intent is required")

    content = _mapping(request.get("content"))
    subject = _text(content.get("subject"))
    body = _text(content.get("body"))
    _check(checks, "content", bool(body), "content.body is required")

    constraints = _mapping(request.get("constraints"))
    approval_required = constraints.get("human_approval_required") is True
    _check(
        checks,
        "human_approval_boundary",
        approval_required,
        "constraints.human_approval_required must be true",
    )

    evidence = [_mapping(item) for item in _sequence(request.get("evidence"))]
    evidence_ids = {_text(item.get("id")) for item in evidence if _text(item.get("id"))}
    valid_evidence = all(
        _text(item.get("id"))
        and _text(item.get("kind"))
        and _text(item.get("text"))
        and _text(item.get("source"))
        for item in evidence
    )
    minimum_evidence = _integer(profile.get("minimum_evidence"), 0)
    _check(
        checks,
        "evidence_shape",
        valid_evidence and len(evidence) >= minimum_evidence,
        f"at least {minimum_evidence} complete evidence item(s) are required",
    )

    required_kinds = {_text(item) for item in _sequence(profile.get("required_evidence_kinds"))}
    present_kinds = {_text(item.get("kind")) for item in evidence}
    missing_kinds = sorted(required_kinds - present_kinds)
    _check(
        checks,
        "required_evidence",
        not missing_kinds,
        "missing evidence kinds: " + ", ".join(missing_kinds),
    )

    bindings = [_mapping(item) for item in _sequence(request.get("claim_bindings"))]
    malformed_bindings = [
        index
        for index, item in enumerate(bindings)
        if not _is_valid_claim_binding(item, evidence_ids)
    ]
    _check(
        checks,
        "claim_bindings_well_formed",
        not malformed_bindings,
        "claim binding(s) are malformed or reference unknown evidence: "
        + ", ".join(str(index) for index in malformed_bindings),
    )
    valid_bindings = [item for item in bindings if _is_valid_claim_binding(item, evidence_ids)]
    minimum_bindings = _integer(profile.get("minimum_claim_bindings"), 0)
    _check(
        checks,
        "claim_bindings",
        len(valid_bindings) >= minimum_bindings,
        f"at least {minimum_bindings} claim binding(s) to known evidence are required",
    )

    unrepresented_bindings = [
        index
        for index, item in enumerate(valid_bindings)
        if not _evidence_is_represented(_text(item.get("claim")), body)
    ]
    _check(
        checks,
        "claim_bindings_in_content",
        not unrepresented_bindings,
        "claim binding(s) are not represented in content: "
        + ", ".join(str(index) for index in unrepresented_bindings),
    )

    if body and required_kinds:
        unrepresented = [
            kind
            for kind in sorted(required_kinds)
            if not any(
                _text(item.get("kind")) == kind
                and _evidence_is_represented(_text(item.get("text")), body)
                for item in evidence
            )
        ]
        _check(
            checks,
            "evidence_in_content",
            not unrepresented,
            "content does not reflect evidence kinds: " + ", ".join(unrepresented),
        )

    _check_limits(checks, request, profile, subject=subject, body=body)

    blocked_phrases = [
        _text(item).lower() for item in _sequence(profile.get("blocked_phrases")) if _text(item)
    ]
    combined = f"{subject}\n{body}".lower()
    found_blocked = [phrase for phrase in blocked_phrases if phrase in combined]
    _check(
        checks,
        "blocked_phrases",
        not found_blocked,
        "blocked phrase(s): " + ", ".join(found_blocked),
    )

    if profile.get("require_cta") is True:
        _check(
            checks,
            "clear_cta",
            bool(_CTA_RE.search(body)),
            "content needs a clear, low-friction CTA",
        )
    if profile.get("require_proof_link") is True:
        _check(
            checks, "proof_link", bool(_URL_RE.search(body)), "content needs an HTTPS proof link"
        )

    ok = all(_mapping(item).get("status") == "pass" for item in checks)
    reasons: list[YamlValue] = [
        _text(_mapping(item).get("detail"))
        for item in checks
        if _mapping(item).get("status") == "fail"
    ]
    return {
        "schema_version": ARTIFACT_RECEIPT_SCHEMA,
        "policy_version": _integer(config.get("version"), 1),
        "artifact_id": _text(request.get("artifact_id")),
        "artifact_type": artifact_type,
        "channel": _text(request.get("channel")),
        "request_hash": _hash(request),
        "contract_hash": _hash({key: value for key, value in request.items() if key != "content"}),
        "artifact_hash": _hash({"subject": subject, "body": body}),
        "ok": ok,
        "status": "approved_for_human_review" if ok else "blocked",
        "human_approval_required": True,
        "checks": checks,
        "reasons": reasons,
    }


def _check_limits(
    checks: list[YamlValue],
    request: YamlMapping,
    profile: YamlMapping,
    *,
    subject: str,
    body: str,
) -> None:
    constraints = _mapping(request.get("constraints"))
    limits = (
        ("body_words", len(_TOKEN_RE.findall(body)), "max_words"),
        ("body_characters", len(body), "max_chars"),
        ("subject_words", len(_TOKEN_RE.findall(subject)), "max_subject_words"),
        ("subject_characters", len(subject), "max_subject_chars"),
        (
            "sentences",
            len([part for part in _SENTENCE_RE.split(body) if part.strip()]),
            "max_sentences",
        ),
    )
    for check_id, actual, key in limits:
        profile_limit = _optional_integer(profile.get(key))
        requested_limit = _optional_integer(constraints.get(key))
        candidates = [value for value in (profile_limit, requested_limit) if value is not None]
        if not candidates:
            continue
        limit = min(candidates)
        _check(checks, check_id, actual <= limit, f"{check_id} is {actual}; maximum is {limit}")


def _evidence_is_represented(evidence_text: str, body: str) -> bool:
    evidence_tokens = _significant_tokens(evidence_text)
    body_tokens = _significant_tokens(body)
    return bool(evidence_tokens & body_tokens)


def _is_valid_claim_binding(item: YamlMapping, evidence_ids: set[str]) -> bool:
    evidence_values = _sequence(item.get("evidence_ids"))
    return (
        bool(_text(item.get("claim")))
        and bool(evidence_values)
        and all(_text(value) in evidence_ids for value in evidence_values)
    )


def _significant_tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(value)
        if len(token) >= 4 and token.lower() not in _STOPWORDS
    }


def _check(checks: list[YamlValue], check_id: str, passed: bool, detail: str) -> None:
    checks.append({"id": check_id, "status": "pass" if passed else "fail", "detail": detail})


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mapping(value: YamlValue | None) -> YamlMapping:
    return value if isinstance(value, dict) else {}


def _sequence(value: YamlValue | None) -> list[YamlValue]:
    return value if isinstance(value, list) else []


def _text(value: YamlValue | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _integer(value: YamlValue | None, fallback: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else fallback


def _optional_integer(value: YamlValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
