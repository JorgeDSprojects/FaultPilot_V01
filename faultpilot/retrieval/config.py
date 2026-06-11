"""Configuration loader for FaultPilot retrieval settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RouteProfile:
    """Route-specific retrieval limits."""

    bm25_k: int
    dense_k: int
    top_n_rerank: int


@dataclass(frozen=True)
class RetrievalSettings:
    """Global retrieval tuning values."""

    bm25_k: int
    dense_k: int
    rrf_k: int
    top_n_rerank: int
    final_k: int
    min_rrf_score: float
    max_context_chars: int
    dedup_by: str
    route_profiles: dict[str, RouteProfile]

    def profile_for_route(self, route: str) -> RouteProfile:
        """Return route overrides, or fall back to baseline values."""
        profile = self.route_profiles.get(route)
        if profile is not None:
            return profile
        return RouteProfile(
            bm25_k=self.bm25_k,
            dense_k=self.dense_k,
            top_n_rerank=self.top_n_rerank,
        )


@dataclass(frozen=True)
class FaultPilotSettings:
    """Top-level strongly-typed settings object."""

    retrieval: RetrievalSettings
    raw: dict[str, Any]


def load_settings(path: Path) -> FaultPilotSettings:
    """Load settings YAML and expose typed retrieval knobs."""
    if not path.exists():
        raise FileNotFoundError(f"Settings file does not exist: {path}")

    data = _read_yaml(path)
    retrieval_block = _read_dict(data, "retrieval")

    route_profiles: dict[str, RouteProfile] = {}
    raw_profiles = _read_dict(retrieval_block, "route_profiles", required=False)
    for route_name, route_data in raw_profiles.items():
        if not isinstance(route_data, dict):
            continue
        route_profiles[route_name] = RouteProfile(
            bm25_k=int(route_data["bm25_k"]),
            dense_k=int(route_data["dense_k"]),
            top_n_rerank=int(route_data["top_n_rerank"]),
        )

    retrieval = RetrievalSettings(
        bm25_k=int(retrieval_block["bm25_k"]),
        dense_k=int(retrieval_block["dense_k"]),
        rrf_k=int(retrieval_block["rrf_k"]),
        top_n_rerank=int(retrieval_block["top_n_rerank"]),
        final_k=int(retrieval_block["final_k"]),
        min_rrf_score=float(retrieval_block["min_rrf_score"]),
        max_context_chars=int(retrieval_block["max_context_chars"]),
        dedup_by=str(retrieval_block["dedup_by"]),
        route_profiles=route_profiles,
    )
    return FaultPilotSettings(retrieval=retrieval, raw=data)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load config/settings.yaml. Install pyyaml."
        ) from exc

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Settings root must be a dictionary")
    return payload


def _read_dict(
    payload: dict[str, Any],
    key: str,
    required: bool = True,
) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        if required:
            raise ValueError(f"Missing required object: {key}")
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected object for key: {key}")
    return value
