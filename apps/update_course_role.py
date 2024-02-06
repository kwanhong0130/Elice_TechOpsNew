import streamlit as st
import requests
import time
import pandas as pd
import json
import copy
import datetime

from loguru import logger
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
from st_aggrid import ColumnsAutoSizeMode

def app():
    if 'course_fetch_df' not in st.session_state:
        st.session_state['course_fetch_df'] = pd.DataFrame()

    # Set the API endpoint URL
    base_url = "https://api-rest.elice.io"

    auth_login_endpoint = "/global/auth/login/"
    org_get_endpoint = "/global/organization/get/" # org_id or organization_short_name required

    now_datetime = datetime.datetime.now()
    formatted_now_date = now_datetime.strftime("%Y%m%d_%H%M%S")

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    role_type_map = {
        0: "미등록 유저",
        45: "학생",
        50: "임시 튜터",
        60: "조교",
        90: "조교장",
        120: "선생님",
        150: "관리자"
    }

    st.header('⚒️ 과목 권한 정보 일괄 변경')

    st.markdown(
        """
        ### Ops overview
        #### 작업이 수행하는 내용(사용자)
        목적
        - 기관의 과목 세팅 작업 시, 교육기간 등의 시간 정보 일괄 세팅

        기존방식 1️⃣
        - 과목마다 들어가서 변경하고 싶은 설정값으로 한땀한땀 바꾼다. 👀🤚💦
        
        """
    )

    # https://github.com/Socvest/streamlit-pagination
    def get_org_course_list(endpoint, offset, count, sessionkey, **kwargs):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        all_course_list = []

        while True:
            # Set the query parameters for the API request
            if not kwargs['filter_title']:
                params = f"?offset={offset}&count={count}&filter_conditions={kwargs['filter_cond']}"
            else:
                params = f"?offset={offset}&count={count}&filter_conditions={kwargs['filter_cond']}&filter_title={kwargs['filter_title']}"
            request_url = base_url+endpoint+params
            # logger.info(f"Get course list: {request_url}")

            # Send the API request with the query parameters
            response = requests.get(request_url, headers=headers)

            # Check if the response status code is OK
            if response.status_code == 200:
                # Get the JSON data from the response
                res_json = response.json()

                # Get the paginated data from the JSON data
                paginated_data = res_json['courses']

                # Do your manipulation on the paginated data here
                all_course_list.extend(paginated_data)

                # Increment the offset parameter for the next API request
                offset += count

                # Check if there are more data to fetch
                if offset >= res_json['course_count']:
                    break
            else:
                # Handle the API request error here
                print('API request error')
                break

        return all_course_list

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
    
    def get_user_by_email(endpoint, email, sessionkey):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        params = f"?email={email}"
        request_url = base_url+endpoint+params
        response = requests.get(request_url, headers=headers)
        res_json = response.json()
        logger.info(res_json)
        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            logger.info("Get user success")
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)
            logger.error("Get usesr failed for some reason.")
        return res_json

    def update_course_role(org_name: str, course_id: int, user_id: int, role: int, sessionkey: str):
        # https://api-rest.elice.io/org/23ictoc-c/course/role/edit/
        course_role_edit_url = f"https://api-rest.elice.io/org/{org_name}/course/role/edit/"
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        role_edit_data = {
            "course_id": course_id,
            "user_id": user_id,
            "role": role
        }

        logger.info(json.dumps(role_edit_data, indent = 1, ensure_ascii=False))

        response = requests.post(course_role_edit_url, headers=headers, data=role_edit_data)

        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            res_json = response.json()
            logger.info(f"Request success: {json.dumps(res_json, indent = 1, ensure_ascii=False)}")
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)

        return res_json

    st.subheader('과목 수강기간 정보 업데이트')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="update_course_role_org_input")
    course_list_endpoint = f"/org/{org_name}/course/list/"
    get_user_by_email_endpoint = f"/org/{org_name}/user/get/by_email/"
    logger.info(f"Current org_short_name is: {org_name}")

    agree = st.checkbox('과목명의 필터링 ON/OFF')
    input_filter_title = ""
    if agree:
        input_filter_title = st.text_input("불러올 과목 목록의 과목명 필터링 값을 입력해주세요.", placeholder="'[5월]'과 같이 입력 후 엔터를 눌러주세요.")
        st.info(f'입력한 필터 키워드 값: {input_filter_title}')

    # @st.cache_data
    def get_api_data():
        data = get_org_course_list(course_list_endpoint, 0, 10, 
                                st.session_state['sessionkey'],
                                filter_cond={"$and": []},
                                filter_title=input_filter_title) # offset:0 count: 10

        # progress bar
        st.success("Fetched data from API!")  # 👈 Show a success message
        return data

    if st.button("과목 불러오기"):
        if not org_name:
            st.warning("과목 리스트를 불러올 기관의 기관명이 입력되지 않았습니다. ⛔️")
        else:
            org_info = get_org(org_get_endpoint, org_name, st.session_state['sessionkey'])
            st.write(f"#### {org_info['name']} 과목 리스트")
            course_infos = get_api_data() # course/list -> ['courses]

            course_names = []
            course_ids = []
            course_urls = []
            course_roles = []
            course_role_names = []
            for course in course_infos:
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{org_name}.elice.io/courses/{course_id_str}/info')
                course_roles.append(course['course_role'])
                course_role_names.append(role_type_map[course['course_role']])

            df = pd.DataFrame({
                '과목 명': course_names,
                '과목 ID': course_ids,
                '과목 권한 코드': course_roles,
                '과목 권한': course_role_names,
                '과목 URL': course_urls # https://salestest.elice.io/courses/36207/info
            })

            st.session_state['course_fetch_df'] = df
    else:
        st.info('[과목 불러오기] 버튼을 눌러서 과목을 불러옵니다.')

    gb = GridOptionsBuilder.from_dataframe(st.session_state['course_fetch_df'])
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    if not st.session_state['course_fetch_df'].empty:
        gb.configure_selection(selection_mode='multiple', use_checkbox=True)
        gb.configure_column('과목 명', headerCheckboxSelection=True)

    gridOptions = gb.build()

    # when checkbox is selected update page and button status is set to false
    grid_table = AgGrid(st.session_state['course_fetch_df'], 
                        gridOptions=gridOptions, 
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                        theme='material')

    selected_course_rows = grid_table['selected_rows']
    selected_df = pd.DataFrame(selected_course_rows)

    st.write('#### 2️⃣ 과목 선택하기', selected_df)
    st.info('🔼 위의 과목 목록에서 수강기간 정보를 변경할 과목을 체크박스로 선택해주세요')

    st.write('---')
    st.write('#### 3️⃣ 획득하려는 과목 권한을 선택해주세요.')
    reverse_dictionary = {v:k for k,v in role_type_map.items()} 
    selected_role_type = st.selectbox('과목권한을 선택해주세요.',
                                    ('미등록 유저', '학생', '임시 튜터', '조교', '조교장', '선생님', '관리자'))
    st.info(f"다음의 권한을 선택하셨습니다. ▶️ {selected_role_type}")

    if not selected_df.empty:
        selected_df['변경할 과목 권한'] = selected_role_type
        to_edit_df = selected_df[['과목 명', '과목 ID', '과목 권한', '변경할 과목 권한']]
    else: to_edit_df = pd.DataFrame()    
    edited_df = st.experimental_data_editor(to_edit_df, width=None)

    if st.button("권한 업데이트 🛎"):
        progress_text = "요청한 수강방법 업데이트를 진행중입니다. 🏄‍♂️"
        my_bar = st.progress(0, text=progress_text)

        get_user_result_json = get_user_by_email(get_user_by_email_endpoint, st.session_state['email'],
                                          st.session_state['sessionkey'])
        org_user_id = get_user_result_json['user']['id']

        for percent_complete in range(100):
            time.sleep(0.05)
            my_bar.progress(percent_complete + 1, text=progress_text)

        for _, row in edited_df.iterrows():
            course_id = row['과목 ID']
            edit_result_json = update_course_role(org_name, course_id, org_user_id, reverse_dictionary[selected_role_type],
                                                st.session_state['sessionkey'])
            logger.info(json.dumps(edit_result_json, indent = 1, ensure_ascii=False))

        my_bar.empty()
        st.success("업데이트를 완료했습니다. 🎉")                                
    else: st.info("🔼 [권한 업데이트 🛎] 버튼을 눌러주세요.")