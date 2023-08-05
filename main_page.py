import streamlit as st
import requests
import pandas as pd

from loguru import logger
from multiapp import MultiApp
from apps import intro, change_course_title, update_time_info, update_course_role, \
update_enroll_type, update_complete_cond, course_clone, schedule_lectures, \
deauth_users, military_report # import your app modules here

st.set_page_config(
    page_title="Elice TechOps Team Page",
    page_icon="👋"
)

st.markdown("""
<style>
div.stButton > button:first-child {
background-color: #A961DC; color:white;
}
</style>""", unsafe_allow_html=True)

st.write("# Welcome to Elice TechOps Team! 👋")

app = MultiApp()

st.markdown(
    """
    ## 엘리스 테크옵스 팀의 자동 업무 페이지입니다.

    > '과목 불러오기'를 통해 가져온 데이터는 '세션(session)'에 저장합니다.
    각 작업은 기본적으로 세션에 저장된 데이터를 가져옵니다.
    """
)

if 'course_fetch_df' not in st.session_state:
    st.session_state['course_fetch_df'] = pd.DataFrame()

if 'origin_org_name' not in st.session_state:
    st.session_state['origin_org_name'] = ""

if 'target_org_name' not in st.session_state:
    st.session_state['target_org_name'] = ""

if 'target_org_id' not in st.session_state:
    st.session_state['target_org_id'] = None

# Add all your application here
app.add_app("들어가며", intro.app)
app.add_app("1️⃣ 과목명 일괄 변경하기", change_course_title.app)
app.add_app("2️⃣ 수강기간 정보 일괄 업데이트", update_time_info.app)
app.add_app("3️⃣ 과목 권한 일괄 업데이트", update_course_role.app)
app.add_app("4️⃣ 과목 수강방법 일괄 업데이트", update_enroll_type.app)
app.add_app("5️⃣ 과목 이수조건 일괄 업데이트", update_complete_cond.app)
app.add_app("6️⃣ 과목 복제하기", course_clone.app)
app.add_app("7️⃣ 수업 공개예약 설정하기", schedule_lectures.app)
app.add_app("8️⃣ 구성원 일괄 인증 해제", deauth_users.app)
app.add_app("9️⃣ 군인공지능 수료현황 리포트", military_report.app)
st.write("---")
# The main app
app.run()