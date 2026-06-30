"""File agent — directory scanning, organization, and duplicate detection."""

from __future__ import annotations

import hashlib
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from shadowforge.core.base_agent import BaseAgent
from shadowforge.core.message_bus import MessageBus


class FileAgent(BaseAgent):
    """Handles file system operations: scan, organize, deduplicate, cleanup."""

    def __init__(
        self,
        message_bus: MessageBus,
        organize_categories: Optional[dict[str, list[str]]] = None,
        name: str = "file",
    ) -> None:
        super().__init__(
            name=name,
            message_bus=message_bus,
            capabilities=[
                "scan_directory",
                "analyze_summary",
                "find_duplicates",
                "organize_by_type",
                "cleanup_empty_dirs",
                "move_file",
                "delete_file",
            ],
        )
        self.organize_categories = organize_categories or {
            "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
            "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".xlsx"],
            "videos": [".mp4", ".avi", ".mkv", ".mov"],
            "audio": [".mp3", ".wav", ".flac", ".ogg"],
            "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp"],
        }
        self._last_scan: dict[str, Any] = {}

    def process(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")
        params = task.get("params", {})

        handlers = {
            "scan_directory": self._scan_directory,
            "analyze_summary": self._analyze_summary,
            "find_duplicates": self._find_duplicates,
            "organize_by_type": self._organize_by_type,
            "cleanup_empty_dirs": self._cleanup_empty_dirs,
            "move_file": self._move_file,
            "delete_file": self._delete_file,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")

        return handler(params)

    def _resolve_path(self, path_str: str) -> Path:
        return Path(os.path.expanduser(path_str)).resolve()

    def _scan_directory(self, params: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(params.get("path", "~/Desktop"))
        max_depth = params.get("depth", 3)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        files: list[dict[str, Any]] = []
        total_size = 0

        for root, dirs, filenames in os.walk(path):
            depth = len(Path(root).relative_to(path).parts)
            if depth >= max_depth:
                dirs.clear()
                continue

            for filename in filenames:
                filepath = Path(root) / filename
                try:
                    stat = filepath.stat()
                    files.append({
                        "path": str(filepath),
                        "name": filename,
                        "size": stat.st_size,
                        "extension": filepath.suffix.lower(),
                        "modified": stat.st_mtime,
                    })
                    total_size += stat.st_size
                except OSError:
                    continue

        ext_counts: dict[str, int] = defaultdict(int)
        for f in files:
            ext_counts[f["extension"]] += 1

        self._last_scan = {"path": str(path), "files": files}
        self.logger.info("Scanned %s: %d files", path, len(files))

        return {
            "success": True,
            "path": str(path),
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "extension_breakdown": dict(ext_counts),
            "files": files[:100],
        }

    def _categorize(self, extension: str) -> str:
        for cat, extensions in self.organize_categories.items():
            if extension in extensions:
                return cat
        return "other"

    def _analyze_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        """Full analysis report for the last scanned directory."""
        if not self._last_scan.get("files") and params.get("path"):
            self._scan_directory({"path": params["path"], "depth": params.get("depth", 5)})

        files = self._last_scan.get("files", [])
        if not files:
            raise RuntimeError("No scan data. Run scan_directory first or provide a valid path.")

        categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ext_counts: dict[str, int] = defaultdict(int)
        for file_info in files:
            ext = file_info["extension"] or "(no ext)"
            ext_counts[ext] += 1
            categories[self._categorize(file_info["extension"])].append(file_info)

        largest = sorted(files, key=lambda f: f["size"], reverse=True)[:10]
        total_size = sum(f["size"] for f in files)

        report = {
            "success": True,
            "scanned_path": self._last_scan.get("path"),
            "total_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "unique_extensions": len(ext_counts),
            "extension_breakdown": dict(sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "category_breakdown": {cat: len(items) for cat, items in categories.items()},
            "largest_files": [
                {"name": f["name"], "size_mb": round(f["size"] / (1024 * 1024), 2), "path": f["path"]}
                for f in largest
            ],
            "category_details": {
                cat: [f["name"] for f in items[:5]]
                for cat, items in categories.items() if items
            },
        }
        self.logger.info(
            "Analysis: %d files, %.1f MB, %d categories",
            report["total_files"], report["total_size_mb"], len(report["category_breakdown"]),
        )
        return report

    def _file_hash(self, filepath: Path, algorithm: str = "md5") -> str:
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _find_duplicates(self, params: dict[str, Any]) -> dict[str, Any]:
        files = self._last_scan.get("files", [])
        if not files and "path" in params:
            self._scan_directory({"path": params["path"]})
            files = self._last_scan.get("files", [])

        hash_map: dict[str, list[str]] = defaultdict(list)
        for file_info in files:
            filepath = Path(file_info["path"])
            if filepath.exists() and filepath.is_file():
                try:
                    file_hash = self._file_hash(filepath)
                    hash_map[file_hash].append(str(filepath))
                except OSError:
                    continue

        duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
        duplicate_count = sum(len(paths) - 1 for paths in duplicates.values())

        self.logger.info("Found %d duplicate groups", len(duplicates))
        return {
            "success": True,
            "duplicate_groups": len(duplicates),
            "duplicate_files": duplicate_count,
            "groups": [
                {"hash": h, "files": paths, "count": len(paths)}
                for h, paths in list(duplicates.items())[:20]
            ],
        }

    def _organize_by_type(self, params: dict[str, Any]) -> dict[str, Any]:
        base_path_str = params.get("path", self._last_scan.get("path", "~/Desktop"))
        base_path = self._resolve_path(base_path_str)
        dry_run = params.get("dry_run", True)

        if not self._last_scan.get("files"):
            self._scan_directory({"path": str(base_path)})

        moved: list[dict[str, str]] = []
        for file_info in self._last_scan.get("files", []):
            ext = file_info["extension"]
            category = "other"
            for cat, extensions in self.organize_categories.items():
                if ext in extensions:
                    category = cat
                    break

            if category == "other":
                continue

            src = Path(file_info["path"])
            dest_dir = base_path / f"_organized" / category
            dest = dest_dir / src.name

            if src.parent == dest_dir:
                continue

            entry = {"from": str(src), "to": str(dest), "category": category}
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.move(str(src), str(dest))
                    entry["moved"] = True
                else:
                    entry["moved"] = False
                    entry["reason"] = "destination exists"
            else:
                entry["moved"] = False
                entry["reason"] = "dry_run"

            moved.append(entry)

        self.logger.info("Organize plan: %d files (%s)", len(moved), "dry_run" if dry_run else "executed")
        return {
            "success": True,
            "dry_run": dry_run,
            "files_to_organize": len(moved),
            "plan": moved[:50],
        }

    def _cleanup_empty_dirs(self, params: dict[str, Any]) -> dict[str, Any]:
        base_path = self._resolve_path(params.get("path", self._last_scan.get("path", "~/Desktop")))
        dry_run = params.get("dry_run", True)
        removed: list[str] = []

        for root, dirs, _ in os.walk(base_path, topdown=False):
            for dirname in dirs:
                dirpath = Path(root) / dirname
                try:
                    if not any(dirpath.iterdir()):
                        removed.append(str(dirpath))
                        if not dry_run:
                            dirpath.rmdir()
                except OSError:
                    continue

        return {
            "success": True,
            "dry_run": dry_run,
            "empty_dirs_found": len(removed),
            "directories": removed[:30],
        }

    def _move_file(self, params: dict[str, Any]) -> dict[str, Any]:
        src = self._resolve_path(params["source"])
        dest = self._resolve_path(params["destination"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return {"success": True, "from": str(src), "to": str(dest)}

    def _delete_file(self, params: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(params["path"])
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return {"success": True, "deleted": str(path)}