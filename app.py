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
# 1. PDF 기반 9가지 핵심 레시피 및 28일(4주) 사이클 생성
# -----------------------------------------------------------------------------
BASE_RECIPES = [
    {
        "menu": "1. 오트밀 바나나 요거트볼",
        "time": "2분 (화기 불필요)",
        "point": "불이나 전자레인지 없이 재료만 섞으면 끝! 식이섬유와 유산균이 풍부한 초간편 볼.",
        "ingredients": "오트밀 1/2컵, 플레인 요거트 1컵, 바나나 1개, 견과류 한 줌, 꿀 약간",
        "steps": "1) 오트밀과 요거트를 그릇에 섞어준다.\n2) 슬라이스한 바나나를 올리고 견과류를 뿌린 후, 마지막으로 꿀을 약간 둘러준다.",
        "no_cook": True,
        "dairy_free": False
    },
    {
        "menu": "2. 오트밀 죽",
        "time": "2분 30초 (전자레인지)",
        "point": "따뜻하고 속이 편안한 한 끼! 우유 대신 물을 사용하면 유당불내증도 안심할 수 있어요.",
        "ingredients": "오트밀 1/2컵, 우유 or 물 150mL, 계란 1개, 소금 약간",
        "steps": "1) 그릇에 오트밀과 우유(또는 물)를 넣고 잘 저어준다.\n2) 계란을 깨서 넣은 뒤 노른자를 터뜨려준다.\n3) 전자레인지에 2분 먼저 돌리고 잘 섞은 뒤 30초 추가로 돌린다.",
        "no_cook": False,
        "dairy_free": True
    },
    {
        "menu": "3. 오버나이트 오트밀(숙성)",
        "time": "0분 (전날 밤 준비)",
        "point": "전날 밤 냉장고에 넣어두면 아침에 꺼내 과일만 올려 바로 먹는 0분 컷 메뉴!",
        "ingredients": "오트밀 1/2컵, 우유 100mL, 계란 1개(선택), 치아씨드 1스푼, 꿀 및 과일 토핑",
        "steps": "1) 오트밀, 우유, 치아씨드, 꿀을 섞어 밀폐용기에 담는다.\n2) 냉장고에 6시간 이상 보관한 후, 먹기 직전에 좋아하는 과일을 올려준다.",
        "no_cook": True,
        "dairy_free": False
    },
    {
        "menu": "4. 즉석밥 카레",
        "time": "3분 (전자레인지)",
        "point": "전자레인지 하나로 완성하는 든든한 한 끼! 닭가슴살이나 소세지를 얹어 단백질까지 챙기세요.",
        "ingredients": "즉석밥 1개, 고형카레 1/2개, 물 5스푼 (+ 닭가슴살 또는 소세지)",
        "steps": "1) 즉석밥을 전자레인지에 데워준다.\n2) 고형카레 1/2개를 즉석밥에 올려주고 물 5스푼을 넣어준다.\n3) 전자레인지에 2분 먼저 돌리고 잘 섞은 뒤 30초~1분 추가로 돌린다.\n4) 냉장고에 있는 닭가슴살 또는 소세지를 데워 올려 맛있게 먹는다.",
        "no_cook": False,
        "dairy_free": True
    },
    {
        "menu": "5. 캔참치밥",
        "time": "2분 (초간편 양념)",
        "point": "자취방 필수템 캔참치에 양념만 슥슥 비비면 완성되는 고단백 밥도둑!",
        "ingredients": "밥(적당량), 캔참치(1캔), 간장(1스푼), 맛소금(조금), 후추(조금), 다진 마늘(1스푼), 청양고추(약간), 참기름(1스푼), 통깨(약간)",
        "steps": "1) 캔참치를 개봉한 뒤 간장 1스푼을 넣습니다.\n2) 맛소금과 후추를 조금씩 넣습니다.\n3) 다진 마늘 1스푼과 잘게 썬 청양고추를 넣습니다.\n4) 참기름 1스푼을 넣고 통깨를 뿌립니다.\n5) 완성한 양념 참치를 준비한 밥과 함께 먹습니다.",
        "no_cook": True,
        "dairy_free": True
    },
    {
        "menu": "6. 계란볶음밥",
        "time": "5분 (팬 조리)",
        "point": "밥알을 계란으로 먼저 코팅해 고슬고슬하고 고소한 중식당 스타일 아침 볶음밥!",
        "ingredients": "햇반(1개), 계란(2개), 대파(20g), 식용유(2큰술/30mL), 굴소스(1/2큰술/7.5mL), 소금(두 꼬집)",
        "steps": "1) 햇반에 계란 1개를 넣고 섞어 밥알을 코팅합니다.\n2) 나머지 계란 1개를 풀어 달군 팬에 식용유를 두르고 스크램블에그를 만듭니다.\n3) 계란으로 코팅한 밥을 넣고 2분간 볶습니다.\n4) 굴소스 1/2큰술과 소금 두 꼬집을 넣고 1분간 더 볶습니다.\n5) 마지막으로 썬 대파 20g을 넣고 30초간 더 볶습니다.",
        "no_cook": False,
        "dairy_free": True
    },
    {
        "menu": "7. 콩나물밥 (기본 양념장)",
        "time": "7분 (냄비 조리)",
        "point": "아삭한 콩나물과 감칠맛 나는 간장 양념장의 조화! 속이 편안한 한식 아침 식사.",
        "ingredients": "콩나물(200g), 찬밥(2공기), 물(50mL), 계란프라이(선택) / 양념장: 진간장(2스푼), 국간장(1스푼), 고춧가루(1스푼), 갈은 깨(1스푼), 다진 마늘(1스푼)",
        "steps": "1) 깨끗이 씻은 콩나물 200g을 냄비에 넣습니다.\n2) 물 50mL를 넣고 찬밥 2공기를 올린 뒤 뚜껑을 덮어 김이 날 때까지 익힙니다.\n3) 김이 나면 2분 정도 더 익혀 불을 끕니다.\n4) 뚜껑을 닫은 채 1분간 뜸을 들인 후 뚜껑을 열어 밥과 콩나물을 잘 섞습니다.\n5) 기본 양념장 재료를 섞고, 원하면 계란프라이를 올린 뒤 양념장과 함께 비벼 먹습니다.",
        "no_cook": False,
        "dairy_free": True
    },
    {
        "menu": "8. 콩나물밥 (부추짜박이 양념장)",
        "time": "8분 (냄비 조리)",
        "point": "향긋한 부추와 양파가 듬뿍 들어간 특제 부추짜박이 양념장으로 비벼 먹는 별미!",
        "ingredients": "콩나물(200g), 찬밥(2공기), 물(50mL) / 부추짜박이: 부추(100g), 양파(1/2개), 청양고추(2개), 다진 마늘(1스푼), 진간장(3스푼), 국간장(1스푼), 액젓(1스푼), 매실액기스(1스푼), 갈은 깨(1스푼), 고춧가루(2스푼)",
        "steps": "1) 냄비에 콩나물 200g과 물 50mL, 찬밥을 올려 김이 날 때까지 익힌 후 2분 더 익히고 1분간 뜸을 들입니다.\n2) 부추 100g(1cm 길이), 양파 1/2개, 청양고추 2개를 잘게 다져 볼에 담습니다.\n3) 볼에 다진 마늘, 진간장, 국간장, 액젓, 매실액기스, 갈은 깨, 고춧가루를 넣고 골고루 섞어 부추짜박이를 만듭니다.\n4) 콩나물밥 위에 부추짜박이를 올리고 취향에 따라 계란프라이, 구운 김, 참기름을 곁들여 비벼 먹습니다.",
        "no_cook": False,
        "dairy_free": True
    },
    {
        "menu": "9. 계란죽",
        "time": "5분 (냄비 조리)",
        "point": "아침에 입맛이 없거나 위장이 예민할 때 부드럽게 술술 넘어가는 따뜻한 영양죽!",
        "ingredients": "계란(2개), 밥(1공기), 물(300mL), 치킨스톡(반 스푼) 또는 소금(반 스푼), 참기름(마무리용)",
        "steps": "1) 물 300mL에 밥 1공기를 넣고 잘 풀어줍니다.\n2) 한 번 잘 끓이면서 밥알을 풀어줍니다.\n3) 계란 2개를 깨 넣고 숟가락으로 잘 풀어줍니다.\n4) 치킨스톡 반 스푼으로 간합니다. (치킨스톡이 없으면 소금 반 스푼 사용)\n5) 그릇에 담고 참기름을 둘러 완성합니다.",
        "no_cook": False,
        "dairy_free": True
    }
]

