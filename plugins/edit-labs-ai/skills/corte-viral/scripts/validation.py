from __future__ import annotations
import os

import json
import py_compile
from pathlib import Path
from typing import Any

from scripts.utils import HarnessError, PROJECT_ROOT, load_json

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ARTIFACT_SCHEMAS = {
    "00-manifest.json": "run-manifest.schema.json",
    "01-media.json": "media.schema.json",
    "02-transcript.json": "transcript.schema.json",
    "03-visual-index.json": "visual-index.schema.json",
    "04-context-map.json": "context-map.schema.json",
    "05-viral-moments.json": "viral-moments.schema.json",
    "06-candidates.json": "clip-candidates.schema.json",
    "07-feed-review.json": "feed-review.schema.json",
    "08-technical-audit.json": "technical-audit.schema.json",
    "09-blind-review.json": "blind-review.schema.json",
    "10-deduplication.json": "deduplication.schema.json",
    "11-edit-plans.json": "edit-plans.schema.json",
    "12-quality-review.json": "quality-review.schema.json",
    "13-final-clips.json": "final-clips.schema.json",
    "14-rejected-clips.json": "final-clips.schema.json",
    "16-output-verification.json": "output-verification.schema.json",
}

# Pareceres de revisores de LLM (feed-psychologist, revisor cego, quality-controller): o pacote
# não traz esses revisores (a revisão é humana); o arquivo é validado quando existe, nunca exigido.
OPTIONAL_ARTIFACTS = {"07-feed-review.json", "09-blind-review.json", "12-quality-review.json"}


def validate_json_data(data: Any, schema_name: str) -> list[str]:
    if jsonschema is None:
        raise HarnessError("jsonschema não está instalado")
    schema_path = PROJECT_ROOT / "schemas" / schema_name
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def validate_json_file(path: str | Path, schema_name: str) -> list[str]:
    return validate_json_data(load_json(path), schema_name)


def validate_run_artifacts(run_dir: str | Path) -> dict[str, Any]:
    run = Path(run_dir)
    manifest_path = run / "00-manifest.json"
    manifest = load_json(manifest_path, {})
    mode = str(manifest.get("mode", "full"))
    required = dict(ARTIFACT_SCHEMAS)
    # Analysis and verification runs are valid without rendered media. Full and
    # render modes must contain the deterministic post-render QC report.
    if mode not in {"full", "render"}:
        required.pop("16-output-verification.json", None)
    results = []
    for filename, schema in required.items():
        path = run / filename
        if not path.exists():
            if filename in OPTIONAL_ARTIFACTS:
                continue
            results.append({"file": filename, "exists": False, "valid": False, "errors": ["missing"]})
            continue
        errors = validate_json_file(path, schema)
        results.append({"file": filename, "exists": True, "valid": not errors, "errors": errors})
    return {"valid": all(item["valid"] for item in results), "mode": mode, "files": results}


