import streamlit as st
import datetime
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# =====================================================================
# 🚨 이곳에 아까 만든 '구글 스프레드시트'의 인터넷 주소를 복사해서 넣어주세요!
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1opWmQ2UfHILLSFEBDY778hi35A5Lly10hvaw9wlpPto/edit?gid=0#gid=0"
# =====================================================================

# -----------------------------------------------------------------------------
# 0. 데이터베이스(구글 시트) 연결 설정
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

if "checkins" not in st.session_state:
    st.session_state.checkins = []

# -----------------------------------------------------------------------------
# 1. 28일(4주) 전체 추천 메뉴 리스트
# -----------------------------------------------------------------------------
RECOMMENDATIONS = [
    # 1주 차
    {"menu": "바나나 1개 + 무가당 두유", "time": "1분", "point": "불이 필요 없고 든든한 식물성 단백질 충전!"},
    {"menu": "사과 반 쪽 + 삶은 계란 1개", "time": "1분 (미리 준비)", "point": "아침 사과는 금! 식이섬유와 질 좋은 단백질의 조화."},
    {"menu": "그릭 요거트 + 한줌 견과류", "time": "1분", "point": "유산균과 건강한 지방으로 장 건강과 뇌 활력을 동시에!"},
    {"menu": "통밀빵 1쪽 + 슬라이스 치즈", "time": "2분", "point": "복합 탄수화물로 아침 혈당을 완만하게 올려줍니다."},
    {"menu": "편의점 감동란 2개 + 아몬드 브리즈", "time": "1분", "point": "바쁜 아침, 출근/등교길 편의점에서 바로 픽업하는 꿀조합!"},
    {"menu": "시리얼 한 컵 + 우유", "time": "1분", "point": "가장 클래식한 아침! 당분이 적은 시리얼을 추천해요."},
    {"menu": "오버나이트 오트밀", "time": "0분 (전날 준비)", "point": "전날 우유에 불려둔 오트밀을 꺼내 먹기만 하면 끝!"},
    
    # 2주 차
    {"menu": "전자레인지 머그컵 계란찜", "time": "3분", "point": "계란 2개와 물 약간, 전자레인지 3분이면 따뜻한 단백질 완성!"},
    {"menu": "편의점 참치마요 삼각김밥 + 따뜻한 차", "time": "1분", "point": "한국인은 밥심! 든든하게 탄수화물을 채워요."},
    {"menu": "단백질 쉐이크 + 바나나 반 개", "time": "2분", "point": "마시는 단백질로 빠르고 간편하게 포만감을 줍니다."},
    {"menu": "인스턴트 컵수프 + 모닝빵 1개", "time": "3분", "point": "따뜻한 물만 부으면 완성! 속을 편안하게 데워줍니다."},
    {"menu": "그래놀라 + 플레인 요거트", "time": "1분", "point": "바삭한 식감으로 잠든 뇌를 깨워주는 아침 식사."},
    {"menu": "고구마 1개 + 우유", "time": "1분 (미리 준비)", "point": "식이섬유가 풍부해 점심때까지 배고프지 않아요."},
    {"menu": "닭가슴살 소시지 + 방울토마토 5알", "time": "3분", "point": "전자레인지 조리로 끝내는 고단백 아침식사."},

    # 3주 차
    {"menu": "식빵 토스트 + 딸기잼 얇게", "time": "3분", "point": "토스터기만 있으면 끝! 커피와 가장 잘 어울려요."},
    {"menu": "연두부 1팩 + 오리엔탈 드레싱", "time": "1분", "point": "소화가 안 되는 아침에 가장 부드럽게 넘어가는 메뉴."},
    {"menu": "편의점 단백질 바 + 아메리카노", "time": "1분", "point": "정말 시간이 없을 때 주머니에 넣고 나갈 수 있는 비상식량!"},
    {"menu": "참치마요 카나페 (크래커 + 참치 약간)", "time": "3분", "point": "작지만 강력한 열량! 색다른 아침을 원할 때 좋아요."},
    {"menu": "냉동 블루베리 + 요거트 + 꿀 약간", "time": "2분", "point": "눈 건강에 좋은 안토시아닌과 상큼함으로 아침을 시작해요."},
    {"menu": "미숫가루(우유에 타서) + 견과류", "time": "2분", "point": "고소한 전통식 아침! 포만감이 아주 뛰어납니다."},
    {"menu": "크래미(맛살) 2개 + 스트링 치즈 1개", "time": "1분", "point": "포장만 벗기면 끝! 짭조름한 단백질 간편식."},

    # 4주 차
    {"menu": "인절미(떡) 3조각 + 두유", "time": "1분", "point": "냉동실 떡을 전자레인지에 살짝 돌려 쫄깃하게 즐겨요."},
    {"menu": "오트밀 컵죽", "time": "3분", "point": "시판 오트밀 죽에 뜨거운 물만 부으면 든든한 한 끼 완성."},
    {"menu": "냉동 볶음밥 반 공기", "time": "3분", "point": "남은 볶음밥을 소분해 두었다가 아침에 데워 먹기만 하세요."},
    {"menu": "구운 계란 2개 + 사과즙 1팩", "time": "1분", "point": "유통기한이 긴 구운 계란은 1인 가구의 든든한 동반자입니다."},
    {"menu": "냉동 만두 3개 (전자레인지 조리)", "time": "3분", "point": "전자레인지용 찜기를 활용하면 촉촉하게 수분을 채운 아침 완성!"},
    {"menu": "토마토 1개 + 올리브오일 살짝", "time": "2분", "point": "신선하고 가볍게! 비타민 흡수율을 높인 지중해식 아침."},
    {"menu": "나만의 3분 컷 최애 조합!", "time": "자유", "point": "지난 4주간 가장 맘에 들었던 메뉴를 스스로 차려보세요!"},
]