# 9가지 메뉴를 28일(4주) 전체 일정에 순환 배정
RECOMMENDATIONS = [BASE_RECIPES[i % len(BASE_RECIPES)] for i in range(28)]

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
st.title("🍱 나 혼자 잘 먹는다: 간편 아침 챌린지")
st.markdown("20대 1인 가구를 위한 계획된 행동이론(TPB) 기반 4주 아침식사 습관 프로젝트")

if not user_name.strip():
    st.warning("👈 왼쪽 사이드바에서 **이름(또는 닉네임)**과 **챌린지 시작일**을 먼저 입력해 주세요! 입력하신 이름으로 출석 기록과 설문이 연동됩니다.")

tab_pre, tab_daily, tab_post = st.tabs([
    "📋 1. 사전 설문 (시작 전)",
    "🍱 2. 데일리 아침 챌린지 (1~28일)",
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
                    st.success("✅ 사전 설문이 구글 스프레드시트에 안전하게 저장되었습니다! 이제 '2. 데일리 아침 챌린지' 탭으로 이동해 주세요.")
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")

# =============================================================================
# [탭 2] 데일리 아침 챌린지 (PDF 레시피 사이클 + 상세 조리법 + 날짜 잠금)
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
    
    # 필터 조건에 맞지 않을 경우 조건에 맞는 레시피 사이클 내에서 대체 추천
    is_dairy_ok = (not filter_dairy) or todays_pick["dairy_free"]
    is_nocook_ok = (not filter_nocook) or todays_pick["no_cook"]
    
    st.subheader(f"💡 {week[:4]} {day} (전체 {selected_day_num}일 차) 추천 레시피")
    if not (is_dairy_ok and is_nocook_ok):
        filtered_pool = [
            item for item in BASE_RECIPES
            if ((not filter_dairy) or item["dairy_free"]) and ((not filter_nocook) or item["no_cook"])
        ]
        if filtered_pool:
            todays_pick = filtered_pool[total_day_index % len(filtered_pool)]
            st.warning("선택하신 필터 조건에 맞춰 레시피 사이클 내 대체 메뉴를 배정했습니다!")

    st.info(f"**{todays_pick['menu']}** (소요 시간: {todays_pick['time']})\n\n👉 **추천 포인트:** {todays_pick['point']}")
    
    with st.expander("📖 준비 재료 및 상세 조리 순서 보기", expanded=True):
        st.markdown(f"**🛒 준비 재료:**\n{todays_pick['ingredients']}")
        st.markdown(f"**👩‍🍳 조리 방법:**\n{todays_pick['steps']}")

    st.divider()

    # 2) 주차별 심리 미션
    st.subheader(f"📢 이번 주 심리 미션: {week}")
    if week_index == 0:
        st.markdown("**[행동에 대한 태도 (Attitude)]** 아침 식사는 나를 위한 최고의 투자!\n\n아침을 챙겨 먹는 것은 귀찮은 일이 아니라, **오늘 하루 나의 집중력과 활력을 높이는 긍정적인 행동**입니다.")
    elif week_index == 1:
        st.markdown("**[주관적 규범 (Subjective Norm)]** 요즘 갓생러들의 필수 루틴, 간편 아침식사!\n\n많은 20대들이 아침 굶기를 멈추고 자신만의 간편한 조식 루틴을 만들고 있습니다.")
    elif week_index == 2:
        st.markdown("**[지각된 행동 통제 (Perceived Behavioral Control)]** 전자레인지와 간단한 재료면 끝! 내가 통제하는 아침\n\n'시간이 없어서'는 더 이상 핑계가 될 수 없죠? 간단한 자취 레시피들로 완벽하게 통제하고 있습니다.")
    else:
        st.markdown("**[행동 의도와 실천 (Intention & Behavior)]** 나만의 아침 식사 습관, 이제는 완벽한 내 일상으로!\n\n벌써 4주 차입니다. 9가지 핵심 레시피를 자유자재로 활용하며 건강한 아침 루틴을 완성해 보세요.")

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
            ("선택 안 함 (굶음)", f"추천 레시피: {todays_pick['menu']}", "다른 추천 레시피 활용", "편의점 간편식", "어제 남은 음식", "기타 (직접 요리 등)"),
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

    # 4) 구글 시트 연동 실시간 달성률 시각화
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