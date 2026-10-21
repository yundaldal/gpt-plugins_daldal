# 한글 문서 분석·생성 라우팅

`scripts/document_adapter.py`는 HWPX와 TXT를 내장 방식으로 읽고 `status`, `format`, `engine`, `engine_version`, `source_revision`, `blocks`, `warnings` 구조로 정규화합니다.

레거시 HWP와 PDF를 분석하려면 사용자가 설치한 kordoc 호환 실행 파일을 `PUMUI_KORDOC` 환경 변수로 지정합니다. 어댑터는 `kordoc <input-file> --format json`을 호출하고 `success: true`, 문자열 `markdown`, 배열 `blocks`, 객체 `metadata`를 확인합니다. text·table·image 등 구조화 block은 원형을 보존하며 metadata의 engine·engine_version은 제공되지 않으면 기본값을 사용합니다. 플러그인은 엔진을 설치하거나 다운로드하지 않습니다.

생성은 `scripts/run_case.py`와 `scripts/build_hwpx.py`가 포함된 HWPX 바탕 양식을 사용합니다. 분석 결과는 질문 상태에서 필요한 값을 확인한 뒤 `validate_case.py`, `harness.py`, `hwpx_check.py`를 통과시켜야 산출물로 확정합니다.

내장 HWPX 추출은 section XML의 텍스트 노드를 순서대로 제공하며 표의 셀 배치와 병합 구조를 보존하지 않습니다. 표 구조가 필요한 판독은 이미 설치되어 연결된 kordoc을 사용합니다. 구조가 잘못되었거나 본문 추출이 비어 있으면 읽기 성공으로 처리하지 않습니다.

Repeated confirmation instances use IDs such as `field.confirm::session[0]` and bind `index`, `field_path`, `value`, `source_id`, and `source_revision` in the context. `field_path` uses case JSON paths such as `draft.title` or `allowance.people[0].travel.amount`, with dots for properties and brackets for array indexes. The built-in HWPX block source records a section and text-node index; it does not preserve table layout.