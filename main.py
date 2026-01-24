import streamlit as st
import os
import time
import logging
import json
from dotenv import load_dotenv
from utils import (
    initialize_client,
    check_data_files,
    load_data,
    run_parallel_agents,
    run_head_agent,
    get_conversation_history,
    search_precedent,
    format_precedent_title,
    format_precedent_summary
)

# --- 환경 변수 및 Gemini API 설정 ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
client = initialize_client(GOOGLE_API_KEY)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 페이지 설정
st.set_page_config(
    page_title="관세법 판례 기반 챗봇",
    page_icon="⚖️",
    layout="wide",
)

# 애플리케이션 제목
st.title("⚖️ 관세법 판례 기반 챗봇")
st.markdown("관세법 판례 정보를 활용한 AI 기반 법률 챗봇입니다.")

# 탭 생성
tab1, tab2 = st.tabs(["💬 챗봇 모드", "🔍 판례 검색"])

# 대화 관련 설정
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_responses_history" not in st.session_state:
    st.session_state.agent_responses_history = []

if "expansion_results_history" not in st.session_state:
    st.session_state.expansion_results_history = []

if "processing" not in st.session_state:
    st.session_state.processing = False

# 대화 맥락 관리 설정
if "context_enabled" not in st.session_state:
    st.session_state.context_enabled = True

# 데이터 저장을 위한 세션 상태 설정
if "loaded_data" not in st.session_state:
    st.session_state.loaded_data = {
        "court_cases": [],
        "tax_cases": [],
        "preprocessed_data": {},
        "law_terms": []
    }

with st.sidebar:
    st.header("설정")
    
    
    # 대화 관리 옵션들
    st.header("대화 관리")
    
    # 대화 맥락 활용 옵션
    context_enabled = st.checkbox("이전 대화 맥락 활용", value=st.session_state.context_enabled)
    if context_enabled != st.session_state.context_enabled:
        st.session_state.context_enabled = context_enabled
        if context_enabled:
            st.success("이전 대화 맥락을 활용합니다.")
        else:
            st.info("각 질문을 독립적으로 처리합니다.")
    
    # 최근 대화 유지 수 선택
    if st.session_state.context_enabled:
        max_history = st.slider("최근 대화 유지 수", min_value=2, max_value=10, value=5)
        st.session_state.max_history = max_history
    
    # 새로운 대화 시작 버튼
    if st.button("새로운 대화 시작하기"):
        # 메시지 기록 및 에이전트 답변 초기화 (데이터는 유지)
        st.session_state.messages = []
        st.session_state.agent_responses_history = []
        st.session_state.expansion_results_history = []
        st.session_state.processing = False
        st.success("새로운 대화가 시작되었습니다.")

# 실행 시 데이터 파일 존재 여부 확인
has_data_files = check_data_files()
if not has_data_files:
    st.warning("일부 데이터 파일이 없습니다. 예시 데이터를 사용하거나 필요한 파일을 추가해주세요.")
else:
    # 데이터가 아직 로드되지 않았다면 로드
    if not st.session_state.loaded_data["court_cases"]:
        with st.spinner("데이터를 로드하고 전처리 중입니다..."):
            court_cases, tax_cases, preprocessed_data, law_terms = load_data()
            st.session_state.loaded_data = {
                "court_cases": court_cases,
                "tax_cases": tax_cases,
                "preprocessed_data": preprocessed_data,
                "law_terms": law_terms
            }
            st.success("데이터 로드 및 전처리가 완료되었습니다.")

