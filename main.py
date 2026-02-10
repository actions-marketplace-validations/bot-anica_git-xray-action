"""Git X-Ray GitHub Action — PR deployment risk analysis."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from base64 import b64decode
from datetime import datetime

# ---------------------------------------------------------------------------
# License validation (Ed25519 asymmetric — public key can only VERIFY)
# ---------------------------------------------------------------------------

# This public key can only verify signatures, not create them.
# The private key is held by the seller and never published.
_PUBLIC_KEY_B64 = "5znHa00Y0bHZMyYiep5JD553EwrqBhysHNnElcbyghU="


def _verify_license(key: str, repo_owner: str) -> dict:
    """Verify a license key using Ed25519 signature.

    License format: GXRAY-<base64(payload)>.<base64(signature)>
    Payload format: owner|plan|expiry_date
    """
    if not key:
        return {"valid": False, "plan": "none", "reason": "no key"}

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        if not key.startswith("GXRAY-"):
            return {"valid": False, "plan": "none", "reason": "invalid format"}

        raw = key[6:]
        parts = raw.split(".", 1)
        if len(parts) != 2:
            return {"valid": False, "plan": "none", "reason": "invalid format"}

        payload_b64, sig_b64 = parts
        payload_bytes = b64decode(payload_b64)
        sig_bytes = b64decode(sig_b64)
        payload = payload_bytes.decode()
        fields = payload.split("|")

        if len(fields) != 3:
            return {"valid": False, "plan": "none", "reason": "invalid payload"}

        owner, plan, expiry = fields

        # Verify Ed25519 signature using public key
        pub_key_bytes = b64decode(_PUBLIC_KEY_B64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)
        try:
            public_key.verify(sig_bytes, payload_bytes)
        except Exception:
            return {"valid": False, "plan": "none", "reason": "invalid signature"}

        # Check owner matches (or wildcard)
        if owner != "*" and owner.lower() != repo_owner.lower():
            return {"valid": False, "plan": plan, "reason": "owner mismatch"}

        # Check expiry
        if datetime.strptime(expiry, "%Y-%m-%d") < datetime.now():
            return {"valid": False, "plan": plan, "reason": "expired"}

        return {"valid": True, "plan": plan, "reason": "ok"}

    except ImportError:
        return {"valid": False, "plan": "none", "reason": "cryptography package not installed"}
    except Exception as e:
        return {"valid": False, "plan": "none", "reason": str(e)}


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _github_api(method: str, url: str, body: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "git-xray-action",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get_event() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return {}
    with open(path) as f:
        return json.load(f)


def _get_changed_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        capture_output=True, text=True,
    )
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def _post_or_update_comment(repo: str, pr_number: int, body: str) -> None:
    """Post a new comment or update an existing one (to avoid spam)."""
    marker = "<!-- git-xray-action -->"
    body_with_marker = f"{marker}\n{body}"

    # Check for existing comment
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    try:
        comments = _github_api("GET", url)
        for comment in comments:
            if marker in comment.get("body", ""):
                update_url = comment["url"]
                _github_api("PATCH", update_url, {"body": body_with_marker})
                return
    except Exception:
        pass

    # Post new comment
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    _github_api("POST", url, {"body": body_with_marker})


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _run_analysis(changed_files: list[str], top_n: int, full_analysis: bool):
    from git_xray.parser import parse_repo
    from git_xray.analysis import (
        analyze_bus_factor,
        analyze_coupling,
        analyze_hotspots,
    )

    commits = parse_repo(".")

    if len(commits) < 20:
        return None, "insufficient_history"

    changed_set = set(changed_files)

    # Hotspots: find which changed files are repo hotspots
    all_hotspots = analyze_hotspots(commits, top_n=100)
    hotspot_map = {h.path: h for h in all_hotspots}
    pr_hotspots = [hotspot_map[f] for f in changed_files if f in hotspot_map]
    pr_hotspots.sort(key=lambda h: h.risk_score, reverse=True)

    # Hotspot rank for context
    hotspot_ranks = {h.path: i + 1 for i, h in enumerate(all_hotspots)}

    result = {
        "hotspots": pr_hotspots[:top_n],
        "hotspot_ranks": hotspot_ranks,
        "total_repo_files": len(hotspot_map),
    }

    if full_analysis:
        # Bus factor: find files in PR where only 1-2 people have worked
        all_bus = analyze_bus_factor(commits, top_n=200, dir_depth=3)
        bus_warnings = []
        for entry in all_bus:
            if entry.risk in ("CRITICAL", "WARNING"):
                d = entry.directory
                for f in changed_files:
                    if f.startswith(d) or d == "(root)":
                        bus_warnings.append((f, entry))
                        break
        result["bus_factor"] = bus_warnings[:top_n]

        # Coupling: find files that usually change with PR files but aren't in this PR
        all_coupling = analyze_coupling(commits, top_n=200, min_coupling=0.5)
        missing_coupled = []
        for c in all_coupling:
            if c.file_a in changed_set and c.file_b not in changed_set:
                missing_coupled.append((c.file_b, c.file_a, c))
            elif c.file_b in changed_set and c.file_a not in changed_set:
                missing_coupled.append((c.file_a, c.file_b, c))
        result["missing_coupled"] = missing_coupled[:top_n]
    else:
        result["bus_factor"] = []
        result["missing_coupled"] = []

    return result, "ok"


# ---------------------------------------------------------------------------
# Risk score
# ---------------------------------------------------------------------------

def _calculate_risk(
    changed_files: list[str],
    result: dict,
    full_analysis: bool,
) -> tuple[int, str]:
    """Calculate risk score 0-100 and level."""
    score = 0.0

    # Large PRs are inherently riskier
    n_files = len(changed_files)
    if n_files > 50:
        score += 20
    elif n_files > 20:
        score += 12
    elif n_files > 10:
        score += 6

    # Hotspot files in PR
    for h in result.get("hotspots", []):
        rank = result["hotspot_ranks"].get(h.path, 999)
        if rank <= 5:
            score += 15  # top-5 hotspot
        elif rank <= 15:
            score += 8
        elif rank <= 30:
            score += 4

    if full_analysis:
        # Bus factor warnings
        score += len(result.get("bus_factor", [])) * 10

        # Missing coupled files
        score += len(result.get("missing_coupled", [])) * 12

    score = min(100, int(score))

    if score >= 70:
        level = "CRITICAL"
    elif score >= 45:
        level = "HIGH"
    elif score >= 20:
        level = "MODERATE"
    else:
        level = "LOW"

    return score, level


# ---------------------------------------------------------------------------
# Comment formatting
# ---------------------------------------------------------------------------

_LEVEL_ICONS = {
    "LOW": "\U0001f7e2",       # green circle
    "MODERATE": "\U0001f7e1",  # yellow circle
    "HIGH": "\U0001f7e0",      # orange circle
    "CRITICAL": "\U0001f534",  # red circle
}


def _bar(value: float, width: int = 8) -> str:
    filled = round(value * width)
    return "\u2593" * filled + "\u2591" * (width - filled)


def _format_comment(
    changed_files: list[str],
    result: dict,
    score: int,
    level: str,
    full_analysis: bool,
    is_private: bool,
) -> str:
    icon = _LEVEL_ICONS.get(level, "")
    lines = []

    lines.append(f"## {icon} Git X-Ray \u2014 PR Risk Analysis")
    lines.append("")

    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| **Risk Level** | {icon} **{level}** ({score}/100) |")
    lines.append(f"| **Files Changed** | {len(changed_files)} |")

    n_hotspots = len(result.get("hotspots", []))
    if n_hotspots > 0:
        lines.append(f"| **Hotspot Files** | {n_hotspots} |")

    n_bus = len(result.get("bus_factor", []))
    n_coupling = len(result.get("missing_coupled", []))
    warnings = n_bus + n_coupling
    if warnings > 0:
        lines.append(f"| **Warnings** | {warnings} |")

    lines.append("")

    # Hotspots section
    hotspots = result.get("hotspots", [])
    if hotspots:
        lines.append("### \U0001f525 Hotspot Files in This PR")
        lines.append("")
        lines.append(
            "These files change most frequently in the repo \u2014 "
            "statistically where bugs concentrate."
        )
        lines.append("")
        lines.append("| File | Repo Rank | Risk | Churn |")
        lines.append("|------|-----------|------|-------|")

        for h in hotspots:
            rank = result["hotspot_ranks"].get(h.path, "?")
            total = result["total_repo_files"]
            risk_bar = _bar(h.risk_score)
            churn = f"+{h.total_additions:,}/-{h.total_deletions:,}"
            lines.append(
                f"| `{h.path}` | #{rank} of {total} | {risk_bar} | {churn} |"
            )

        lines.append("")

    # Bus factor section
    bus_warnings = result.get("bus_factor", [])
    if bus_warnings:
        lines.append("### \u26a0\ufe0f Bus Factor Warnings")
        lines.append("")
        lines.append(
            "These areas have concentrated knowledge \u2014 "
            "if key contributors leave, the code becomes risky."
        )
        lines.append("")
        lines.append("| Area | Risk | Key Contributor |")
        lines.append("|------|------|-----------------|")

        seen_dirs = set()
        for f, entry in bus_warnings:
            if entry.directory in seen_dirs:
                continue
            seen_dirs.add(entry.directory)
            top = entry.top_contributors[0] if entry.top_contributors else ("?", 0, 0)
            name = top[0].split("@")[0] if "@" in top[0] else top[0]
            if len(name) > 20:
                name = name[:19] + "\u2026"
            pct = top[2]
            risk_label = f"\U0001f534 {entry.risk}" if entry.risk == "CRITICAL" else f"\U0001f7e1 {entry.risk}"
            lines.append(
                f"| `{entry.directory}` | {risk_label} | "
                f"**{name}** ({pct:.0f}% of commits) |"
            )

        lines.append("")

    # Missing coupled files section
    missing = result.get("missing_coupled", [])
    if missing:
        lines.append("### \U0001f517 Possibly Missing Files")
        lines.append("")
        lines.append(
            "These files usually change together with files in this PR "
            "but weren't included."
        )
        lines.append("")
        lines.append("| Missing File | Paired With | Coupling | Co-Commits |")
        lines.append("|-------------|-------------|----------|------------|")

        for missing_file, paired_with, c in missing:
            pct = f"{c.score * 100:.0f}%"
            lines.append(
                f"| `{missing_file}` | `{paired_with}` | {pct} | {c.co_commits} |"
            )

        lines.append("")

    # Upgrade CTA for private repos without license
    if is_private and not full_analysis:
        lines.append("### \U0001f513 Unlock Full Analysis")
        lines.append("")
        lines.append(
            "This is a **public-repo preview**. Private repos get full analysis including:"
        )
        lines.append("- \u26a0\ufe0f Bus factor warnings (knowledge concentration risk)")
        lines.append("- \U0001f517 Missing coupled files detection")
        lines.append("- \U0001f4c8 Historical risk tracking")
        lines.append("")
        lines.append(
            "**[Get a license key \u2192](https://github.com/bot-anica/git-xray-action#pricing)**"
        )
        lines.append("")

    # Footer
    if score == 0 and not hotspots and not bus_warnings and not missing:
        lines.append("No significant risks detected. Ship it! \U0001f680")
        lines.append("")

    lines.append("---")
    lines.append(
        '<sub>\U0001f4ca <a href="https://github.com/bot-anica/git-xray">Git X-Ray</a>'
        " \u2014 deployment risk analysis for every PR</sub>"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    event = _get_event()
    pr = event.get("pull_request")

    if not pr:
        print("Not a pull_request event. Skipping.")
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = pr["number"]
    base_ref = pr["base"]["ref"]
    is_private = event.get("repository", {}).get("private", False)
    repo_owner = repo.split("/")[0] if "/" in repo else ""

    print(f"Analyzing PR #{pr_number} on {repo} (base: {base_ref})")

    # License check
    license_key = os.environ.get("INPUT_LICENSE_KEY", "")
    if is_private and license_key:
        lic = _verify_license(license_key, repo_owner)
        full_analysis = lic["valid"]
        if not lic["valid"]:
            print(f"License: {lic['reason']} — running limited analysis")
        else:
            print(f"License: valid ({lic['plan']} plan)")
    elif is_private:
        full_analysis = False
        print("Private repo without license — running limited analysis")
    else:
        full_analysis = True
        print("Public repo — full analysis (free)")

    top_n = int(os.environ.get("INPUT_TOP", "5"))

    # Get changed files
    changed_files = _get_changed_files(base_ref)
    if not changed_files:
        print("No changed files detected. Skipping.")
        return

    print(f"Changed files: {len(changed_files)}")

    # Run analysis
    t0 = time.time()
    result, status = _run_analysis(changed_files, top_n, full_analysis)
    elapsed = time.time() - t0
    print(f"Analysis completed in {elapsed:.1f}s")

    if status == "insufficient_history":
        body = (
            "## \U0001f4ca Git X-Ray \u2014 PR Risk Analysis\n\n"
            "Not enough git history for meaningful analysis (minimum: 20 commits). "
            "Risk analysis will activate as the repository grows.\n\n"
            "---\n"
            '<sub><a href="https://github.com/bot-anica/git-xray">Git X-Ray</a></sub>'
        )
        _post_or_update_comment(repo, pr_number, body)
        return

    score, level = _calculate_risk(changed_files, result, full_analysis)
    print(f"Risk: {level} ({score}/100)")

    comment = _format_comment(changed_files, result, score, level, full_analysis, is_private)
    _post_or_update_comment(repo, pr_number, comment)
    print("Comment posted.")


if __name__ == "__main__":
    main()
