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

    def local_name(node):
        return node.tag.rsplit("}", 1)[-1]

    def ancestor(node, parents, name):
        while node is not None:
            if local_name(node) == name:
                return node
            node = parents.get(node)
        return None

    def sibling_index(node, parents, name):
        parent = parents.get(node)
        if parent is None:
            return 0
        siblings = [child for child in list(parent) if local_name(child) == name]
        return siblings.index(node) if node in siblings else 0

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "mimetype" not in names or "Contents/content.hpf" not in names:
            raise ValueError("invalid HWPX structure")
        if archive.read("mimetype").decode("ascii").strip() != "application/hwp+zip":
            raise ValueError("invalid HWPX mimetype")
        section_names = sorted(name for name in names if re.fullmatch(r"Contents/section[0-9]+\.xml", name))
        if not section_names:
            raise ValueError("HWPX has no section XML")
        ElementTree.fromstring(archive.read("Contents/content.hpf"))
        for name in section_names:
            root = ElementTree.fromstring(archive.read(name))
            if local_name(root) not in {"sec", "section"}:
                raise ValueError("invalid HWPX section XML")
            parents = {child: node for node in root.iter() for child in node}
            for index, node in enumerate(root.iter()):
                if local_name(node) == "t" and node.text:
                    text = re.sub(r"\s+", " ", node.text).strip()
                    if text:
                        paragraph = ancestor(node, parents, "p")
                        table = ancestor(node, parents, "tbl")
                        row = ancestor(node, parents, "tr")
                        cell = ancestor(node, parents, "tc")
                        if table is not None and row is not None and cell is not None:
                            location = (
                                f"table:{sibling_index(table, parents, 'tbl')}"
                                f"/row:{sibling_index(row, parents, 'tr')}"
                                f"/cell:{sibling_index(cell, parents, 'tc')}"
                            )
                            if paragraph is not None:
                                location += f"/paragraph:{sibling_index(paragraph, parents, 'p')}"
                        elif paragraph is not None:
                            location = f"paragraph:{sibling_index(paragraph, parents, 'p')}"
                        else:
                            location = f"text:{index}"
                        blocks.append({"source": f"{name}#{location}/node:{index}", "text": text})
    if not blocks:
        raise ValueError("empty HWPX content")
    return blocks


def _normalize_engine_result(data, path):
    if not isinstance(data, dict):
        raise ValueError("invalid kordoc response schema")
    metadata = data.get("metadata")
    blocks = data.get("blocks")
    if (data.get("success") is not True or not isinstance(data.get("markdown"), str)
            or not isinstance(blocks, list) or not isinstance(metadata, dict)):
        raise ValueError("invalid kordoc response schema")
    revision = metadata.get("source_revision")
    if revision is not None and not isinstance(revision, str):
        raise ValueError("kordoc source revision must be text or null")
    if metadata.get("engine") is not None and not isinstance(metadata["engine"], str):
        raise ValueError("kordoc engine metadata must be text")
    if metadata.get("engine_version") is not None and not isinstance(metadata["engine_version"], str):
        raise ValueError("kordoc engine version metadata must be text")
    for block in blocks:
        if not isinstance(block, dict) or ("type" in block and not isinstance(block["type"], str)):
            raise ValueError("kordoc returned an invalid block")
        if "text" in block and not isinstance(block["text"], str):
            raise ValueError("kordoc block text must be text")
        if block.get("type") in {"text", "paragraph"} and (not isinstance(block.get("text"), str) or not block["text"].strip()):
            raise ValueError("kordoc returned an empty text block")
    markdown = data["markdown"]
    has_usable_block = any(
        any(value.strip() if isinstance(value, str) else bool(value) for key, value in block.items() if key != "type")
        for block in blocks
    )
    if not markdown.strip() and not has_usable_block:
        raise ValueError("kordoc returned empty extraction")
    warnings = data.get("warnings", [])
    if not isinstance(warnings, list):
        raise ValueError("kordoc warnings must be an array")
    engine = metadata.get("engine") or "kordoc"
    engine_version = metadata.get("engine_version") or "unknown"
    return {
        "status": "ok", "format": data.get("format", path.suffix.lstrip(".")),
        "engine": engine, "engine_version": engine_version,
        "source_revision": revision,
        "blocks": blocks,
        "warnings": [str(w) for w in warnings],
    }


def _external_inspect(path):
    command = os.environ.get("PUMUI_KORDOC")
    if not command:
        return None
    args = shlex.split(command, posix=False) + [str(path), "--format", "json"]
    try:
        process = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False,
                                 shell=args[0].lower().endswith((".cmd", ".bat")))
        if process.returncode != 0:
            return {"status": "engine_failed", "format": path.suffix.lstrip("."), "engine": "kordoc", "engine_version": "unknown", "source_revision": None, "blocks": [], "warnings": ["문서 분석 엔진이 실패했습니다."]}
        return _normalize_engine_result(json.loads(process.stdout), path)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return {"status": "engine_failed", "format": path.suffix.lstrip("."), "engine": "kordoc", "engine_version": "unknown", "source_revision": None, "blocks": [], "warnings": ["문서 분석 엔진 응답을 읽지 못했습니다."]}


def inspect(path):
    path = Path(path)
    suffix = path.suffix.lower()
    result = {"status": "ok", "format": suffix.lstrip("."), "engine": "builtin", "engine_version": "1", "source_revision": None, "blocks": [], "warnings": []}
    if suffix == ".hwpx":
        try:
            result["blocks"] = _hwpx_blocks(path)
        except (OSError, RuntimeError, UnicodeError, zipfile.BadZipFile, ElementTree.ParseError, ValueError):
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
