"""Repository checks that `claude plugin validate` does not make.

    python scripts/validate.py      print findings; exit 1 on any error or warning

Checks: the manifests agree with each other and with pyproject.toml; every
skill is self-sufficient (its paths exist inside its folder, it carries the
engine and the generated rules, and they are current); every engine command a
skill teaches exists with the options it uses; no skill writes the learner's
files around the engine or commits without the learner's yes; the plugin
holds only accepted file types; translated documents link to each other; the
session test files are well formed; and no committed file holds a secret,
a personal address, a user's home path or a learner's folder.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SKILLS = PLUGIN / "skills"
sys.path.insert(0, str(REPO / "src"))
sys.dont_write_bytecode = True

from vocabbot import cli  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")
PLUGIN_TYPES = {".md", ".json", ".png", ".pyz", ""}
TRANSLATED = [
    "README.md",
    "QUICKSTART.md",
    "docs/pilot.md",
    "docs/development-plan.md",
    "plugin/README.md",
    "plugin/PRIVACY.md",
]
SECRETS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "an Anthropic API key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), "a GitHub token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "an AWS key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ALLOWED_EMAIL = re.compile(r"noreply@anthropic\.com|@example\.(?:com|org)$|^git@github\.com$")
HOME_PATH = re.compile(r"(?i)(?:[A-Z]:\\Users\\|/Users/|/home/)(?!runner\b|<|\{|\$)[A-Za-z0-9._-]+")
TEXT_TYPES = {".md", ".json", ".jsonl", ".py", ".toml", ".yml", ".yaml", ".txt", ".tsv", ""}
DIRECT_WRITE = re.compile(
    r"(?:>>?\s*\S*(?:registers|log|courses)/)"
    r"|(?:\b(?:Write|Edit)\b[^\n]*\b(?:plan\.json|reviews\.jsonl|own\.jsonl|decisions\.md|flags\.jsonl)\b)"
)

errors: list[str] = []
warnings: list[str] = []


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{rel(path)}: unreadable ({exc})")
        return {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- manifests


def semver_of(pep440: str) -> str:
    """1.0.0rc1 -> 1.0.0-rc.1, 1.0.0 -> 1.0.0, 1.0.0.dev2 -> 1.0.0-dev.2."""
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:\.?(a|b|rc|dev)\.?(\d+))?", pep440)
    if not match:
        return ""
    base, kind, number = match.groups()
    if not kind:
        return base
    label = {"a": "alpha", "b": "beta"}.get(kind, kind)
    return f"{base}-{label}.{number}"


def check_manifests() -> str:
    claude = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    portable = load_json(PLUGIN / "plugin.json")
    market = load_json(REPO / ".claude-plugin" / "marketplace.json")
    codex = load_json(REPO / ".agents" / "plugins" / "marketplace.json")
    version = str(claude.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        errors.append("plugin/.claude-plugin/plugin.json: version must be semver")
    for key in ("name", "version", "description", "license", "homepage", "repository"):
        if portable.get(key) != claude.get(key):
            errors.append(f"plugin/plugin.json: '{key}' differs from .claude-plugin/plugin.json")
    if not str(portable.get("$schema", "")).startswith("https://agent-plugins.org/schemas/"):
        errors.append("plugin/plugin.json: '$schema' must name the Agent Plugins schema")
    openai = (portable.get("extensions") or {}).get("com.openai") or {}
    onboarding = openai.get("onboardingSkill", "")
    if not onboarding or not (PLUGIN / onboarding).is_file():
        errors.append(f"plugin/plugin.json: onboardingSkill {onboarding!r} does not exist")
    shown = openai.get("interface") or {}
    for key in ("displayName", "shortDescription", "category", "privacyPolicyURL"):
        if not shown.get(key):
            errors.append(f"plugin/plugin.json: extensions.com.openai.interface.{key} is missing")
    name = claude.get("name")
    entry = next((p for p in market.get("plugins", []) if p.get("name") == name), None)
    if entry is None or (REPO / str(entry.get("source", ""))).resolve() != PLUGIN.resolve():
        errors.append(".claude-plugin/marketplace.json: no entry for the plugin in ./plugin")
    if codex.get("name") != market.get("name"):
        errors.append(".agents/plugins/marketplace.json: name differs from the Claude catalog")
    entry = next((p for p in codex.get("plugins", []) if p.get("name") == name), None)
    source = (entry or {}).get("source") or {}
    if not entry or (REPO / str(source.get("path", ""))).resolve() != PLUGIN.resolve():
        errors.append(".agents/plugins/marketplace.json: no entry for the plugin in ./plugin")
    elif not (entry.get("policy") or {}).get("installation") or not entry.get("category"):
        errors.append(".agents/plugins/marketplace.json: policy.installation and category needed")
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    found = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    package = found.group(1) if found else ""
    if semver_of(package) != version:
        errors.append(f"pyproject.toml version {package} does not match the plugin's {version}")
    init = (REPO / "src" / "vocabbot" / "__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{package}"' not in init:
        errors.append("src/vocabbot/__init__.py: __version__ differs from pyproject.toml")
    changelog = REPO / "CHANGELOG.md"
    if not changelog.is_file() or f"## {version}" not in changelog.read_text(encoding="utf-8"):
        errors.append(f"CHANGELOG.md has no section '## {version}'")
    return version


# ---------------------------------------------------------------- skills


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        found = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if found:
            key = found.group(1)
            value = found.group(2).strip()
            fields[key] = "" if value in (">", "|", ">-", "|-") else value.strip('"')
        elif key and line.startswith(" "):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, match.group(2)


def commands() -> dict[str, argparse.ArgumentParser]:
    """Every engine command (and subcommand) with its parser."""
    parser = cli.build_parser()
    out: dict[str, argparse.ArgumentParser] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                out[name] = sub
                for inner in sub._actions:
                    if isinstance(inner, argparse._SubParsersAction):
                        for sub_name, sub_sub in inner.choices.items():
                            out[f"{name} {sub_name}"] = sub_sub
    return out


def taught_calls(text: str) -> list[str]:
    """Engine calls a skill text shows: code spans and lines of code blocks with --json."""
    spans: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
        elif inside:
            spans.append(line)
        else:
            spans += re.findall(r"`([^`\n]+)`", line)
    calls = []
    for span in spans:
        span = span.strip()
        if "--json" not in span:
            continue
        span = re.sub(r'^.*?vocabbot\.pyz"?\s+', "", span)
        span = span.split("<<")[0].strip()
        if re.match(r"^[a-z]+(?:\s|$)", span):
            calls.append(span)
    return calls


def check_call(call: str, known: dict[str, argparse.ArgumentParser], where: str) -> None:
    words = shlex.split(call.replace("<", "").replace(">", "").replace("|", " "))
    if not words:
        return
    name = " ".join(words[:2]) if " ".join(words[:2]) in known else words[0]
    parser = known.get(name)
    if parser is None:
        errors.append(f"{where}: `{call}` names no engine command")
        return
    options = set(parser._option_string_actions)
    for word in words:
        if word.startswith("--") and word.split("=")[0] not in options:
            errors.append(f"{where}: `{call}` uses {word}, which `{name}` does not take")


def check_skills() -> None:
    known = commands()
    for skill in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        skill_md = skill / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{rel(skill)}: no SKILL.md")
            continue
        fields, body = frontmatter(skill_md)
        name, description = fields.get("name", ""), fields.get("description", "")
        if name != skill.name:
            errors.append(f"{rel(skill_md)}: name '{name}' must match the folder")
        if not NAME_RE.match(name) or len(name) > 64 or any(r in name for r in RESERVED):
            errors.append(f"{rel(skill_md)}: invalid skill name '{name}'")
        if not description or len(description) > 1024:
            errors.append(f"{rel(skill_md)}: description empty or over 1024 characters")
        if re.search(r"<[A-Za-z/][^>]*>", description):
            errors.append(f"{rel(skill_md)}: description holds an XML-like tag")
        if skill_md.read_text(encoding="utf-8").count("\n") >= 500:
            errors.append(f"{rel(skill_md)}: 500 lines or more; move detail to reference/")
        for needed in ("reference/gotchas.md", "shared/rules.md", "shared/labels.md"):
            if not (skill / needed).is_file():
                errors.append(f"{rel(skill)}: missing {needed}")
        if "shared/rules.md" not in body or "${CLAUDE_SKILL_DIR}/bin/vocabbot.pyz" not in body:
            errors.append(f"{rel(skill_md)}: must point to shared/rules.md and bin/vocabbot.pyz")
        for md in sorted(skill.rglob("*.md")):
            text = md.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#\s]+)\)", text):
                if re.match(r"^[a-z]+://", target):
                    continue
                resolved = (md.parent / target).resolve()
                if skill.resolve() not in resolved.parents or not resolved.exists():
                    errors.append(f"{rel(md)}: link {target} is not a file of the skill")
            for path in re.findall(r"`((?:shared|reference|bin)/[A-Za-z0-9_./-]+)`", text):
                if not (skill / path).exists():
                    errors.append(f"{rel(md)}: names `{path}`, which the skill does not have")
            if "../" in text or "${CLAUDE_PLUGIN_ROOT}" in text:
                errors.append(f"{rel(md)}: refers outside the skill folder")
            for call in taught_calls(text):
                check_call(call, known, rel(md))
            lines = text.splitlines()
            for number, line in enumerate(lines, 1):
                if DIRECT_WRITE.search(line):
                    errors.append(f"{rel(md)}:{number}: writes a learner's file around the engine")
                if "commit --confirm" in line:
                    window = " ".join(lines[max(0, number - 4) : number]).lower()
                    if "yes" not in window:
                        errors.append(f"{rel(md)}:{number}: commit without the learner's yes")
                if re.search(r"--today\b", line):
                    errors.append(f"{rel(md)}:{number}: a skill never sets the learning day")


def check_generated() -> None:
    done = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "build.py"), "skills", "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if done.returncode:
        try:
            stale = json.loads(done.stdout)["stale"]
        except (ValueError, KeyError):
            stale = [done.stderr.strip()[-300:]]
        errors.append(
            "generated files are stale; run python scripts/build.py skills: " + ", ".join(stale)
        )


def check_plugin_files() -> None:
    files = [p for p in PLUGIN.rglob("*") if p.is_file()]
    for path in files:
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            errors.append(f"{rel(path)}: cache file in the plugin")
        elif path.suffix.lower() not in PLUGIN_TYPES:
            errors.append(f"{rel(path)}: file type {path.suffix} does not belong in the plugin")
    readme = PLUGIN / "README.md"
    if not readme.is_file() or len(readme.read_text(encoding="utf-8").split()) < 40:
        errors.append("plugin/README.md missing or under 40 words")
    print(f"plugin files: {len(files)}")


def check_translations() -> None:
    for doc in TRANSLATED:
        english = REPO / doc
        polish = english.with_name(english.stem + ".pl.md")
        if not english.is_file() or not polish.is_file():
            errors.append(f"{doc}: the English file and its .pl.md translation are both needed")
            continue
        if f"]({polish.name})" not in english.read_text(encoding="utf-8")[:400]:
            errors.append(f"{doc}: its first lines must link to {polish.name}")
        if f"]({english.name})" not in polish.read_text(encoding="utf-8")[:400]:
            errors.append(f"{rel(polish)}: its first lines must link to {english.name}")


def check_sessions() -> None:
    done = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "session_test.py"), "--lint"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if done.returncode:
        errors.append("session files: " + (done.stdout + done.stderr).strip()[-500:])


# ---------------------------------------------------------------- committed files


def committed_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [REPO / line for line in out.splitlines() if line and (REPO / line).is_file()]


def check_committed() -> None:
    for path in committed_files():
        relative = rel(path)
        if path.name in ("plan.json", "reviews.jsonl") and not relative.startswith("tests/"):
            errors.append(f"{relative}: a learner's folder never enters the repository")
        if path.suffix.lower() not in TEXT_TYPES or path.stat().st_size > 3_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in SECRETS:
            if pattern.search(text):
                errors.append(f"{relative}: holds what looks like {label}")
        for address in set(EMAIL.findall(text)):
            if not ALLOWED_EMAIL.search(address):
                errors.append(f"{relative}: holds the e-mail address {address}")
        for home in set(HOME_PATH.findall(text)):
            errors.append(f"{relative}: holds the home path {home}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    version = check_manifests()
    check_skills()
    check_generated()
    check_plugin_files()
    check_translations()
    check_sessions()
    check_committed()
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"version {version}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors or warnings else 0


if __name__ == "__main__":
    sys.exit(main())
