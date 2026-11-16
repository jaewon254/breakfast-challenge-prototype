import streamlit as st
import datetime
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# =====================================================================
# 🚨 이곳에 기존에 사용하던 '구글 스프레드시트' 인터넷 주소를 넣어주세요!
# (양끝 큰따옴표 "" 는 절대 지우지 마세요!)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1opWmQ2UfHILLSFEBDY778hi35A5Lly10hvaw9wlpPto/edit?gid=0#gid=0"
# =====================================================================

st.set_page_config(page_title="나 혼자 잘 먹는다 챌린지", page_icon="🍱", layout="centered")

# -----------------------------------------------------------------------------
# 0. 데이터베이스(구글 시트) 연결 및 시트 자동 초기화
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    secret_dict = json.loads(st.secrets["google_secret"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def get_or_create_sheets():
    client = init_connection()
    spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)
    
    # 1) 데일리 체크인 기록용 시트 확인 및 자동 생성
    try:
        checkin_sheet = spreadsheet.worksheet("체크인_기록")
    except gspread.WorksheetNotFound:
        checkin_sheet = spreadsheet.add_worksheet(title="체크인_기록", rows="1000", cols="10")
        checkin_sheet.append_row(["인증일시", "이름", "챌린지시작일", "진행주차", "진행일차", "일차번호", "식사여부", "식사형태"])
        
    # 2) 사전/사후 TPB 설문 기록용 시트 확인 및 자동 생성
    try:
        survey_sheet = spreadsheet.worksheet("설문_기록")
    except gspread.WorksheetNotFound:
        survey_sheet = spreadsheet.add_worksheet(title="설문_기록", rows="1000", cols="15")
        survey_sheet.append_row([
            "제출일시", "설문구분", "이름", "나이",
            "Q1(태도)", "Q2(주관적규범1)", "Q3(주관적규범2)",
            "Q4(행동통제1)", "Q5(행동통제2)", "Q6(행동의도1)", "Q7(행동의도2)", "Q8(최근30일행동)"
        ])
        
    return checkin_sheet, survey_sheet

@st.cache_data(ttl=60)
def load_user_checkins(user_name):
    if not user_name.strip():
        return []
    try:
        checkin_sheet, _ = get_or_create_sheets()
        records = checkin_sheet.get_all_records()
        completed_days = [
            int(row["일차번호"]) for row in records
            if str(row.get("이름", "")).strip() == user_name.strip() and "네" in str(row.get("식사여부", ""))
        ]
        return list(set(completed_days))
    except Exception:
        return []

# -----------------------------------------------------------------------------
# 1. 28일(4주) 추천 메뉴 리스트 (맞춤 필터링 태그 포함)
# -----------------------------------------------------------------------------
RECOMMENDATIONS = [
    # 1주 차
    {"menu": "바나나 1개 + 무가당 두유", "time": "1분", "point": "불이 필요 없고 든든한 식물성 단백질 충전!", "no_cook": True, "dairy_free": True},
    {"menu": "사과 반 쪽 + 삶은 계란 1개", "time": "1분 (미리 준비)", "point": "아침 사과는 금! 식이섬유와 질 좋은 단백질의 조화.", "no_cook": True, "dairy_free": True},
    {"menu": "그릭 요거트 + 한줌 견과류", "time": "1분", "point": "유산균과 건강한 지방으로 장 건강과 뇌 활력을 동시에!", "no_cook": True, "dairy_free": False},
    {"menu": "통밀빵 1쪽 + 슬라이스 치즈", "time": "2분", "point": "복합 탄수화물로 아침 혈당을 완만하게 올려줍니다.", "no_cook": True, "dairy_free": False},
    {"menu": "편의점 감동란 2개 + 아몬드 브리즈", "time": "1분", "point": "바쁜 아침, 출근/등교길 편의점에서 바로 픽업하는 꿀조합!", "no_cook": True, "dairy_free": True},
    {"menu": "시리얼 한 컵 + 우유", "time": "1분", "point": "가장 클래식한 아침! 당분이 적은 시리얼을 추천해요.", "no_cook": True, "dairy_free": False},
    {"menu": "오버나이트 오트밀", "time": "0분 (전날 준비)", "point": "전날 우유에 불려둔 오트밀을 꺼내 먹기만 하면 끝!", "no_cook": True, "dairy_free": False},
    
    # 2주 차
    {"menu": "전자레인지 머그컵 계란찜", "time": "3분", "point": "계란 2개와 물 약간, 전자레인지 3분이면 따뜻한 단백질 완성!", "no_cook": False, "dairy_free": True},
    {"menu": "편의점 참치마요 삼각김밥 + 따뜻한 차", "time": "1분", "point": "한국인은 밥심! 든든하게 탄수화물을 채워요.", "no_cook": True, "dairy_free": True},
    {"menu": "단백질 쉐이크 + 바나나 반 개", "time": "2분", "point": "마시는 단백질로 빠르고 간편하게 포만감을 줍니다.", "no_cook": True, "dairy_free": False},
    {"menu": "인스턴트 컵수프 + 모닝빵 1개", "time": "3분", "point": "따뜻한 물만 부으면 완성! 속을 편안하게 데워줍니다.", "no_cook": False, "dairy_free": False},
    {"menu": "그래놀라 + 플레인 요거트", "time": "1분", "point": "바삭한 식감으로 잠든 뇌를 깨워주는 아침 식사.", "no_cook": True, "dairy_free": False},
    {"menu": "고구마 1개 + 우유", "time": "1분 (미리 준비)", "point": "식이섬유가 풍부해 점심때까지 배고프지 않아요.", "no_cook": True, "dairy_free": False},
    {"menu": "닭가슴살 소시지 + 방울토마토 5알", "time": "3분", "point": "전자레인지 조리로 끝내는 고단백 아침식사.", "no_cook": False, "dairy_free": True},

    # 3주 차
    {"menu": "식빵 토스트 + 딸기잼 얇게", "time": "3분", "point": "토스터기만 있으면 끝! 커피와 가장 잘 어울려요.", "no_cook": False, "dairy_free": True},
    {"menu": "연두부 1팩 + 오리엔탈 드레싱", "time": "1분", "point": "소화가 안 되는 아침에 가장 부드럽게 넘어가는 메뉴.", "no_cook": True, "dairy_free": True},
    {"menu": "편의점 단백질 바 + 아메리카노", "time": "1분", "point": "정말 시간이 없을 때 주머니에 넣고 나갈 수 있는 비상식량!", "no_cook": True, "dairy_free": True},
    {"menu": "참치마요 카나페 (크래커 + 참치 약간)", "time": "3분", "point": "작지만 강력한 열량! 색다른 아침을 원할 때 좋아요.", "no_cook": True, "dairy_free": True},
    {"menu": "냉동 블루베리 + 요거트 + 꿀 약간", "time": "2분", "point": "눈 건강에 좋은 안토시아닌과 상큼함으로 아침을 시작해요.", "no_cook": True, "dairy_free": False},
    {"menu": "미숫가루(우유에 타서) + 견과류", "time": "2분", "point": "고소한 전통식 아침! 포만감이 아주 뛰어납니다.", "no_cook": True, "dairy_free": False},
    {"menu": "크래미(맛살) 2개 + 스트링 치즈 1개", "time": "1분", "point": "포장만 벗기면 끝! 짭조름한 단백질 간편식.", "no_cook": True, "dairy_free": False},

    # 4주 차
    {"menu": "인절미(떡) 3조각 + 두유", "time": "1분", "point": "냉동실 떡을 전자레인지에 살짝 돌려 쫄깃하게 즐겨요.", "no_cook": False, "dairy_free": True},
    {"menu": "오트밀 컵죽", "time": "3분", "point": "시판 오트밀 죽에 뜨거운 물만 부으면 든든한 한 끼 완성.", "no_cook": False, "dairy_free": True},
    {"menu": "냉동 볶음밥 반 공기", "time": "3분", "point": "남은 볶음밥을 소분해 두었다가 아침에 데워 먹기만 하세요.", "no_cook": False, "dairy_free": True},
    {"menu": "구운 계란 2개 + 사과즙 1팩", "time": "1분", "point": "유통기한이 긴 구운 계란은 1인 가구의 든든한 동반자입니다.", "no_cook": True, "dairy_free": True},
    {"menu": "냉동 만두 3개 (전자레인지 조리)", "time": "3분", "point": "전자레인지용 찜기를 활용하면 촉촉하게 수분을 채운 아침 완성!", "no_cook": False, "dairy_free": True},
    {"menu": "토마토 1개 + 올리브오일 살짝", "time": "2분", "point": "신선하고 가볍게! 비타민 흡수율을 높인 지중해식 아침.", "no_cook": True, "dairy_free": True},
    {"menu": "나만의 3분 컷 최애 조합!", "time": "자유", "point": "지난 4주간 가장 맘에 들었던 메뉴를 스스로 차려보세요!", "no_cook": True, "dairy_free": True},
]

# -----------------------------------------------------------------------------
# 2. 사이드바: 참여자 정보 및 일정 관리
# -----------------------------------------------------------------------------
st.sidebar.header("👤 참여자 정보 설정")
user_name = st.sidebar.text_input("이름 (또는 닉네임) 입력", placeholder="예: 김서연")
start_date = st.sidebar.date_input("챌린지 시작일 선택", datetime.date.today())

# 시작일 기준 실제 경과 일차 계산 (1일 차 ~ 28일 차)
today = datetime.date.today()
elapsed_days = (today - start_date).days + 1
if elapsed_days < 1:
    st.sidebar.warning("아직 챌린지 시작일 전입니다. 시작일을 오늘로 맞추면 바로 인증할 수 있습니다.")
else:
    st.sidebar.success(f"현재 챌린지 **{min(elapsed_days, 28)}일 차** 진행 중!")

st.sidebar.divider()
st.sidebar.header("🗓️ 주차·일차 탐색")
weeks = ["1주 차: 태도 형성", "2주 차: 주관적 규범", "3주 차: 행동 통제", "4주 차: 습관 정착"]
week = st.sidebar.radio("주차 선택:", weeks)

days = ["1일 차", "2일 차", "3일 차", "4일 차", "5일 차", "6일 차", "7일 차"]
day = st.sidebar.radio(f"{week[:4]} 일차 선택:", days)

week_index = weeks.index(week)
day_index = days.index(day)
total_day_index = (week_index * 7) + day_index
selected_day_num = total_day_index + 1  # 1 ~ 28

# -----------------------------------------------------------------------------
# 3. 메인 화면 및 3단계 탭 구성
# -----------------------------------------------------------------------------
st.title("🍱 나 혼자 잘 먹는다: 3분 챌린지")
st.markdown("20대 1인 가구를 위한 계획된 행동이론(TPB) 기반 4주 아침식사 습관 프로젝트")

if not user_name.strip():
    st.warning("👈 왼쪽 사이드바에서 **이름(또는 닉네임)**과 **챌린지 시작일**을 먼저 입력해 주세요! 입력하신 이름으로 출석 기록과 설문이 연동됩니다.")

tab_pre, tab_daily, tab_post = st.tabs([
    "📋 1. 사전 설문 (시작 전)",
    "🍱 2. 데일리 3분 챌린지 (1~28일)",
    "🏆 3. 사후 설문 (4주 완료 후)"
])

# =============================================================================
# [탭 1] 사전 설문 (Pre-test)
# =============================================================================
with tab_pre:
    st.subheader("📋 챌린지 시작 전 사전 설문 (Pre-test)")
    st.markdown("챌린지를 시작하기 전, 평소 아침식사에 대한 생각과 빈도를 기록합니다. (4주 후 사후 설문과 비교 분석됩니다.)")
    
    with st.form("pre_survey_form"):
        pre_age = st.number_input("만 나이를 입력하세요", min_value=15, max_value=100, value=22, key="pre_age")
        st.markdown("---")
        st.markdown("**💡 각 문항에 대해 평소 자신이 생각하는 정도를 선택해 주세요.** *(1점: 전혀 그렇지 않다 ~ 5점: 매우 그렇다)*")
        
        q1 = st.slider("1. [태도] 아침 식사를 규칙적으로 하는 것은 나의 건강과 일상생활에 도움이 된다고 생각한다.", 1, 5, 3, key="pre_q1")
        q2 = st.slider("2. [주관적 규범] 가족이나 친구 등 나에게 중요한 사람들은 내가 아침 식사를 규칙적으로 하기를 바란다고 생각한다.", 1, 5, 3, key="pre_q2")
        q3 = st.slider("3. [주관적 규범] 내 주변 사람들은 아침 식사를 챙겨 먹는 행동을 긍정적으로 평가한다고 생각한다.", 1, 5, 3, key="pre_q3")
        q4 = st.slider("4. [인지된 행동 통제력] 바쁜 아침에도 5분 이내의 간편식을 활용하면 아침 식사를 챙겨 먹을 수 있다는 자신감이 있다.", 1, 5, 3, key="pre_q4")
        q5 = st.slider("5. [인지된 행동 통제력] 시간이나 비용이 부족하더라도 아침 식사를 규칙적으로 실천할 수 있다고 생각한다.", 1, 5, 3, key="pre_q5")
        q6 = st.slider("6. [행동 의도] 앞으로 2주 동안 최소 3회 이상 아침 식사를 챙겨 먹을 의향이 있다.", 1, 5, 3, key="pre_q6")
        q7 = st.slider("7. [행동 의도] 앞으로 아침 식사를 지속적인 생활 습관으로 유지하기 위해 노력할 것이다.", 1, 5, 3, key="pre_q7")
        
        st.markdown("---")
        q8 = st.number_input("8. [실제 행동] 최근 30일 동안 아침 식사를 한 날은 며칠입니까? (0일 ~ 30일)", min_value=0, max_value=30, value=0, key="pre_q8")
        
        pre_submit = st.form_submit_button("사전 설문 제출하기")
        
        if pre_submit:
            if not user_name.strip():
                st.error("왼쪽 사이드바에 이름(또는 닉네임)을 먼저 입력해 주세요!")
            else:
                try:
                    _, survey_sheet = get_or_create_sheets()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    survey_sheet.append_row([
                        now_str, "사전설문(Pre)", user_name.strip(), pre_age,
                        q1, q2, q3, q4, q5, q6, q7, q8
                    ])
                    st.success("✅ 사전 설문이 구글 스프레드시트에 안전하게 저장되었습니다! 이제 '2. 데일리 3분 챌린지' 탭으로 이동해 주세요.")
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")

# =============================================================================
# [탭 2] 데일리 3분 챌린지 (맞춤 필터 + 날짜 잠금 + 구글 시트 영구 저장)
# =============================================================================
with tab_daily:
    # 1) 맞춤형 메뉴 필터링 옵션
    st.markdown("#### 🔍 나만의 식습관·조리환경 맞춤 필터")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filter_dairy = st.checkbox("🥛 유당불내증 / 우유·유제품 제외")
    with f_col2:
        filter_nocook = st.checkbox("🔥 불·전자레인지 없이 바로 섭취")
        
    todays_pick = RECOMMENDATIONS[total_day_index]
    
    # 필터 조건에 맞지 않을 경우 대체 메뉴 자동 추천
    is_dairy_ok = (not filter_dairy) or todays_pick["dairy_free"]
    is_nocook_ok = (not filter_nocook) or todays_pick["no_cook"]
    
    st.subheader(f"💡 {week[:4]} {day} (전체 {selected_day_num}일 차) 추천 메뉴")
    if is_dairy_ok and is_nocook_ok:
        st.info(f"**{todays_pick['menu']}** (소요 시간: {todays_pick['time']})\n\n👉 **추천 이유:** {todays_pick['point']}")
    else:
        filtered_pool = [
            item for item in RECOMMENDATIONS
            if ((not filter_dairy) or item["dairy_free"]) and ((not filter_nocook) or item["no_cook"])
        ]
        alt_pick = filtered_pool[total_day_index % len(filtered_pool)]
        st.warning(f"기존 메뉴({todays_pick['menu']})는 선택한 필터 조건과 맞지 않아 맞춤 대체 메뉴를 추천합니다!")
        st.info(f"**[맞춤 대체] {alt_pick['menu']}** (소요 시간: {alt_pick['time']})\n\n👉 **추천 이유:** {alt_pick['point']}")
        todays_pick = alt_pick

    st.divider()

    # 2) 주차별 심리 미션
    st.subheader(f"📢 이번 주 심리 미션: {week}")
    if week_index == 0:
        st.markdown("**[행동에 대한 태도 (Attitude)]** 아침 식사는 나를 위한 최고의 투자!\n\n아침을 챙겨 먹는 것은 귀찮은 일이 아니라, **오늘 하루 나의 집중력과 활력을 높이는 긍정적인 행동**입니다.")
    elif week_index == 1:
        st.markdown("**[주관적 규범 (Subjective Norm)]** 요즘 갓생러들의 필수 루틴, 3분 아침식사!\n\n많은 20대들이 아침 굶기를 멈추고 자신만의 간편한 조식 루틴을 만들고 있습니다.")
    elif week_index == 2:
        st.markdown("**[지각된 행동 통제 (Perceived Behavioral Control)]** 불 없이 3분이면 끝! 내가 완벽히 통제하는 아침\n\n'시간이 없어서'는 더 이상 핑계가 될 수 없죠? 칼도 불도 필요 없는 3분 컷 메뉴들로 완벽하게 통제하고 있습니다.")
    else:
        st.markdown("**[행동 의도와 실천 (Intention & Behavior)]** 나만의 아침 식사 습관, 이제는 완벽한 내 일상으로!\n\n벌써 4주 차입니다. 이제 3분 아침식사는 평생을 갈 당신만의 건강한 무기입니다.")

    st.divider()

    # 3) 데일리 체크인 (순차 해금 제어 + 영구 저장)
    st.subheader(f"✅ {week[:4]} {day} 인증")
    is_locked = selected_day_num > elapsed_days
    
    if is_locked:
        st.error(f"🔒 **미래 날짜 잠금 안내:** 설정하신 시작일({start_date}) 기준 오늘은 **{max(elapsed_days, 0)}일 차**입니다. {selected_day_num}일 차 인증은 해당 날짜가 되면 자동으로 열립니다!")
    
    with st.form(f"daily_checkin_{total_day_index}"):
        ate_breakfast = st.radio("오늘 아침(또는 첫 끼)을 챙겨 드셨나요?", ("네, 먹었습니다 😋", "아니요, 굶었습니다 🥲"), disabled=is_locked)
        meal_type = st.selectbox(
            "어떤 형태로 드셨나요?",
            ("선택 안 함 (굶음)", f"추천 메뉴: {todays_pick['menu']}", "편의점 간편식", "전자레인지 간편 조리", "어제 남은 음식", "배달 음식", "기타 (직접 요리 등)"),
            disabled=is_locked
        )
        submit_btn = st.form_submit_button("오늘 하루 인증하고 구글 시트에 기록하기", disabled=is_locked)
        
        if submit_btn:
            if not user_name.strip():
                st.error("왼쪽 사이드바에 이름(또는 닉네임)을 먼저 입력해 주세요!")
            else:
                try:
                    checkin_sheet, _ = get_or_create_sheets()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    checkin_sheet.append_row([
                        now_str,
                        user_name.strip(),
                        str(start_date),
                        week[:4],
                        day,
                        selected_day_num,
                        ate_breakfast,
                        meal_type
                    ])
                    st.cache_data.clear()  # 캐시 초기화하여 즉시 달성률 갱신
                    
                    if "네" in ate_breakfast:
                        st.success(f"최고예요! '{meal_type}' 인증 기록이 구글 스프레드시트에 영구 저장되었습니다. 🎉")
                    else:
                        st.info(f"기록이 저장되었습니다. 내일은 꼭 '{todays_pick['menu']}'에 도전해 보세요! 💪")
                except Exception as e:
                    st.error(f"인증 기록 저장 중 오류가 발생했습니다: {e}")

    st.divider()

    # 4) 구글 시트 연동 실시간 달성률 시각화 (새로고침해도 유지됨)
    st.subheader("📊 나의 4주 누적 달성률 (실시간 DB 연동)")
    completed_days = load_user_checkins(user_name)
    progress_count = len(completed_days)
    progress_rate = min(progress_count / 28.0, 1.0)
    
    st.progress(progress_rate)
    if user_name.strip():
        st.markdown(f"**{user_name.strip()}**님의 누적 인증 일수: 총 28일 중 **{progress_count}일** 완료! (달성률: **{int(progress_rate * 100)}%**)")
    else:
        st.markdown("왼쪽 사이드바에 이름을 입력하면 본인의 누적 달성률이 자동으로 불러와집니다.")

# =============================================================================
# [탭 3] 사후 설문 (Post-test)
# =============================================================================
with tab_post:
    st.subheader("🏆 4주 챌린지 완료 후 사후 설문 (Post-test)")
    st.markdown("4주간의 아침식사 챌린지를 마친 후의 생각과 행동 변화를 기록합니다.")
    
    with st.form("post_survey_form"):
        post_age = st.number_input("만 나이를 입력하세요", min_value=15, max_value=100, value=22, key="post_age")
        st.markdown("---")
        st.markdown("**💡 4주 챌린지 참여 후, 각 문항에 대해 자신이 생각하는 정도를 선택해 주세요.** *(1점: 전혀 그렇지 않다 ~ 5점: 매우 그렇다)*")
        
        pq1 = st.slider("1. [태도] 아침 식사를 규칙적으로 하는 것은 나의 건강과 일상생활에 도움이 된다고 생각한다.", 1, 5, 3, key="post_q1")
        pq2 = st.slider("2. [주관적 규범] 가족이나 친구 등 나에게 중요한 사람들은 내가 아침 식사를 규칙적으로 하기를 바란다고 생각한다.", 1, 5, 3, key="post_q2")
        pq3 = st.slider("3. [주관적 규범] 내 주변 사람들은 아침 식사를 챙겨 먹는 행동을 긍정적으로 평가한다고 생각한다.", 1, 5, 3, key="post_q3")
        pq4 = st.slider("4. [인지된 행동 통제력] 바쁜 아침에도 5분 이내의 간편식을 활용하면 아침 식사를 챙겨 먹을 수 있다는 자신감이 있다.", 1, 5, 3, key="post_q4")
        pq5 = st.slider("5. [인지된 행동 통제력] 시간이나 비용이 부족하더라도 아침 식사를 규칙적으로 실천할 수 있다고 생각한다.", 1, 5, 3, key="post_q5")
        pq6 = st.slider("6. [행동 의도] 앞으로 2주 동안 최소 3회 이상 아침 식사를 챙겨 먹을 의향이 있다.", 1, 5, 3, key="post_q6")
        pq7 = st.slider("7. [행동 의도] 앞으로 아침 식사를 지속적인 생활 습관으로 유지하기 위해 노력할 것이다.", 1, 5, 3, key="post_q7")
        
        st.markdown("---")
        pq8 = st.number_input("8. [실제 행동] 최근 30일 동안 아침 식사를 한 날은 며칠입니까? (0일 ~ 30일)", min_value=0, max_value=30, value=0, key="post_q8")
        
        post_submit = st.form_submit_button("사후 설문 제출하고 챌린지 완주하기")
        
        if post_submit:
            if not user_name.strip():
                st.error("왼쪽 사이드바에 이름(또는 닉네임)을 먼저 입력해 주세요!")
            else:
                try:
                    _, survey_sheet = get_or_create_sheets()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    survey_sheet.append_row([
                        now_str, "사후설문(Post)", user_name.strip(), post_age,
                        pq1, pq2, pq3, pq4, pq5, pq6, pq7, pq8
                    ])
                    st.success("🎉 4주간의 챌린지와 사후 설문이 모두 완료되었습니다! 수고하셨습니다!")
                    st.balloons()
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")