# 합성 대화 하네스 시나리오

이 시나리오는 `플러그인 참고/01.png`~`05.png`에서 확인한 실제 질문 방식의 판단 지점을 합성 자료로 되짚습니다. 사진의 문구와 순서를 모든 품의에 그대로 적용하지 않습니다. 품의 유형, 현재 자료, 이미 확인한 답에 맞는 질문만 하나씩 제시합니다.

모든 질문은 카탈로그의 객관식 보기를 보여 주며 `직접 입력`도 같은 선택지 목록에 둡니다. 입력이 필요한 선택지를 고른 뒤에는 별도 값을 받습니다. 아래의 SYNTHETIC 값은 테스트용 가상 자료입니다.

| 시나리오 | 합성 조건 | 질문·예상 적용 | 회귀 확인 |
|---|---|---|---|
| 유형 추천 검토 | 추출 근거는 A4를 추천하지만 확정 확인은 없음 | `type.confirm`: 추천 진행 / 유형 선택 / 직접 입력 중 하나를 선택할 때까지 유형을 확정하지 않음 | `test_required_choice_followup_and_custom_values_are_validated`, `test_type_and_attachment_choices_must_match_the_case` |
| 자료 추가 후 재개 | 요청서 파일이 누락됨 | `intake.readiness`: 현재 자료 점검 / 자료 추가 후 점검 / 직접 입력. 자료를 추가하겠다는 선택만 기록한 상태로는 생성하지 않음 | `test_add_replace_and_rate_review_require_an_inspected_input_file`, `test_generation_requires_state_file_and_blocks_unresolved_state` |
| 읽을 수 없는 원본 | 손상된 HWPX 또는 현재 도구에서 읽지 못하는 파일 | `source.unreadable`: 읽을 수 있는 자료로 교체 / 내용을 직접 입력 / 직접 입력. 확인되지 않은 원문을 추정하지 않음 | `test_document_adapter.py`의 손상·빈 문서 사례 |
| 서로 다른 출처 값 | `SYNTHETIC_SOURCE_A`와 `SYNTHETIC_SOURCE_B`가 같은 세션 제목에 다르게 기록됨 | `source.conflict::session[0]`에서 출처를 묶어 확인하고 선택값을 case에 반영. 원본 변경 시 답변을 stale로 처리 | `test_source_conflict_answer_is_bound_to_resolved_case_value`, `test_source_revision_marks_old_answers_stale` |
| 추출값 수정 | 회의 제목 `SYNTHETIC_SOURCE_A`를 사용자가 `SYNTHETIC_EDIT`으로 고침 | `field.confirm::session[0]`: 추출값 사용 / 직접 수정 / 직접 입력. 수정한 값과 case 값이 다르면 생성 차단 | `test_repeated_session_instances_are_catalogued_and_required`, `test_extracted_value_and_conflict_questions_require_source_bindings` |
| 사람별 교통비 | 두 사람의 교통비 확인 상태가 서로 다름 | `travel.present::person[0]`, `travel.present::person[1]`을 독립적으로 묻고 각 답을 `allowance.people[i].travel.amount`에 적용 | `test_repeated_question_instances_are_independent`, `test_travel_amount_followup_must_equal_bound_case_amount` |
| 붙임 선택 | 합성 붙임 목록에 필수·선택 파일이 함께 있음 | `attachment.include`: 현재 목록 사용 / 목록 수정 / 직접 입력. 최종 목록을 case와 대조하고 번호를 다시 확인 | `test_type_and_attachment_choices_must_match_the_case` |
| 기준 단가 확인 | 기관·회계연도에 맞는 단가 근거가 아직 없음 | `rate.confirm`: 기준 단가 확인 / 기준 자료 재검토 / 직접 입력. 검토를 선택하면 실제 입력 파일을 읽고 확인하기 전 계산을 확정하지 않음 | `test_add_replace_and_rate_review_require_an_inspected_input_file`, `test_rate_review_with_verified_file_can_be_marked_answered` |
| 유형과 무관한 질문 제외 | 물품 또는 경비 자료에 A4 컨설팅 질문 조건이 없음 | 해당 질문을 제시하지 않고 필요한 입력만 확인 | `test_context_selects_only_questions_triggered_by_intake_facts`, `test_repeat_counts_do_not_leak_questions_into_unrelated_context` |

기계 하네스는 질문 ID·선택값·직접 입력값·출처 revision·최종 case 값을 비교합니다. 대화 모델이 실제로 질문을 제시하는 모양과 문장 선택은 위 시나리오를 사용한 별도 실행 평가 대상이며, 플러그인 지침이나 단위시험만으로 UI 버튼 노출까지 보증하지 않습니다.
