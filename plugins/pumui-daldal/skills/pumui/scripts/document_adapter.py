"""Safe local document inspection adapter used before case construction."""
import json
import os
import re
import shlex
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def _hwpx_blocks(path):
    blocks = []
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.startswith("Contents/") and name.endswith(".xml")]
        for name in names:
            root = ElementTree.fromstring(archive.read(name))
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1] == "t" and node.text:
                    text = re.sub(r"\s+", " ", node.text).strip()
                    if text:
                        blocks.append({"source": name, "text": text})
    return blocks


def _normalize_engine_result(data, path):
    return {
        "status": data.get("status", "ok"), "format": data.get("format", path.suffix.lstrip(".")),
        "engine": data.get("engine", "kordoc"), "engine_version": data.get("engine_version", "unknown"),
        "source_revision": data.get("source_revision"),
        "blocks": [b for b in data.get("blocks", []) if isinstance(b, dict) and isinstance(b.get("text"), str)],
        "warnings": [str(w) for w in data.get("warnings", [])],
    }


def _external_inspect(path):
    command = os.environ.get("PUMUI_KORDOC")
    if not command:
        return None
    args = shlex.split(command, posix=False) + ["inspect", str(path), "--json"]
    try:
        process = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False,
                                 shell=args[0].lower().endswith((".cmd", ".bat")))
        if process.returncode != 0:
            return {"status": "engine_failed", "format": path.suffix.lstrip("."), "engine": "kordoc", "engine_version": "unknown", "source_revision": None, "blocks": [], "warnings": ["문서 분석 엔진이 실패했습니다."]}
        return _normalize_engine_result(json.loads(process.stdout), path)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {"status": "engine_failed", "format": path.suffix.lstrip("."), "engine": "kordoc", "engine_version": "unknown", "source_revision": None, "blocks": [], "warnings": ["문서 분석 엔진 응답을 읽지 못했습니다."]}


def inspect(path):
    path = Path(path)
    suffix = path.suffix.lower()
    result = {"status": "ok", "format": suffix.lstrip("."), "engine": "builtin", "engine_version": "1", "source_revision": None, "blocks": [], "warnings": []}
    if suffix == ".hwpx":
        try:
            result["blocks"] = _hwpx_blocks(path)
        except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            result["status"] = "unreadable"
            result["warnings"].append("HWPX 컨테이너를 읽지 못했습니다.")
    elif suffix == ".txt":
        try:
            result["blocks"] = [{"source": path.name, "text": line.strip()} for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, UnicodeError):
            result["status"] = "unreadable"
            result["warnings"].append("텍스트 파일을 읽지 못했습니다.")
    elif suffix == ".pdf":
        result = _external_inspect(path) or result
        if result["engine"] == "builtin":
            result["status"] = "needs_engine"
            result["warnings"].append("PDF 추출 엔진이 필요합니다.")
    elif suffix == ".hwp":
        result = _external_inspect(path) or result
        if result["engine"] == "builtin":
            result["status"] = "needs_engine"
            result["warnings"].append("HWP 전용 엔진 또는 Windows COM이 필요합니다.")
    else:
        result["status"] = "unsupported"
        result["warnings"].append("지원하지 않는 문서 형식입니다.")
    return result
