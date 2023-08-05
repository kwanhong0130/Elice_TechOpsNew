import streamlit as st
import requests
import time
import pandas as pd
import json
import copy
import datetime

from urllib.parse import urlencode
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
    org_get_endpoint = "/global/organization/get/" # org_id or organization_short_name required

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    st.header('🍪 과목(Course) 복제하기')

    # https://github.com/Socvest/streamlit-pagination
    def get_org_course_list(org_name, offset, count, sessionkey, **kwargs):
        get_course_list_url = f"https://api-rest.elice.io/org/{org_name}/course/list/"
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
            # request_url = base_url+endpoint+params
            request_url = get_course_list_url+params

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

    def clone_course(org_name: str, course_id: int, org_id: int, to_clone_course_name: str, sessionkey: str):
        clone_course_url = f"https://api-rest.elice.io/org/{org_name}/course/clone/"

        headers = {
            "Authorization": "Bearer " + sessionkey,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        post_data = {
            "course_id": course_id,
            "target_organization_id": org_id
        }

        if to_clone_course_name:
            post_data['title'] = to_clone_course_name

        logger.info(json.dumps(post_data, indent=1, ensure_ascii=False))

        response = requests.post(clone_course_url, headers=headers, data=post_data)

        res_json = response.json()
        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            logger.info("Course clone got response")
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)
        return res_json

    st.subheader('연결과목이 아닌 일반 과목을 일괄 복제합니다.(차수, 주차 등)')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="course_clone_org_input")
    st.session_state['origin_org_name'] = org_name
    st.session_state['target_org_name'] = org_name
    if st.session_state['origin_org_name']:
        st.info(f"현재 입력된 기관명: {st.session_state['origin_org_name']}")
    logger.info(f"Current org_short_name is: {st.session_state['origin_org_name']}")

    agree = st.checkbox('과목명의 필터링 ON/OFF')
    input_filter_title = ""
    if agree:
        input_filter_title = st.text_input("불러올 과목 목록의 과목명 필터링 값을 입력해주세요.", placeholder="'[5월]'과 같이 입력 후 엔터를 눌러주세요.")
        st.info(f'입력한 필터 키워드 값: {input_filter_title}')

    is_to_another_org = st.checkbox('다른 기관으로 과목 복제')
    another_org_name = ""
    if is_to_another_org:
        another_org_name = st.text_input("과목이 복제될 기관의 도메인 이름을 입력해주세요.", placeholder="'hyundai'과 같이 입력 후 엔터를 눌러주세요.")
        st.info(f'입력한 과목 복제 목적지의 기관 이름: {another_org_name}')
        st.session_state['target_org_name'] = another_org_name

    # @st.cache_data
    def get_api_data():
        data = get_org_course_list(st.session_state['origin_org_name'], 0, 10, 
                                   st.session_state['sessionkey'],
                                   filter_cond={"$and": []},
                                   filter_title=input_filter_title) # offset:0 count: 10
        logger.info("get_api_data() called")
        # progress bar
        st.success("Fetched data from API!")  # 👈 Show a success message
        return data

    load_course_btn = st.button("과목 불러오기", key='course_clone_load')
    if load_course_btn:
        if not st.session_state['origin_org_name']:
            st.warning("과목 리스트를 불러올 기관의 기관명이 입력되지 않았습니다. ⛔️")
        else:
            org_info = get_org(org_get_endpoint, st.session_state['origin_org_name'], st.session_state['sessionkey'])
            if st.session_state['target_org_name']:
                target_org_info = get_org(org_get_endpoint, st.session_state['target_org_name'], st.session_state['sessionkey'])
                st.session_state['target_org_id'] = target_org_info['id']
            else:
                st.session_state['target_org_id'] = org_info['id']
            st.write(f"#### {org_info['name']} 과목 리스트")
            course_infos = get_api_data() # course/list -> ['courses']
            
            course_names = []
            course_ids = []
            course_urls = []
            # is_origin_course = []
            origin_org_name = st.session_state['origin_org_name']
            for course in course_infos:
                # logger.info(json.dumps(course))
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{origin_org_name}.elice.io/courses/{course_id_str}/info')
                # if course['origin_course'] is None: # course/get call needed
                #     is_origin_course.append("")
                # else:
                #     is_origin_course.append(course['origin_course']['title'])

            df = pd.DataFrame({
                '과목 명': course_names,
                '과목 ID': course_ids,
                '과목 URL': course_urls # https://salestest.elice.io/courses/36207/info
            })

            st.session_state['course_fetch_df'] = df
            # st.write(st.session_state)
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
    st.info('🔼 위의 과목 목록에서 복제할 과목을 체크박스로 선택해주세요')

    selected_course_rows = grid_table['selected_rows']
    selected_df = pd.DataFrame(selected_course_rows)

    st.write('#### 2️⃣ 과목 선택하기', selected_df)

    st.write('---')
    st.write('#### 3️⃣ 복제 과목 이름 설정하기')
    st.info('🔽 변경하려는 과목명의 셀 전체를 전체 복사-붙여넣기 가능합니다.')
    st.warning('🔽 변경하려는 과목명 미입력시 기존 과목명 그대로 복제됩니다.')

    if not selected_df.empty:
        selected_df['복제 과목명'] = ""
        to_edit_df = selected_df[['과목 명', '과목 ID', '복제 과목명']]
    else: to_edit_df = pd.DataFrame()

    edited_df = st.experimental_data_editor(to_edit_df, width=None)
    if st.button("과목 복제하기 🛎"): # check if no data in '변경 과목명'
        progress_text = "요청한 과목 복제를 진행중입니다. 🏄‍♂️"
        my_bar = st.progress(0, text=progress_text)

        for percent_complete in range(100):
            time.sleep(0.05)
            my_bar.progress(percent_complete + 1, text=progress_text)

        for _, row in edited_df.iterrows():
            course_id = row['과목 ID']
            origin_course_name = row['과목 명']
            to_clone_course_name = origin_course_name if not row['복제 과목명'] else row['복제 과목명']
            clone_result = clone_course(st.session_state['origin_org_name'], course_id, st.session_state['target_org_id'], 
                                        to_clone_course_name, st.session_state['sessionkey'])
            st.info(f"과목 복제: {origin_course_name}:{course_id} -> {to_clone_course_name}")
            logger.info("Result json: " + json.dumps(clone_result, indent = 1, ensure_ascii=False))
        my_bar.empty()
        st.success("업데이트를 완료했습니다. 🎉")                                
    else: st.info("🔼 [과목 복제하기 🛎] 버튼을 눌러주세요.")