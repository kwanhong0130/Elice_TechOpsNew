import streamlit as st
import requests
import pandas as pd

from loguru import logger
from multiapp import MultiApp
from apps import intro # import your app modules here

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

# Add all your application here
app.add_app("들어가며", intro.app)
st.write("---")
# The main app
app.run()