def _frontmatter(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, ["frontmatter_must_start_on_first_line"]
    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None, ["frontmatter_closing_marker_missing"]
    if yaml is None:
        return None, ["pyyaml_missing"]
    try:
        data = yaml.safe_load("\n".join(lines[1:closing])) or {}
    except Exception as exc:  # pragma: no cover - message is user-facing
        return None, [f"frontmatter_yaml_invalid:{exc}"]
    if not isinstance(data, dict):
        return None, ["frontmatter_not_mapping"]
    return data, errors


def _validate_skill(path: Path) -> dict[str, Any]:
    data, errors = _frontmatter(path)
    data = data or {}
    if not data.get("description"):
        errors.append("description_missing")
    tools = data.get("allowed-tools", [])
    if isinstance(tools, str):
        tools_text = tools
    elif isinstance(tools, list):
        tools_text = " ".join(str(item) for item in tools)
    else:
        tools_text = ""
    if "Agent" not in tools_text:
        errors.append("agent_tool_not_preapproved")
    # no plugin `edit-labs-ai` o motor roda pelo comando `vch` do bin/ do plugin: `Bash(vch *)` também vale
    if "scripts/vch.py" not in tools_text and "Bash(vch " not in tools_text:
        errors.append("vch_command_not_preapproved")
    return {"path": str(path.relative_to(PROJECT_ROOT)), "valid": not errors, "errors": errors, "frontmatter": data}


def _tool_names(value: Any) -> set[str]:
    """Normalize a Claude Code subagent `tools` declaration for validation."""
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _validate_agents() -> list[dict[str, Any]]:
    results = []
    names: set[str] = set()
    for path in sorted((PROJECT_ROOT / "agentes").glob("*.md")):
        data, errors = _frontmatter(path)
        data = data or {}
        name = data.get("name")
        if not name:
            errors.append("name_missing")
        elif name in names:
            errors.append("duplicate_name")
        else:
            names.add(str(name))
        if not data.get("description"):
            errors.append("description_missing")

        tools = _tool_names(data.get("tools"))
        if not tools:
            errors.append("tools_missing_or_empty_can_prevent_agent_launch")

        # The blind reviewer must launch with at least one currently resolvable
        # tool, but must have no way to inspect local project state. Its packet
        # is passed inline by the orchestrator.
        if name == "blind-reviewer":
            forbidden_local = {
                "Read", "Grep", "Glob", "Bash", "Write", "Edit",
                "NotebookEdit", "Agent", "Task", "TaskCreate", "TaskGet",
                "TaskList", "TaskOutput", "TaskStop", "TaskUpdate", "TodoWrite",
            }
            forbidden = sorted(tools & forbidden_local)
            if forbidden:
                errors.append(f"blind_reviewer_has_forbidden_tools:{','.join(forbidden)}")
            if tools != {"WebSearch"}:
                errors.append("blind_reviewer_tools_must_equal_WebSearch")

        results.append({
            "path": str(path.relative_to(PROJECT_ROOT)),
            "name": name,
            "valid": not errors,
            "errors": errors,
            "tools": sorted(tools),
        })
    if not results:
        results.append({"path": "agentes", "valid": False, "errors": ["no_agents_found"]})
    return results


def _validate_yaml_files() -> list[dict[str, Any]]:
    results = []
    if yaml is None:
        return [{"path": "config", "valid": False, "errors": ["pyyaml_missing"]}]
    for path in sorted((PROJECT_ROOT / "config").rglob("*.yaml")):
        errors = []
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data is None:
                errors.append("empty_yaml")
        except Exception as exc:
            errors.append(str(exc))
        results.append({"path": str(path.relative_to(PROJECT_ROOT)), "valid": not errors, "errors": errors})
    return results


def _validate_python_files() -> list[dict[str, Any]]:
    results = []
    for path in sorted((PROJECT_ROOT / "scripts").glob("*.py")):
        errors = []
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(str(exc))
        results.append({"path": str(path.relative_to(PROJECT_ROOT)), "valid": not errors, "errors": errors})
    return results


# no plugin, os agentes moram na pasta agents/ do próprio plugin (o lançador exporta EDITLABS_AGENTS)
AGENTS_HOME = Path(os.environ["EDITLABS_AGENTS"]) if os.environ.get("EDITLABS_AGENTS") else Path.home() / ".claude" / "agents"


def _validate_installed_agents() -> dict[str, Any]:
    """
    Os subagentes so existem para o Claude Code quando estao em ~/.claude/agents/.
    A copia dentro da skill (agentes/) e a fonte; esta checagem garante que a
    instalacao foi feita e nao ficou defasada. Sem a instalacao, o Agent nao
    encontra os subagentes.
    """
    errors = []
    source = sorted((PROJECT_ROOT / "agentes").glob("*.md"))
    if not source:
        return {"valid": False, "errors": ["no_agents_in_package"], "installed": []}
    installed = []
    for path in source:
        target = AGENTS_HOME / path.name
        if not target.exists():
            errors.append(f"nao_instalado:{path.name}")
            continue
        if target.read_bytes() != path.read_bytes():
            errors.append(f"defasado:{path.name}")
        installed.append(path.name)
    return {"valid": not errors, "errors": errors, "installed": installed,
            "agents_home": str(AGENTS_HOME)}


def validate_project() -> dict[str, Any]:
    required = [
        "SKILL.md", "INSTALAR.md", "REGRAS.md", "verificar.py",
        "config/default.yaml", "requirements.txt",
        "scripts/vch.py", "scripts/output_qc.py", "scripts/render.py",
        "schemas/final-clips.schema.json", "schemas/output-verification.schema.json",
        "schemas/edit-plans.schema.json", "tests/smoke_test.sh",
        "docs/05-regras-de-selecao.md", "docs/06-regras-de-edicao.md",
        "models/face_detection_yunet_2023mar.onnx",
    ]
    files = []
    for relative in required:
        path = PROJECT_ROOT / relative
        files.append({"path": relative, "exists": path.exists()})

    schemas = []
    for path in sorted((PROJECT_ROOT / "schemas").glob("*.json")):
        errors = []
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            if jsonschema is not None:
                jsonschema.Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(str(exc))
        schemas.append({"path": path.name, "valid": not errors, "errors": errors})

    skills = [_validate_skill(PROJECT_ROOT / "SKILL.md")]
    agents = _validate_agents()
    installed_agents = _validate_installed_agents()
    yaml_files = _validate_yaml_files()
    python_files = _validate_python_files()
    expected_agents = {
        "context-mapper", "clip-hunter", "clip-builder", "clip-deduplicator", "edit-director",
    }
    actual_agents = {str(item.get("name")) for item in agents if item.get("name")}
    consistency_errors = []
    missing_agents = sorted(expected_agents - actual_agents)
    unexpected_agents = sorted(actual_agents - expected_agents)
    if missing_agents:
        consistency_errors.append(f"missing_agents:{','.join(missing_agents)}")
    if unexpected_agents:
        consistency_errors.append(f"unexpected_agents:{','.join(unexpected_agents)}")
    consistency = {"valid": not consistency_errors, "errors": consistency_errors}

    valid = (
        all(item["exists"] for item in files)
        and all(item["valid"] for item in schemas)
        and all(item["valid"] for item in skills)
        and all(item["valid"] for item in agents)
        and all(item["valid"] for item in yaml_files)
        and all(item["valid"] for item in python_files)
        and consistency["valid"]
        and installed_agents["valid"]
    )
    return {
        "valid": valid,
        "required_files": files,
        "schemas": schemas,
        "skills": skills,
        "agents": agents,
        "installed_agents": installed_agents,
        "yaml": yaml_files,
        "python": python_files,
        "consistency": consistency,
    }


