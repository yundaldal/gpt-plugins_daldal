# 달달샘 GPT 플러그인 모음

교육·업무용 플러그인을 모아 공유하는 저장소입니다. 기존 플러그인과 공개용으로 점검한 플러그인 6종을 제공합니다.

| 플러그인 | 주요 기능 | 다운로드 | 사용·기능 안내 |
|---|---|---|---|
| 관련 공문 정보 추출기_달달샘 | 기안할 때 관련 공문을 참고해야 할때 에듀파인에서 캡쳐해서 넣어주면 추출해줍니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/related-document-extractor.zip) | [플러그인 안내](plugins/related-document-extractor/README.md) |
| 품의 기안 도우미_달달샘 | 수당·물품·경비 품의 초안, 계산 산출물 및 교차 점검 | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/pumui-daldal-0.1.2.zip) | [사용 안내·원본](plugins/pumui-daldal/) |
| 특수교육 개별화교육계획(iep)평가 입력 도우미_달달샘 | 월별 교육목표·내용·방법·평가계획과 관찰 기록을 바탕으로 특수교육 평가 문장을 간결하고 긍정적인 NEIS 입력 형태로 다듬습니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/iep-eval.zip) | [플러그인 안내](plugins/iep-eval/README.md) |
| 개념기반 교육과정 설계 도우미(핵심개념, 일반화, 탐구질문을 생성) - 달달샘 | 수업 주제와 교과·학년 맥락을 바탕으로 핵심개념, 일반화 문장, 사실적·개념적·논쟁적 탐구질문을 연결해 설계합니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/ib-core.zip) | [플러그인 안내](plugins/ib-core/README.md) |
| 품의기안문과 첨부엑셀파일을 생성하는 AI - 달달샘 | 견적서나 품목 목록을 분석해 학교 품의 문안과 항목·수량·단가·합계를 담은 업로드용 Excel을 작성합니다. 파일 근거와 금액 산식을 대조합니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/approval-excel.zip) | [플러그인 안내](plugins/approval-excel/README.md) |
| 개념기반 교육과정 설계 디자이너 챗봇 (Feat. 에듀테크)- 다양한 학습자용_달달샘 | 교육과정·학년·교과 맥락을 순서대로 확인한 뒤 개념 기반 단원 요소와 차시별 지도안을 설계합니다. 학생의 다양한 학습 요구에 맞는 수업 지원도 연결합니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/ib-planner.zip) | [플러그인 안내](plugins/ib-planner/README.md) |
| 캔바 AI 코드 생성 프롬프트 생성기 | 수업 아이디어를 Canva AI 또는 Canva Code에 넣을 한국어 학습 게임 제작 프롬프트로 바꿉니다. 상호작용, 화면 흐름, 접근성, 반응형 동작과 오류 회복을 구체화합니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/canva-game.zip) | [플러그인 안내](plugins/canva-game/README.md) |
| 특수교육 개별화교육계획(IEP)설계 도우미_성취기준도 연결_달달샘 | 학생의 현재 수준과 지원 요구를 바탕으로 개별화교육계획을 단계적으로 설계하고, 포함된 특수교육 교육과정 기준표에서 실제 분류번호와 문구를 확인해 연결합니다. | [ZIP 다운로드](https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/iep-plan.zip) | [플러그인 안내](plugins/iep-plan/README.md) |

## 설치 안내

[무료·유료 계정별 설치 조건, ZIP 업로드, GitHub 마켓플레이스 가져오기](INSTALLATION.md)를 확인하세요. GitHub에서 ZIP을 내려받는 것만으로 ChatGPT에 자동 설치되지는 않습니다.

ZIP 다운로드, 워크스페이스 업로드, 사용자 설치는 각각 별도 단계입니다. 업로드는 플러그인을 워크스페이스에 등록합니다. 설치 정책이 **사용 가능(Available)**이면 각 사용자가 플러그인 디렉터리에서 **플러그인 설치(Install plugin)**를 눌러야 하고, 관리자가 **설치됨(Installed)** 정책을 설정하면 대상 사용자에게 자동 설치됩니다. 자세한 절차는 [설치 안내](INSTALLATION.md)를 참고하세요. 이 저장소 ZIP의 실제 ChatGPT 설치 흐름은 검증하지 않았으며, 메뉴와 권한은 계정·워크스페이스에 따라 달라질 수 있습니다. 배포 ZIP은 `downloads/`에서 제공합니다. GitHub Releases는 아직 구성하지 않았습니다.

## 품의 자료와 산출물 위치 선택

- **로컬 폴더에서 자료를 읽고 결과도 폴더에 저장하려면:** ChatGPT Desktop에서 프로젝트를 만들고, 프로젝트의 **Work** 또는 **Codex** 작업에서 사용할 로컬 폴더를 열어 접근을 허용합니다. 입력 자료를 해당 폴더에 두고, 산출물을 저장할 폴더 경로도 요청에 지정합니다. 프로젝트를 만들기만 해서는 PC 폴더가 자동 연결되지 않습니다.
- **프로젝트에서 로컬 폴더를 열지 않고 작업하려면:** 품의 자료를 해당 채팅창에 첨부합니다. 결과는 같은 채팅의 답변이나 다운로드 파일로 제시되며, PC의 로컬 폴더에 자동 저장되지는 않습니다.

ChatGPT 웹은 PC의 로컬 폴더에 직접 접근할 수 없습니다. 데스크톱의 로컬 파일 접근은 앱·Work/Codex 권한과 폴더 접근 허용이 필요합니다. [ChatGPT Work와 Codex 안내](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex)를 참고하세요.
## 플러그인 형식

새로 추가한 6개는 외부 MCP 서버나 API 키를 요구하지 않는 Skills 전용 플러그인입니다. 사용자 요청에 맞는 지침과 참고자료를 ChatGPT에 제공합니다.

## 공개 자료 점검

학생 사례는 식별할 수 없는 합성 예시로 바꿨고, 학교·기관명·개인 이름·내부 문서번호와 Office 작성자 메타데이터를 정리했습니다. IEP 성취기준 데이터는 원본 표 본문을 보존했습니다. IEP 참고 PDF 캡처 5개는 공개 재배포 대신 주제와 작성 절차를 담은 자체 안내 자료로 대체했습니다.

예시와 시험용 입력은 가상 정보이며, IEP 성취기준표는 정확성을 위해 공식 기준 자료를 유지했습니다. 문서와 계산 결과는 검토용 초안이므로 원자료, 단가 적용 여부와 회계 요건을 담당자가 확인한 뒤 사용하세요.

## GitHub 마켓플레이스

워크스페이스 관리자는 [marketplace.json](.agents/plugins/marketplace.json)을 가져와 플러그인을 관리할 수 있습니다. 개인 요금제 사용자의 설치 기능과는 별개이며, 가져오기 후에도 각 워크스페이스의 접근 정책을 설정해야 합니다.