# ==================== 탭 1: 챗봇 모드 ====================
with tab1:
    # 저장된 메시지 및 에이전트 답변 표시
    assistant_count = 0  # assistant 메시지 카운터
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # === 쿼리 확장 결과 표시 (NEW) ===
                if assistant_count < len(st.session_state.expansion_results_history):
                    expansion_result = st.session_state.expansion_results_history[assistant_count]
                    if expansion_result:
                        with st.expander("🔍 쿼리 확장 결과 보기", expanded=False):
                            st.markdown("**유사질문 (3개):**")
                            for i, q in enumerate(expansion_result['similar_questions'], 1):
                                st.markdown(f"{i}. {q}")

                            st.markdown("")
                            st.markdown("**핵심어:**")
                            for term in expansion_result['key_terms']:
                                st.markdown(f"• {term}")

                        st.divider()

                # === 에이전트 답변 표시 (기존) ===
                if assistant_count < len(st.session_state.agent_responses_history):
                    agent_responses = st.session_state.agent_responses_history[assistant_count]
                    if agent_responses:
                        # 에이전트 답변 표시 (expander)
                        with st.status("🤖 각 에이전트 답변 보기", state="complete", expanded=False):
                            for resp in agent_responses:
                                st.subheader(f"📋 {resp['agent']}")
                                st.markdown(resp['response'])
                                if resp != agent_responses[-1]:
                                    st.divider()

                        st.divider()

                # 최종 답변 표시
                st.markdown("### 📌 최종 답변")
                st.markdown(message["content"])

                # assistant 카운터 증가
                assistant_count += 1
            else:
                st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):

        # 사용자 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 처리 시작
        st.session_state.processing = True

        # 응답 생성
        with st.chat_message("assistant"):
            try:
                # 저장된 데이터 사용
                court_cases = st.session_state.loaded_data["court_cases"]
                tax_cases = st.session_state.loaded_data["tax_cases"]
                preprocessed_data = st.session_state.loaded_data["preprocessed_data"]
                law_terms = st.session_state.loaded_data["law_terms"]

                # 대화 맥락 가져오기
                conversation_history = ""
                if st.session_state.context_enabled:
                    conversation_history = get_conversation_history(
                        max_messages=st.session_state.get('max_history', 5)
                    )

                # === [섹션 0] 쿼리 확장 결과 표시 (NEW) ===
                query_expansion_section = st.empty()

                # === [섹션 1] 실시간 진행 상황 표시 ===
                progress_display = st.empty()

                # === [섹션 2] 에이전트 답변 동적 표시 (st.status) ===
                agent_status = st.status("🤖 에이전트 답변 생성 중...", expanded=True, state='running')

                # 에이전트 컨테이너 6개 미리 생성
                agent_containers = []
                with agent_status:
                    for i in range(6):
                        agent_containers.append(st.empty())

                # === [섹션 3] 최종 답변 (예약) ===
                final_answer_section = st.empty()

                # === 에이전트 병렬 실행 및 실시간 UI 업데이트 ===
                progress_display.markdown("⏳ 에이전트 실행 중...")

                # 제너레이터로 실시간 처리
                agent_responses = []
                expansion_result = None
                completed_count = 0

                for result in run_parallel_agents(
                    client, court_cases, tax_cases, preprocessed_data, prompt, conversation_history, law_terms
                ):
                    # 쿼리 확장 결과 처리 (첫 번째로 도착)
                    if result.get("type") == "expansion_result":
                        expansion_result = result["data"]

                        # 섹션 0에 쿼리 확장 expander 표시
                        with query_expansion_section.container():
                            with st.expander("🔍 쿼리 확장 결과 보기", expanded=False):
                                st.markdown("**유사질문 (3개):**")
                                for i, q in enumerate(expansion_result['similar_questions'], 1):
                                    st.markdown(f"{i}. {q}")

                                st.markdown("")
                                st.markdown("**핵심어:**")
                                for term in expansion_result['key_terms']:
                                    st.markdown(f"• {term}")

                            st.divider()

                        continue  # 다음 result 처리

                    # 에이전트 결과 처리
                    # 에이전트 인덱스 추출 (예: "Agent 3" -> 2)
                    agent_num = int(result['agent'].split()[-1]) - 1

                    # 즉시 UI 업데이트
                    with agent_containers[agent_num].container():
                        st.subheader(f"📋 {result['agent']}")
                        st.markdown(result['response'])
                        if agent_num < 5:
                            st.divider()

                    completed_count += 1
                    progress_display.markdown(f"✓ {result['agent']} 완료 ({completed_count}/6)")

                    agent_responses.append(result)

                # 순서대로 정렬 (완료 순서가 다를 수 있으므로)
                agent_responses.sort(key=lambda x: int(x['agent'].split()[-1]))

                # 모든 에이전트 완료
                progress_display.markdown("✓ 모든 에이전트 완료 | ⏳ 최종 답변 통합 중...")

                # === Head Agent로 최종 응답 생성 ===
                head_response = run_head_agent(
                    client, agent_responses, prompt, conversation_history
                )

                # 응답 텍스트 추출
                if isinstance(head_response, dict):
                    final_response = head_response.get("response", "응답을 생성할 수 없습니다.")
                else:
                    final_response = head_response

                # === [섹션 2] 자동으로 닫기 ===
                agent_status.update(
                    label="🤖 각 에이전트 답변 보기",
                    state="complete",
                    expanded=False
                )

                # === [섹션 1] 완료 상태 ===
                progress_display.markdown("✅ 답변 생성 완료!")
                time.sleep(0.3)
                progress_display.empty()

                # === [섹션 3] 최종 답변 표시 ===
                with final_answer_section.container():
                    st.markdown("### 📌 최종 답변")
                    st.markdown(final_response)

                # 응답 및 에이전트 답변 저장
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                st.session_state.agent_responses_history.append(agent_responses)
                st.session_state.expansion_results_history.append(expansion_result)

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                logging.error(f"전체 처리 오류: {str(e)}")
                # 오류 메시지도 저장
                error_message = f"오류가 발생했습니다: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                st.session_state.agent_responses_history.append([])  # 빈 리스트 추가 (인덱스 맞추기)
                st.session_state.expansion_results_history.append(None)  # None 추가 (인덱스 맞추기)

        # 처리 완료
        st.session_state.processing = False


