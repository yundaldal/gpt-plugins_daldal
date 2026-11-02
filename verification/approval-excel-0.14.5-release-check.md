# approval-excel 0.14.5 — ChatGPT 실행 도구 호출 지침

## 확인된 실패 원인

0.14.4에는 실제 Excel 생성기, 지역별 원본 양식, 복구용 실행본이 이미 들어 있었지만, 지침은 코드 실행 기능의 필요성을 설명하는 데 그쳤습니다. ChatGPT 대화에서 Python 도구를 실제 호출하고 `generate_upload`를 실행하라는 명시적 단계가 없어, 모델이 파일 생성 없이 한계를 설명하고 끝낼 수 있었습니다. 사용자가 받은 응답도 원본 양식이 없어서가 아니라 생성·검증 경로가 실행되지 않은 상황과 일치합니다.

## 변경 내용 및 마일스톤

| 단계 | 완료 기준 및 증거 |
| --- | --- |
| M1 범위·원본 | 기존 경기·경기 외 원본 양식과 생성·검증 로직을 유지. 품의문 작성 및 확인 프로세스는 수정하지 않음. |
| M2 실행 경로 | SKILL.md와 upload-guide.md가 ChatGPT Python/Code Interpreter를 직접 호출하고 runtime.md 전체 코드 실행 후 `generate_upload(확정값, "/mnt/data")`를 실행하도록 지정. 플러그인에서 원본을 읽지 못하면 배포에 포함된 복구 실행본 사용. |
| M3 검증 | 기존 approval-excel 생성·전달 하네스를 실행해 두 양식 파일의 생성, 재열기, 검증 및 복구 payload를 확인. |
| M4 배포 | 두 매니페스트와 패키지 검사 기대 버전을 0.14.5로 일치. 재생성한 ZIP의 파일 목록·내용·SHA-256 sidecar 확인 후 GitHub main 반영 상태를 확인. |

## 변경 파일

- `plugins/approval-excel/skills/instructions/SKILL.md`
- `plugins/approval-excel/skills/instructions/upload-guide.md`
- `plugins/approval-excel/skills/instructions/runtime.md` (배포 스크립트가 재생성)
- `plugins/approval-excel/README.md`
- 두 `plugin.json` 매니페스트
- `verification/package_approval.py`, `verification/test_approval_delivery.py`
- 생성 패키지 `downloads/approval-excel.zip` 및 SHA-256 파일

## 검증 범위와 한계

로컬 하네스와 패키지 검사는 생성 코드, 두 원본 양식, ZIP 배포를 검증합니다. 이 검사는 사용자의 ChatGPT 화면에서 도구가 활성화되어 있는지, 최신 플러그인 지침이 실제 대화에 반영되었는지 또는 다운로드 첨부가 표시되는지를 대신 확인하지 않습니다. Skills 전용 플러그인은 호스트에서 Python/Code Interpreter를 켤 수 없으므로, 해당 도구가 제공되지 않는 대화에서는 실제 파일 첨부 생성을 보장할 수 없습니다.
