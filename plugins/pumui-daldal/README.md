# 품의 기안 도우미

한국 교육기관의 지출품의 초안과 계산 산출물을 준비하는 skills-only 플러그인입니다. A1~A4 수당, B1~B2 물품 구입, C1~C3 경비 흐름을 지원합니다.

포함된 단가표는 2026년 참고 프로필입니다. 기관·회계연도에 적용되는지 사용자가 확인하기 전에는 수당 계산을 진행하지 마세요. 생성 문서는 검토용 초안이며, 회계 분류·규정·결재 요건의 최종 판단을 대신하지 않습니다.

## ChatGPT 설치 및 배포

이 저장소의 `pumui-daldal-0.1.0.zip`은 portable plugin ZIP입니다. 일반 Custom GPT 편집기의 Knowledge에 ZIP을 올리는 방식과 다릅니다. GPT Knowledge 업로드는 참고 파일을 GPT에 제공하는 기능으로, 플러그인을 설치하거나 ZIP 안의 Python 스크립트를 실행하지 않습니다.

ChatGPT 플러그인 설치 옵션은 계정, 요금제, 지역, workspace 권한과 사용 중인 화면에 따라 달라집니다. 아래에서 현재 계정에 표시되는 경로를 사용하세요.

### 개인 계정에서 ZIP 가져오기가 제공되는 경우

ChatGPT 웹에서 `@plugin-creator`와 ZIP 가져오기 기능을 사용할 수 있을 때 다음과 같이 요청하세요.

1. 새 대화에서 `pumui-daldal-0.1.0.zip`을 첨부합니다.
2. `@plugin-creator 첨부한 ZIP을 가져와 외부 앱 연결 없이 스킬만 포함하는 비공개 플러그인으로 설치해 주세요.`라고 요청합니다.
3. 설치된 플러그인을 새 대화에서 선택해 기본 동작을 확인합니다.

개인 계정에서 이 ZIP 가져오기 흐름이 항상 제공되는 것은 아닙니다. Plugin Creator 또는 ZIP 가져오기 옵션이 보이지 않으면 아래 workspace 관리자 업로드 또는 ChatGPT Desktop 로컬 마켓플레이스 경로를 확인하세요.

### Workspace 관리자가 웹에서 업로드

ZIP 업로드 권한을 가진 적격 workspace owner 또는 admin이 다음 단계를 진행합니다.

1. ChatGPT 웹의 **Admin console**에서 대상 workspace를 선택합니다.
2. **Plugins**를 열고 **Add**를 선택합니다.
3. **Upload plugin**을 선택해 `pumui-daldal-0.1.0.zip`을 올립니다.

멤버에게 업로드 권한이 없으면 workspace 관리자에게 업로드를 요청하세요. 업로드 이후에도 workspace의 설치 정책과 역할 설정이 적용됩니다.

### ChatGPT Desktop에서 로컬 마켓플레이스 사용

로컬 마켓플레이스는 지원되는 ChatGPT Desktop의 Work 또는 Codex 화면에서 사용할 수 있습니다. 계정과 앱 버전에 따라 항목이 보이지 않을 수 있습니다.

1. [GitHub 저장소](https://github.com/yundaldal/gpt-plugins_daldal)에서 **Code → Download ZIP**으로 저장소 ZIP을 내려받아 압축을 풉니다. 이 경로에서는 플러그인 전용 ZIP이 아니라 저장소 ZIP을 사용합니다.
2. 압축을 푼 저장소 루트에서 `.agents/plugins/marketplace.json`과 `pumui-daldal/` 폴더가 함께 있는지 확인합니다.
3. PowerShell에서 저장소 루트로 이동해 로컬 마켓플레이스를 등록합니다.

   ```powershell
   Set-Location "<압축을 푼 저장소 폴더>"
   codex plugin marketplace add .
   ```

4. ChatGPT Desktop을 완전히 종료하고 다시 시작합니다.
5. **Plugins Directory**를 열고 `달달 품의 플러그인` 마켓플레이스를 선택한 뒤 플러그인을 설치합니다.

`codex` 명령이나 로컬 마켓플레이스가 계정에서 지원되지 않으면 workspace 관리자 업로드 경로를 사용하세요. 로컬 마켓플레이스는 공개 Plugins Directory에 게시하는 절차가 아니며, 데스크톱 및 계정별 제공 여부가 다를 수 있습니다.

## 로컬 실행 및 의존성

플러그인의 스킬은 워크플로와 스크립트를 안내합니다. 현재 ChatGPT 런타임이 첨부된 플러그인의 스크립트를 실행할 수 있다고 가정하지 마세요. HWPX·XLSX 파일을 이 패키지의 스크립트로 생성하려면 로컬에서 Python 3.10 이상과 `openpyxl`, `lxml`을 사용할 수 있어야 합니다.

```powershell
python -m pip install -r requirements.txt
python .\skills\pumui\scripts\run_case.py "D:\Private\case.json" "D:\Private\results" "D:\Private\input"
```

마지막 `input` 폴더 인자는 선택 사항입니다. 실제 자료와 산출물은 비공개 폴더에 두세요. 실행기는 입력 `case.json`을 결과 폴더에 저장하지 않습니다. 생성 결과는 유형에 따라 HWPX 기안문, 텍스트 미리보기, 수당 또는 물품 엑셀, 예산연결 업로드 엑셀, 준비점검표, 자동 점검 보고서입니다.

`requirements.txt`는 `openpyxl`과 `lxml`을 사용합니다. 자동 점검에서 실패가 나오면 보고서의 항목을 확인하고, 실패가 남은 결과를 완성본으로 사용하지 마세요.

## 검증

전체 GitHub 소스 트리의 `verification/` 폴더에 합성 입력 테스트가 있습니다. 플러그인 전용 ZIP에는 이 테스트 폴더가 들어 있지 않습니다. 저장소 소스를 받은 경우 저장소 루트에서 실행합니다.

```powershell
python -X utf8 -m unittest discover -s verification -v
```

검증은 모든 유형을 합성 입력으로 실행하고, 세금 경계값·시간별 수당·원고료 한도와 재활용 구간·누락 및 잘못된 입력의 생성 차단을 확인합니다. 합성 입력은 실제 인명, 기관명, 계좌, 과거 문서를 포함하지 않습니다.

이 테스트 결과는 ChatGPT 웹 또는 데스크톱에서 플러그인을 설치해 스크립트 실행과 파일 전달을 확인한 결과가 아닙니다. 해당 환경에서 실행 기능을 사용할 수 없다면 위의 로컬 실행 방법을 이용하세요.

## 공식 안내

- [ChatGPT 플러그인 설치와 ZIP 업로드](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)
- [로컬 및 저장소 플러그인 마켓플레이스](https://developers.openai.com/plugins/build/plugins)
- [Custom GPT의 Knowledge 업로드](https://help.openai.com/en/articles/8554397-creating-and-editing-gpts)

플러그인 원본 및 릴리스 자료: <https://github.com/yundaldal/gpt-plugins_daldal>
