"""Helpers for the Open Knowledge Format (OKF) layer.

OKF (Google, 2026) formalizes Karpathy's "LLM wiki" pattern: a directory of
markdown documents, each representing one *concept*, with a YAML frontmatter
header (structured, queryable) and a markdown body (human- and agent-readable).
Concepts cross-link with ordinary markdown links, forming a knowledge graph.

The only required frontmatter field is ``type``. We use:
    Paper | Concept | Dataset | Schema | Index

Reserved filenames: ``index.md`` (catalog) and ``log.md`` (chronological history).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


def slugify(text: str) -> str:
    """Filesystem-safe, link-stable slug. ``Phoenix, Arizona`` -> ``phoenix-arizona``."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-") or "untitled"


def humanize(key: str) -> str:
    """Turn a schema category key into a display label.

    ``cardiovascular_conditions`` -> ``Cardiovascular conditions``;
    a few domain acronyms/terms are special-cased.
    """
    special = {
        "ground_level_ozone_air_pollution": "Ground-level ozone & air pollution",
        "ground_level_ozone": "Ground-level ozone",
        "vectors_vector_habitat": "Vectors & vector habitat",
        "vector_borne_diseases": "Vector-borne diseases",
        "aridity_mitigation_water_management": "Aridity mitigation & water management",
        "closed_systems_systems_thinking": "Closed systems / systems thinking",
        "immune_system_impacts_inflammation": "Immune-system impacts & inflammation",
        "compounding_environmental_exposures": "Compounding environmental exposures",
        "extreme_precipitation_flooding": "Extreme precipitation & flooding",
        "extreme_seasonal_weather_fluctuations": "Extreme seasonal weather fluctuations",
        "pregnancy_fetal_development_birth": "Pregnancy, fetal development & birth",
        "leaching_chemicals_heavy_metals": "Leaching chemicals & heavy metals",
        "behaviour_violence": "Behaviour & violence",
        "policy_and_law": "Policy & law",
        "drought_aridification": "Drought & aridification",
        "wind_dust": "Wind & dust",
        "fire_smoke": "Fire & smoke",
    }
    if key in special:
        return special[key]
    return key.replace("_", " ").capitalize()


def _yaml_safe(value: Any) -> Any:
    """Coerce values to YAML-friendly primitives (dates -> ISO strings)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _yaml_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_yaml_safe(v) for v in value]
    return value


def dump_frontmatter(meta: dict[str, Any]) -> str:
    """Render a YAML frontmatter block (``type`` first, then sorted keys)."""
    meta = {k: _yaml_safe(v) for k, v in meta.items() if v is not None}
    ordered = {}
    if "type" in meta:
        ordered["type"] = meta.pop("type")
    for key in sorted(meta):
        ordered[key] = meta[key]
    body = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{body}---\n"


def render(meta: dict[str, Any], body: str) -> str:
    """Compose a full OKF document string from frontmatter + markdown body."""
    return dump_frontmatter(meta) + "\n" + body.rstrip() + "\n"


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split an OKF document into (frontmatter dict, markdown body)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].lstrip("\n")
    return {}, text


def write_doc(path: Path, meta: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(meta, body), encoding="utf-8")


def read_doc(path: Path) -> tuple[dict[str, Any], str]:
    return parse(Path(path).read_text(encoding="utf-8"))


def link(label: str, target: Path | str, from_dir: Path | None = None) -> str:
    """Build a markdown link. If ``from_dir`` is given, target is made relative to it."""
    target = Path(target)
    if from_dir is not None:
        try:
            target = Path(__import__("os").path.relpath(target, from_dir))
        except ValueError:
            pass
    return f"[{label}]({target.as_posix()})"