# -----------------------------------------------------------------------------
# 화면 구성 시작
# -----------------------------------------------------------------------------
st.set_page_config(page_title="나 혼자 잘 먹는다 챌린지", page_icon="🍱", layout="centered")

st.title("🍱 나 혼자 잘 먹는다: 3분 챌린지")
st.markdown("20대 1인 가구를 위한 4주 아침식사 습관 형성 프로젝트")

# --- 사이드바: 주차 및 일차 선택 ---
st.sidebar.header("🗓️ 챌린지 일정")
weeks = ["1주 차: 태도 형성", "2주 차: 주관적 규범", "3주 차: 행동 통제", "4주 차: 습관 정착"]
week = st.sidebar.radio("현재 진행 중인 주차:", weeks)

days = ["1일 차", "2일 차", "3일 차", "4일 차", "5일 차", "6일 차", "7일 차"]
day = st.sidebar.radio(f"{week[:4]} 진행 일차:", days)

week_index = weeks.index(week)
day_index = days.index(day)
total_day_index = (week_index * 7) + day_index

todays_pick = RECOMMENDATIONS[total_day_index]

st.divider()

# --- 오늘의 추천 메뉴 영역 ---
st.subheader(f"💡 {week[:4]} {day} 3분 컷 추천 메뉴")
st.info(f"**{todays_pick['menu']}** (소요 시간: {todays_pick['time']})\n\n👉 **추천 이유:** {todays_pick['point']}")

st.divider()

# --- 주차별 교육 콘텐츠 ---
st.subheader(f"📢 이번 주 심리 미션: {week}")
if week_index == 0:
    st.markdown("**[행동에 대한 태도 (Attitude)]** 아침 식사는 나를 위한 최고의 투자!\n\n아침을 챙겨 먹는 것은 귀찮은 일이 아니라, **오늘 하루 나의 집중력과 활력을 높이는 긍정적인 행동**입니다.")
elif week_index == 1:
    st.markdown("**[주관적 규범 (Subjective Norm)]** 요즘 갓생러들의 필수 루틴, 3분 아침식사!\n\n많은 20대들이 아침 굶기를 멈추고 자신만의 간편한 조식 루틴을 만들고 있습니다.")
elif week_index == 2:
    st.markdown("**[지각된 행동 통제 (Perceived Behavioral Control)]** 불 없이 3분이면 끝! 내가 완벽히 통제하는 아침\n\n'시간이 없어서'는 더 이상 핑계가 될 수 없죠? 칼도 불도 필요 없는 3분 컷 메뉴들로 완벽하게 통제하고 있습니다.")
else:
    if day_index == 6:
        st.balloons()
    st.markdown("**[행동 의도와 실천 (Intention & Behavior)]** 나만의 아침 식사 습관, 이제는 완벽한 내 일상으로!\n\n벌써 4주 차입니다. 이제 3분 아침식사는 평생을 갈 당신만의 건강한 무기입니다.")

st.divider()

# --- 데일리 체크인 폼 ---
st.subheader(f"✅ {week[:4]} {day} 인증")

