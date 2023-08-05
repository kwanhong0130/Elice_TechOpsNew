import streamlit as st
import requests
import time
import pandas as pd
import json
import copy
import os

from urllib.parse import urlencode
from loguru import logger
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
from st_aggrid import ColumnsAutoSizeMode

class ColumnNameException(Exception):
    pass

class NoColumnFieldsException(Exception):
    pass

def app():
    # Set the API endpoint URL
    base_url = "https://api-rest.elice.io"
    org_get_endpoint = "/global/organization/get/" # org_id or organization_short_name required

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    st.header('⛔️ 구성원 일괄 인증해제')

    def get_org(endpoint, org_name, sessionkey):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        params = f"?organization_name_short={org_name}"
        request_url = base_url+endpoint+params
        response = requests.get(request_url, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            res_json = response.json()
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)

        return res_json['organization']
    
    def get_user_id(org_name, email, sessionkey):
        request_url = f"https://api-rest.elice.io/org/{org_name}/user/get/by_email/"

        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        params = f"?email={email}"
        response = requests.get(request_url+params, headers=headers)
        # logger.info(response)

        if response.status_code == 200:
            res_json = response.json()
        else:
            print("Error: " + response.reason)
            return None

        return res_json['user']['id']

    def deauth_user(org_id, user_id, to_change_status, sessionkey):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }
        request_url = f"https://api-rest.elice.io/global/organization/user/edit/"
        post_data = {
            "organization_id": org_id,
            "user_id": user_id,
            "status": to_change_status
        }
        
        response = requests.post(request_url, headers=headers, data=post_data)

        if response.status_code == 200:
            res_json = response.json()
        else:
            print("Error: " + response.reason)
            return None

        return res_json

    st.write("#### 1️⃣ 기관 설정하기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="deauth_users_org_input")
    st.session_state['origin_org_name'] = org_name
    if st.session_state['origin_org_name']:
        st.info(f"현재 입력된 기관명: {st.session_state['origin_org_name']}")
        org_info = get_org(org_get_endpoint, st.session_state['origin_org_name'], st.session_state['sessionkey'])
        org_id = org_info['id']
    logger.info(f"Current org_short_name is: {st.session_state['origin_org_name']}")

    st.write('#### 2️⃣ 인증 해제 명단 파일 올리기')
    to_process_df = pd.DataFrame()
    deauth_user_ids = []

    uploaded_file = st.file_uploader(label="Upload members file to deauthorize", accept_multiple_files=False, type=['csv', 'xlsx'])
    if uploaded_file is not None:
        try:
            upload_df = pd.read_excel(uploaded_file)
            column_name_email ='이메일 *필수'
            column_name_uname = '이름 *필수'

            if not column_name_email or not column_name_uname in upload_df.columns:
                raise ColumnNameException("필수 컬럼명이 없습니다.(이메일 *필수/이름 *필수)")
            else:
                deauth_user_emails = upload_df[column_name_email]
                deauth_user_names = upload_df[column_name_uname]
            
                #check empty
                if deauth_user_emails.empty or deauth_user_names.empty:
                    raise NoColumnFieldsException("인증 해제 명단에 값이 없습니다. 명단을 다시 확인해주세요. ⛔️")

                for user_email in deauth_user_emails:
                    deauth_user_ids.append(str(get_user_id(st.session_state['origin_org_name'], user_email, st.session_state['sessionkey'])))

            to_process_df['이름'] = deauth_user_names
            to_process_df['이메일'] = deauth_user_emails
            to_process_df['유저 ID'] = deauth_user_ids
        except Exception as e:
            st.error(e)
            logger.error(e)
    # list validation check

    st.info('🔽 인증 해제하려는 구성원 명단')
    st.write(to_process_df)

    st.info("🪄 명단의 이메일을 기준으로 인증을 해제합니다.")
    if st.button("구성원 일괄 인증 해제 🛎"):
        if not org_name:
            st.error('기관이 선택되지 않았습니다. 🚫')
        else:    
            progress_text = "업로드한 명단을 기준으로 인증 해제중입니다. 🏂"
            my_bar = st.progress(0, text=progress_text)

            for percent_complete in range(100):
                time.sleep(0.025)
                my_bar.progress(percent_complete + 1, text=progress_text)

            for _, row in to_process_df.iterrows():
                deauth_user_result_json = deauth_user(org_id, row['유저 ID'], 0, st.session_state['sessionkey'])
                logger.info("Result json: " + json.dumps(deauth_user_result_json, indent = 1, ensure_ascii=False))
                
                if deauth_user_result_json['_result']['status'] == "ok":
                    st.success(f"인증해제를 완료했습니다. \
                               {row['이름']}: {row['이메일']}")
                else:
                    st.error(f"인증해제에 실패했습니다. \
                               {row['이름']}: {row['이메일']}")