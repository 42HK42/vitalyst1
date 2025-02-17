#!/usr/bin/env python3
"""Dependency update automation script for Vitalyst."""
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import tomli
import tomli_w
import yaml


class DependencyManager:
    """Manages project dependencies across backend and frontend."""

    def __init__(self):
        """Initialize the dependency manager."""
        self.project_root = Path(__file__).parent.parent.parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"

    def update_backend_dependencies(self) -> List[Tuple[str, str, str]]:
        """Update backend Python dependencies."""
        updates: List[Tuple[str, str, str]] = []

        # Get current dependencies
        req_file = self.backend_dir / "requirements.txt"
        current_deps = self._read_requirements(req_file)

        # Check for updates
        for pkg, version in current_deps.items():
            result = subprocess.run(
                ["pip", "index", "versions", pkg], capture_output=True, text=True
            )
            latest = result.stdout.strip().split("\n")[0].split()[-1]
            if latest != version:
                updates.append((pkg, version, latest))

        return updates

    def update_frontend_dependencies(self) -> Dict[str, List[Tuple[str, str, str]]]:
        """Update frontend npm dependencies."""
        updates: Dict[str, List[Tuple[str, str, str]]] = {
            "dependencies": [],
            "devDependencies": [],
        }

        # Get current dependencies
        pkg_file = self.frontend_dir / "package.json"
        with open(pkg_file) as f:
            pkg_data = json.load(f)

        # Check each dependency type
        for dep_type in ["dependencies", "devDependencies"]:
            current_deps = pkg_data.get(dep_type, {})
            for pkg, version in current_deps.items():
                result = subprocess.run(
                    ["npm", "view", pkg, "version"],
                    capture_output=True,
                    text=True,
                    cwd=self.frontend_dir,
                )
                latest = result.stdout.strip()
                current = version.lstrip("^~")
                if latest != current:
                    updates[dep_type].append((pkg, current, latest))

        return updates

    def check_security(self) -> Dict[str, List[str]]:
        """Run security checks on dependencies."""
        issues: Dict[str, List[str]] = {"backend": [], "frontend": []}

        # Backend security check
        result = subprocess.run(
            ["safety", "check"], capture_output=True, text=True, cwd=self.backend_dir
        )
        issues["backend"] = result.stdout.strip().split("\n")

        # Frontend security check
        result = subprocess.run(
            ["npm", "audit"], capture_output=True, text=True, cwd=self.frontend_dir
        )
        issues["frontend"] = result.stdout.strip().split("\n")

        return issues

    def generate_update_report(self) -> str:
        """Generate a report of available updates."""
        report = ["# Dependency Update Report\n"]

        # Backend updates
        report.append("## Backend Dependencies\n")
        backend_updates = self.update_backend_dependencies()
        if backend_updates:
            report.append("| Package | Current | Latest |\n")
            report.append("|---------|----------|--------|\n")
            for pkg, curr, latest in backend_updates:
                report.append(f"| {pkg} | {curr} | {latest} |\n")
        else:
            report.append("All backend dependencies are up to date.\n")

        # Frontend updates
        report.append("\n## Frontend Dependencies\n")
        frontend_updates = self.update_frontend_dependencies()
        for dep_type, updates in frontend_updates.items():
            report.append(f"\n### {dep_type}\n")
            if updates:
                report.append("| Package | Current | Latest |\n")
                report.append("|---------|----------|--------|\n")
                for pkg, curr, latest in updates:
                    report.append(f"| {pkg} | {curr} | {latest} |\n")
            else:
                report.append(f"All {dep_type} are up to date.\n")

        # Security issues
        report.append("\n## Security Issues\n")
        security_issues = self.check_security()
        for env, issues in security_issues.items():
            report.append(f"\n### {env.title()} Security\n")
            if issues and issues[0]:
                report.extend([f"- {issue}\n" for issue in issues])
            else:
                report.append("No security issues found.\n")

        return "".join(report)

    def _read_requirements(self, file_path: Path) -> Dict[str, str]:
        """Read requirements.txt and return package versions."""
        deps = {}
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg, version = line.split("==")
                    deps[pkg] = version
        return deps


if __name__ == "__main__":
    manager = DependencyManager()
    report = manager.generate_update_report()

    # Save report
    report_file = Path(__file__).parent / "dependency_report.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"Dependency report generated: {report_file}")