with st.form(f"daily_checkin_{total_day_index}"):
    date = st.date_input("오늘 날짜", datetime.date.today())
    ate_breakfast = st.radio("오늘 아침(또는 첫 끼)을 챙겨 드셨나요?", ("네, 먹었습니다 😋", "아니요, 굶었습니다 🥲"))
    
    meal_type = st.selectbox(
        "어떤 형태로 드셨나요?", 
        ("선택 안 함 (굶음)", f"추천 메뉴: {todays_pick['menu']}", "편의점 간편식", "전자레인지 간편 조리", "어제 남은 음식", "배달 음식", "기타 (직접 요리 등)")
    )
    
    submit_btn = st.form_submit_button("오늘 하루 인증하기")
    
    if submit_btn:
        if "네" in ate_breakfast:
            if total_day_index not in st.session_state.checkins:
                st.session_state.checkins.append(total_day_index)
            st.success(f"최고예요! '{meal_type}'(으)로 든든하게 하루를 시작했군요. 오아완 성공! 🎉")
        else:
            st.error(f"앗, 아쉽네요. 내일은 꼭 '{todays_pick['menu']}'에 도전해 보세요! 💪")
        
        if total_day_index < 27:
            next_menu = RECOMMENDATIONS[total_day_index + 1]['menu']
            st.info(f"💡 **미리 보는 내일 메뉴:** 내일은 **[{next_menu}]** 입니다.")

st.divider()

# --- 나의 4주 완주 달성률 시각화 ---
st.subheader("📊 나의 4주 연속 달성률")
progress_count = len(st.session_state.checkins)
progress_rate = progress_count / 28.0

st.progress(progress_rate)
st.markdown(f"총 28일 중 **{progress_count}일** 인증 완료! (진행률: **{int(progress_rate * 100)}%**)")

# --- 7일 차 전용: 주간 회고 설문 (구글 시트로 바로 전송!) ---
if "7일 차" in day:
    st.divider()
    st.subheader(f"🏆 {week[:4]} 주간 회고 설문")
    st.markdown("이번 주 동안의 식사 습관과 생각을 되돌아보며 솔직하게 답변해 주세요.")
    
    with st.form(f"weekly_survey_{week_index}"):
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input("본인의 이름 (또는 닉네임)을 입력하세요")
        with col2:
            user_age = st.number_input("나이를 입력하세요", min_value=10, max_value=100, value=20)
            
        st.markdown("---")
        st.markdown("**💡 각 문항에 대해 자신이 생각하는 정도를 선택해 주세요.**\n*(1점: 전혀 그렇지 않다 ~ 5점: 매우 그렇다)*")
        
        # TPB 기반 8개 설문 문항
        q1 = st.slider("1. [태도] 아침 식사를 규칙적으로 하는 것은 나의 건강과 일상생활에 도움이 된다고 생각한다.", 1, 5, 3)
        q2 = st.slider("2. [주관적 규범] 가족이나 친구 등 나에게 중요한 사람들은 내가 아침 식사를 규칙적으로 하기를 바란다고 생각한다.", 1, 5, 3)
        q3 = st.slider("3. [주관적 규범] 내 주변 사람들은 아침 식사를 챙겨 먹는 행동을 긍정적으로 평가한다고 생각한다.", 1, 5, 3)
        q4 = st.slider("4. [인지된 행동 통제력] 바쁜 아침에도 5분 이내의 간편식을 활용하면 아침 식사를 챙겨 먹을 수 있다는 자신감이 있다.", 1, 5, 3)
        q5 = st.slider("5. [인지된 행동 통제력] 시간이나 비용이 부족하더라도 아침 식사를 규칙적으로 실천할 수 있다고 생각한다.", 1, 5, 3)
        q6 = st.slider("6. [행동 의도] 앞으로 2주 동안 최소 3회 이상 아침 식사를 챙겨 먹을 의향이 있다.", 1, 5, 3)
        q7 = st.slider("7. [행동 의도] 앞으로 아침 식사를 지속적인 생활 습관으로 유지하기 위해 노력할 것이다.", 1, 5, 3)
        
        st.markdown("---")
        q8 = st.number_input("8. [실제 행동] 최근 30일 동안 아침 식사를 한 날은 며칠입니까? (0일 ~ 30일)", min_value=0, max_value=30, value=0)
        
        survey_btn = st.form_submit_button("설문 제출하고 이번 주 마무리하기")
        
        if survey_btn:
            if user_name.strip() == "":
                st.error("이름을 입력해 주세요!")
            else:
                try:
                    # 1. 구글 시트 연결 가져오기
                    client = init_connection()
                    # 2. 지정한 엑셀 파일 열기 (첫 번째 시트)
                    sheet = client.open_by_url(GOOGLE_