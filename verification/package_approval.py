"""Build the text-only recovery runtime and source-identical approval ZIP."""
import base64
import hashlib
import io
import json
from pathlib import Path
import textwrap
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/approval-excel'
SKILL = PLUGIN / 'skills/instructions'


def archive(files):
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    return buffer.getvalue()


def runtime_text():
    files = {p.relative_to(SKILL).as_posix(): p.read_bytes()
             for folder in ('scripts', 'templates') for p in (SKILL / folder).iterdir()
             if p.is_file() and p.suffix in ('.py', '.xls', '.xlsx')}
    payload = archive(files)
    encoded = '\n'.join(textwrap.wrap(base64.b64encode(payload).decode('ascii'), 100))
    digest = hashlib.sha256(payload).hexdigest()
    return '''# 원본 포함 자체 복원 실행본

원본 첨부를 사용자에게 요청하지 않습니다. 스크립트나 바이너리 파일이 실행 환경에 보이지 않을 때 아래 Python 코드 전체를 코드 실행 도구에서 실행하세요. 일반적인 설치 환경은 build_upload.py를 직접 실행합니다.

이 문서는 verification/package_approval.py가 생성합니다. payload는 같은 배포의 원본 XLS/XLSX와 생성·검증 Python 소스입니다. 표준 라이브러리로 SHA-256을 확인하고 임시 폴더에 복원합니다. XLSX는 추가 의존성이 없습니다. 경기도 XLS만 xlrd, xlwt, xlutils가 필요하며 ImportError가 발생하면 실행 환경의 패키지 설치 기능으로 설치 후 재시도합니다. 복원 데이터나 스크립트를 임의로 수정하지 않습니다.

```python
import base64
import hashlib
import io
from pathlib import Path
import runpy
import tempfile
from zipfile import ZipFile

PAYLOAD = """
''' + encoded + '''
"""
PAYLOAD_SHA256 = "''' + digest + '''"


def generate_upload(confirmed_case, download_dir):
    payload = base64.b64decode(PAYLOAD)
    if hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
        raise ValueError("실행본이 잘렸거나 변경되었습니다. runtime.md 전체를 다시 읽으세요.")
    destination = Path(download_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="approval-runtime-") as temporary:
        root = Path(temporary).resolve()
        with ZipFile(io.BytesIO(payload)) as z:
            for entry in z.infolist():
                target = (root / entry.filename).resolve()
                if not target.is_relative_to(root):
                    raise ValueError("잘못된 실행본 경로")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(entry))
        module = runpy.run_path(str(root / "scripts/build_upload.py"))
        kind = module["region_kind"](confirmed_case["region"])
        suffix = ".xls" if kind == "gyeonggi" else ".xlsx"
        # Keep earlier downloads when the user requests a revision.
        output = destination / ("edufine-upload" + suffix)
        index = 2
        while output.exists():
            output = destination / ("edufine-upload-" + str(index) + suffix)
            index += 1
        result = module["build"](confirmed_case, output)
        if not result.is_file() or result.stat().st_size == 0:
            raise ValueError("검증된 파일이 없습니다.")
        return {"path": str(result), "verified": True,
                "item_count": len(confirmed_case["items"]),
                "guidance": module["GUIDANCE"]}
```

같은 Python 실행 세션에서 `generate_upload(confirmed_case, "/mnt/data")`를 호출합니다. `confirmed_case`는 upload-guide.md의 region/items 계약대로 현재 대화에서 확정한 입력 dict입니다. 예시 품목을 실제 자료 대신 넣지 않습니다. 다른 호스트에서는 실제 다운로드 가능한 폴더를 사용합니다.

반환값의 verified가 True이고 실제 파일이 존재할 때만 반환 path를 파일 다운로드 링크에 연결합니다. ChatGPT의 /mnt/data 파일은 `[에듀파인 업로드 엑셀 다운로드](sandbox:/mnt/data/실제파일명)`으로 제공합니다. 안내 문구는 엑셀 밖에 제공합니다. 코드 실행 도구가 없는 환경에서는 이 코드가 저절로 실행되거나 파일이 생성되지는 않습니다.
'''


def package_files():
    return {p.relative_to(PLUGIN).as_posix(): p.read_bytes()
            for p in PLUGIN.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def main():
    (SKILL / 'runtime.md').write_text(runtime_text(), encoding='utf-8', newline='\n')
    files = package_files()
    payload = archive(files)
    target = ROOT / 'downloads/approval-excel.zip'
    target.write_bytes(payload)
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(files)
        assert all(z.read(name) == data for name, data in files.items())
    digest = hashlib.sha256(payload).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest + '  approval-excel.zip\n', encoding='ascii')
    for path in (PLUGIN / 'plugin.json', PLUGIN / '.codex-plugin/plugin.json'):
        assert json.loads(path.read_text(encoding='utf-8'))['version'] == '0.14.4'
    print(f'Package verified: {len(files)} files, sha256={digest}')


if __name__ == '__main__':
    main()
