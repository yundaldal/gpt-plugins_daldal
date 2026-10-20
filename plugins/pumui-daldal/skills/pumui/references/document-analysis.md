# 한글 문서 분석·생성 라우팅

`scripts/document_adapter.py`는 HWPX와 TXT를 내장 방식으로 읽고 `status`, `format`, `engine`, `engine_version`, `source_revision`, `blocks`, `warnings` 구조로 정규화합니다.

레거시 HWP와 PDF를 분석하려면 사용자가 설치한 kordoc 호환 실행 파일을 `PUMUI_KORDOC` 환경 변수로 지정합니다. 어댑터는 `kordoc inspect <input-file> --json`을 호출하고 `blocks`의 각 항목에 `text` 문자열이 있는지 확인합니다. 플러그인은 엔진을 설치하거나 다운로드하지 않습니다.

생성은 `scripts/run_case.py`와 `scripts/build_hwpx.py`가 포함된 HWPX 바탕 양식을 사용합니다. 분석 결과는 질문 상태에서 필요한 값을 확인한 뒤 `validate_case.py`, `harness.py`, `hwpx_check.py`를 통과시켜야 산출물로 확정합니다.