# ==================== 탭 2: 판례 검색 ====================
with tab2:
    st.header("🔍 판례 검색")
    st.markdown("사건번호(2023도1907, 2017구합53518 등), 판례번호, 날짜 등으로 판례를 직접 검색할 수 있습니다.")

    # 검색창
    col1, col2 = st.columns([5, 1])
    with col1:
        search_query = st.text_input(
            "검색어 입력",
            placeholder="예: 2023도1907, 2023구합208027, 2024-12-19 등",
            key="search_input"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # 버튼 정렬을 위한 여백
        search_button = st.button("🔍 검색", type="primary", use_container_width=True)

    # 검색 옵션
    with st.expander("⚙️ 검색 옵션"):
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            max_results = st.slider("최대 결과 수", min_value=5, max_value=50, value=5, step=5)
        with col_opt2:
            min_score = st.slider("최소 유사도 점수", min_value=0.0, max_value=100.0, value=50.0, step=5.0)

    # 검색 실행 (버튼 클릭 또는 검색어 입력 시)
    if search_query:
        if not has_data_files:
            st.error("데이터 파일이 로드되지 않았습니다.")
        else:
            with st.spinner("검색 중..."):
                # 검색 수행
                results = search_precedent(
                    search_query,
                    st.session_state.loaded_data["court_cases"],
                    st.session_state.loaded_data["tax_cases"],
                    top_k=max_results,
                    min_score=min_score
                )

            # 결과 표시
            if results:
                st.success(f"✅ {len(results)}건의 판례를 찾았습니다.")

                # 결과 리스트
                for i, result in enumerate(results, 1):
                    score = result['score']
                    data = result['data']
                    source = result['source']
                    matched_fields = result.get('matched_fields', {})

                    # 제목 생성
                    title = format_precedent_title(result)

                    # 점수에 따른 색상 결정
                    if score >= 90:
                        score_color = "🟢"
                    elif score >= 70:
                        score_color = "🟡"
                    elif score >= 50:
                        score_color = "🟠"
                    else:
                        score_color = "🔴"

                    # 매칭 필드 표시
                    matched_info = ""
                    if matched_fields:
                        matched_info = " | 매칭: " + ", ".join([f"{field}({score:.0f})" for field, score in matched_fields.items()])

                    # Expander로 상세 내용 표시
                    with st.expander(f"{i}. {score_color} {title} (유사도: {score:.1f}점){matched_info}"):
                        # 매칭 상세 정보
                        if matched_fields:
                            st.markdown("#### 🎯 매칭 상세")
                            matched_text = " • ".join([f"**{field}**: {score:.1f}점" for field, score in matched_fields.items()])
                            st.markdown(matched_text)
                            st.divider()

                        # 요약 정보 표시
                        st.markdown("#### 📄 요약 정보")
                        summary = format_precedent_summary(result)
                        st.text(summary)

                        st.divider()

                        # 전체 데이터 표시
                        st.markdown("#### 📋 전체 데이터")

                        # 전체 내용을 보기 좋게 표시 (truncation 제거)
                        if source == 'kcs':
                            full_data_text = ""
                            fields = [
                                ("사건번호", data.get('사건번호', 'N/A')),
                                ("사건명", data.get('사건명', 'N/A')),
                                ("선고일자", data.get('선고일자\n(종결일자)', 'N/A')),
                                ("결과", data.get('결과', 'N/A')),
                                ("처분청", data.get('처분청', 'N/A')),
                                ("판결주문", data.get('판결주문', 'N/A')),
                                ("청구취지", data.get('청구취지', 'N/A')),
                                ("판결이유", data.get('판결이유', 'N/A'))
                            ]
                            for field_name, field_value in fields:
                                full_data_text += f"**{field_name}:**\n{field_value}\n\n"

                            with st.container(border=True):
                                st.markdown(full_data_text)
                        else:  # moleg
                            full_data_text = ""
                            fields = [
                                ("판례번호", data.get('판례번호', 'N/A')),
                                ("제목", data.get('제목', 'N/A')),
                                ("법원명", data.get('법원명', 'N/A')),
                                ("선고일자", data.get('선고일자', 'N/A')),
                                ("사건유형", data.get('사건유형', 'N/A')),
                                ("판결요지", data.get('판결요지', 'N/A')),
                                ("참조조문", data.get('참조조문', 'N/A')),
                                ("판결결과", data.get('판결결과', 'N/A')),
                                ("내용", data.get('내용', 'N/A'))
                            ]
                            for field_name, field_value in fields:
                                full_data_text += f"**{field_name}:**\n{field_value}\n\n"

                            with st.container(border=True):
                                st.markdown(full_data_text)

                        st.divider()

                        # 다운로드 버튼
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # JSON 다운로드
                            json_str = json.dumps(data, ensure_ascii=False, indent=2)
                            st.download_button(
                                label="📥 JSON 다운로드",
                                data=json_str,
                                file_name=f"precedent_{i}_{source}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        with col_dl2:
                            # 텍스트 다운로드
                            txt_content = f"{title}\n\n{summary}\n\n{json_str}"
                            st.download_button(
                                label="📄 TXT 다운로드",
                                data=txt_content,
                                file_name=f"precedent_{i}_{source}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
            else:
                st.warning("⚠️ 검색 결과가 없습니다. 다른 검색어를 시도해보세요.")

                # 검색 팁 제공
                with st.expander("💡 검색 팁 및 권장사항"):
                    st.markdown("""
                    ### 🎯 권장 검색 방법

                    **가장 정확한 검색:**
                    - ✅ **핵심 식별자만 입력** (사건번호/판례번호)
                    - 예: `2006두19105` (권장)
                    - 예: `2023구합208027` (권장)

                    **복합 검색 (식별자 + 날짜):**
                    - 예: `2023도1907 2024-12-19`
                    - 예: `2023구합208027 2024.12.19`

                    ---

                    ### 📋 검색 유형별 방법

                    **1. 사건번호로 검색 (KCS 판례)**
                    - 예: `대전지법2023구합208027` (전체)
                    - 예: `2023구합208027` (법원명 생략 - 권장)

                    **2. 판례번호로 검색 (MOLEG 판례)**
                    - 예: `2023도1907` (핵심 식별자만 - 권장 ✅)
                    - 예: `[대법원 2025. 2. 13. 선고 2023도1907 판결]` (전체)

                    **3. 날짜로 검색**
                    - 예: `2024-12-19` 또는 `2024.12.19` 또는 `2024년 12월 19일`

                    ---

                    ### 🔍 점수 계산 방식

                    **가중치:**
                    - 사건번호/판례번호: 80%
                    - 날짜: 20%

                    **보너스:**
                    - 2개 필드 매칭 (식별자 + 날짜): +5점
                    """)

    # 초기 화면 안내
    if not search_query:
        st.info("👆 위의 검색창에 사건번호, 판례번호, 날짜 등을 입력하세요. (Enter 키로 검색)")

        # 사용 예시
        with st.expander("📚 검색 가이드 및 사용 예시", expanded=True):
            st.markdown("""
            ### 🎯 권장 검색 방법

            **가장 정확한 검색: 핵심 식별자만 입력**
            - ✅ 사건번호/판례번호만 입력 (권장)

            ---

            ### 검색 예시

            **1. 판례번호 검색 (가장 권장 ✅)**
            ```
            2023도1907
            ```
            → MOLEG 판례 데이터에서 정확한 판례 검색

            **2. 사건번호 검색 (권장 ✅)**
            ```
            2023구합208027
            ```
            또는
            ```
            대전지법2023구합208027
            ```
            → KCS 판례 데이터에서 정확한 사건 검색

            **3. 날짜 검색**
            ```
            2024-12-19
            ```
            → 해당 날짜에 선고된 판례 검색

            **4. 복합 검색 (식별자 + 날짜)**
            ```
            2023도1907 2024-12-19
            ```
            → 사건번호와 날짜를 조합하여 검색

            ---

            ### 🔍 점수 계산 방식

            - **사건번호/판례번호**: 80% 가중치
            - **날짜**: 20% 가중치
            - **복수 필드 매칭 보너스**: 2개(+5점)
            """)


# 사이드바에 사용 예시 및 정보 추가
with st.sidebar:
    st.subheader("프로젝트 정보")
    st.markdown("""
    이 챗봇은 관세법 판례를 기반으로 답변을 생성합니다.

    **시스템 구조 및 Fallback 전략**
    - **Query Expansion & Individual Agents**:
      - Primary: Gemini 2.5 Flash
      - Fallback: Gemini 2.5 Flash Lite
    - **Head Agent (종합 분석)**:
      - Primary: Gemini 3.0 Flash Preview (Experimental)
      - Fallback 1: Gemini 2.5 Flash
      - Fallback 2: Gemini 2.5 Flash Lite
    - **검색 알고리즘**: Character n-gram TF-IDF

    **주요 장점**
    - 완전 무료 (Gemini API 무료 티어)
    - 일반 노트북/무료 Streamlit Cloud 구동
    - 빠른 응답 (검색 0.05초, 답변 5-10초)
    """)