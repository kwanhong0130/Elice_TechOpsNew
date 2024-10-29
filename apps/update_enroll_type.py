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

    enroll_type_map = {
        0: "무료수강",
        1: "수강 신청",
        2: "비밀번호 입력",
        3: "계정 연결",
        4: "구독",
        5: "시스템 등록",
        6: "크레딧"
    }

    st.header('⚒️ 과목 수강방법 일괄 변경')

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

    def course_setting_edit_single(org_name: str, course_id: int, enroll_info, sessionkey: str):
        edit_course_setting_url = f"https://api-rest.elice.io/org/{org_name}/course/edit/"

        headers = {
            "Authorization": "Bearer " + sessionkey,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        def _update(json, path, new_value):
            obj_ptr = json
            for key in path:
                if key == path[-1]:
                    obj_ptr[key] = new_value
                obj_ptr = obj_ptr[key]

        def _get_course_info(org_name, course_id, sessionkey):
            get_course_info_url = f"https://api-rest.elice.io/org/{org_name}/course/get/?course_id={course_id}"
            headers = {
                "Authorization": "Bearer " + sessionkey
            }

            response = requests.get(get_course_info_url, headers=headers)

            # Check the response status code
            if response.status_code == 200:
                # Response was successful, print the response content
                res_json = response.json()
            else:
                # Response was not successful, print the error message
                print("Error: " + response.reason)

            return res_json

        global_temp_course_info = _get_course_info(org_name, course_id, sessionkey)['course']
        temp_edit_data = copy.deepcopy(global_temp_course_info)

        temp_edit_data['course_id'] = course_id
        # copy nested dict
        temp_edit_data['info_summary_visibility_dict'] = json.dumps(temp_edit_data['info_summary_visibility_dict'])
        temp_edit_data['preference'] = json.dumps(temp_edit_data['preference'])
        temp_edit_data['completion_info'] = json.dumps(temp_edit_data['completion_info'])
        temp_edit_data['attend_info'] = json.dumps(temp_edit_data['attend_info'])
        temp_edit_data['class_times'] = json.dumps(temp_edit_data['class_times'])
        temp_edit_data['objective'] = json.dumps(temp_edit_data['objective'])
        temp_edit_data['faq'] = json.dumps(temp_edit_data['faq'])
        temp_edit_data['target_audience'] = json.dumps(temp_edit_data['target_audience'])
        temp_edit_data['leaderboard_info'] = json.dumps(temp_edit_data['leaderboard_info'])

        temp_edit_data['enroll_type'] = enroll_info[0]
        if enroll_info[0] == 6:
            temp_edit_data['credit'] = enroll_info[1]

        # https://stackoverflow.com/questions/31168819/how-to-send-an-array-using-requests-post-python-value-error-too-many-values
        logger.info("Coppied prev course data: " + json.dumps(temp_edit_data, indent = 1, ensure_ascii=False))
        response = requests.post(edit_course_setting_url, headers=headers, data=temp_edit_data)

        if response.status_code == 200:
            res_json = response.json()
        else:
            print("Error: " + response.reason)
            return None

        return res_json

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

    st.subheader('과목 수강방법 업데이트')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="enroll_type_org_input")
    course_list_endpoint = f"/org/{org_name}/course/list/"
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
            course_enroll_types = []
            course_enroll_type_names = []
            for course in course_infos:
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{org_name}.elice.io/courses/{course_id_str}/info')
                course_roles.append(course['course_role'])
                course_enroll_types.append(course['enroll_type'])
                course_enroll_type_names.append(enroll_type_map[course['enroll_type']])

            df = pd.DataFrame({
                '과목 명': course_names,
                '과목 ID': course_ids,
                '과목 URL': course_urls, # https://salestest.elice.io/courses/36207/info
                '과목 권한': course_roles,
                '과목 수강방법 코드': course_enroll_types,
                '현재 수강 방법': course_enroll_type_names
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
    st.info('🔼 위의 과목 목록에서 수강기간 정보를 변경할 과목을 체크박스로 선택해주세요')

    selected_course_rows = grid_table['selected_rows']
    selected_df = pd.DataFrame(selected_course_rows)

    st.write('#### 2️⃣ 과목 선택하기', selected_df)

    st.write('---')
    st.write('#### 3️⃣ 변경하려는 수강 방법 선택하기')
    enroll_types = ('무료수강', '수강신청', '비밀번호 입력', '계정 연결', '구독', '시스템 등록', '크레딧')
    options = list(range(len(enroll_types)))
    selected_enroll_type = st.selectbox(label='수강방법을 선택해주세요.',
                                        options=options,
                                        format_func=lambda x: enroll_types[x])

    st.info(f"다음의 수강방법을 선택하셨습니다. ▶️ {enroll_type_map[selected_enroll_type]}")
    if selected_enroll_type == 6:
        st.info("크레딧을 선택하셨습니다. 아래에서 과목 별 차감 크레딧을 입력해주세요.")
        if not selected_df.empty:
            selected_df['차감 크레딧'] = ""
            selected_df['변경할 수강 방법'] = enroll_type_map[selected_enroll_type]
            to_edit_df = selected_df[['과목 명', '과목 ID', '현재 수강 방법', '변경할 수강 방법', '차감 크레딧']]
        else: to_edit_df = pd.DataFrame()
        edited_df = st.data_editor(to_edit_df, width=None)
    else:
        if not selected_df.empty:
            selected_df['변경할 수강 방법'] = enroll_type_map[selected_enroll_type]
            to_edit_df = selected_df[['과목 명', '과목 ID', '현재 수강 방법', '변경할 수강 방법']]
        else: to_edit_df = pd.DataFrame()    
        edited_df = st.data_editor(to_edit_df, width=None)

    if st.button("수강방법 업데이트 🛎"):
        if selected_enroll_type == 6:
            if (edited_df['차감 크레딧'] == '').any():
                st.warning('차감 크레딧 정보가 모두 입력되지 않았습니다. ⛔️')
            else:
                progress_text = "요청한 수강방법 업데이트를 진행중입니다. 🏄‍♂️"
                my_bar = st.progress(0, text=progress_text)

                for percent_complete in range(100):
                    time.sleep(0.05)
                    my_bar.progress(percent_complete + 1, text=progress_text)

                for _, row in edited_df.iterrows():
                    course_id = row['과목 ID']
                    enroll_info_data = (6, row['차감 크레딧'])
                    edit_result_json = course_setting_edit_single(org_name, course_id, enroll_info_data, st.session_state['sessionkey'])
                my_bar.empty()
        else:
            progress_text = "요청한 수강방법 업데이트를 진행중입니다. 🏄‍♂️"
            my_bar = st.progress(0, text=progress_text)

            for percent_complete in range(100):
                time.sleep(0.05)
                my_bar.progress(percent_complete + 1, text=progress_text)

            for _, row in edited_df.iterrows():
                course_id = row['과목 ID']
                enroll_info_data = (selected_enroll_type, None)
                edit_result_json = course_setting_edit_single(org_name, course_id, enroll_info_data, st.session_state['sessionkey'])
            my_bar.empty()
        st.success("업데이트를 완료했습니다. 🎉")                                
    else: st.info("🔼 [수강방법 업데이트 🛎] 버튼을 눌러주세요.")