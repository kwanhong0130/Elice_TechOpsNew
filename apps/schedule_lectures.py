import streamlit as st
import requests
import time
import pandas as pd
import json
import copy
import datetime

from urllib.parse import urlencode
from module import convert_ts_datetime
from loguru import logger
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
from st_aggrid import ColumnsAutoSizeMode

def app():
    if 'course_fetch_df' not in st.session_state:
        st.session_state['course_fetch_df'] = pd.DataFrame()

    if 'course_lecture_map' not in st.session_state:
        st.session_state['course_lecture_map'] = dict()

    if 'selected_lec_ids' not in st.session_state:
        st.session_state['selected_lec_ids'] = []

    # Set the API endpoint URL
    base_url = "https://api-rest.elice.io"
    org_get_endpoint = "/global/organization/get/" # org_id or organization_short_name required

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    st.header('🥯 수업(lecture) 공개 예약하기')

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
    
    def get_lecture_list(org_name, course_id, offset, count, sessionkey):
        get_lecture_list_url = f"https://api-rest.elice.io/org/{org_name}/lecture/list/"
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        all_lecture_list = []

        while True:
            params = f"?course_id={course_id}&offset={offset}&count={count}"
            request_url = get_lecture_list_url+params

            # Send the API request with the query parameters
            response = requests.get(request_url, headers=headers)

            # Check if the response status code is OK
            if response.status_code == 200:
                # Get the JSON data from the response
                res_json = response.json()
                # logger.info(res_json)

                # Get the paginated data from the JSON data
                paginated_data = res_json['lectures']

                # Do your manipulation on the paginated data here
                all_lecture_list.extend(paginated_data)

                # Increment the offset parameter for the next API request
                offset += count

                # Check if there are more data to fetch
                if offset >= res_json['lecture_count']:
                    break
            else:
                # Handle the API request error here
                print('API request error')
                break

        return all_lecture_list

    def lecture_edit_open(org_name: str, course_id: int, lecture_id: int, is_open: bool, sessionkey: str):
        edit_lecture_url = f"https://api-rest.elice.io/org/{org_name}/lecture/edit/"

        headers = {
            "Authorization": "Bearer " + sessionkey,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        def _get_lecture_info(org_name: str, lecture_id: int, sessionkey: str):
            get_lecture_info_url = f"https://api-rest.elice.io/org/{org_name}/lecture/get/?lecture_id={lecture_id}"
            headers = {
                "Authorization": "Bearer " + sessionkey
            }

            response = requests.get(get_lecture_info_url, headers=headers)

            # Check the response status code
            if response.status_code == 200:
                # Response was successful, print the response content
                res_json = response.json()
            else:
                # Response was not successful, print the error message
                print("Error: " + response.reason)

            return res_json
        
        global_temp_lecture_info = _get_lecture_info(st.session_state['origin_org_name'], lecture_id, sessionkey)['lecture']
        temp_edit_data = copy.deepcopy(global_temp_lecture_info)

        # required
        temp_edit_data['course_id'] = course_id
        temp_edit_data['lecture_id'] = lecture_id
        # temp_edit_data['lecture_type'] = json.dumps(temp_edit_data['lecture_type'])
        # temp_edit_data['title'] = json.dumps(temp_edit_data['title'], ensure_ascii=False)
        # temp_edit_data['description'] = json.dumps(temp_edit_data['description'])

        # required/open
        temp_edit_data['is_opened'] = is_open
        # temp_edit_data['is_preview'] = json.dumps(temp_edit_data['is_preview'])

       # https://stackoverflow.com/questions/31168819/how-to-send-an-array-using-requests-post-python-value-error-too-many-values
        logger.info("Coppied prev course data: " + json.dumps(temp_edit_data, indent = 1, ensure_ascii=False))
        response = requests.post(edit_lecture_url, headers=headers, data=temp_edit_data)

        if response.status_code == 200:
            res_json = response.json()
        else:
            print("Error: " + response.reason)
            return None

        return res_json

    def schedule_lecture(org_name, lecture_id, schedule_date_info, sessionkey):
        schedule_lecture_url = f"https://api-rest.elice.io/org/{org_name}/lecture/schedule/"

        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        schedule_info_data = {
            "lecture_id": lecture_id,
            "open_schedule_datetime": schedule_date_info['open_schedule_datetime'],
            "close_schedule_datetime": schedule_date_info['close_schedule_datetime']
        }

        response = requests.post(schedule_lecture_url, headers=headers, data=schedule_info_data)

        if response.status_code == 200:
            res_json = response.json()
        else:
            print("Error: " + response.reason)
            return None

        return res_json
    
    st.subheader('과목의 수업 공개예약 설정을 일괄 설정합니다.')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="schedule_lec_org_input")
    st.session_state['origin_org_name'] = org_name
    if st.session_state['origin_org_name']:
        st.info(f"현재 입력된 기관명: {st.session_state['origin_org_name']}")
    logger.info(f"Current org_short_name is: {st.session_state['origin_org_name']}")

    agree = st.checkbox('과목명의 필터링 ON/OFF')
    input_filter_title = ""
    if agree:
        input_filter_title = st.text_input("불러올 과목 목록의 과목명 필터링 값을 입력해주세요.", placeholder="'[5월]'과 같이 입력 후 엔터를 눌러주세요.")
        st.info(f'입력한 필터 키워드 값: {input_filter_title}')

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

    load_course_btn = st.button("과목 불러오기", key='schedule_lecture_load')
    if load_course_btn:
        if not st.session_state['origin_org_name']:
            st.warning("과목 리스트를 불러올 기관의 기관명이 입력되지 않았습니다. ⛔️")
        else:
            org_info = get_org(org_get_endpoint, st.session_state['origin_org_name'], st.session_state['sessionkey'])
            st.write(f"#### {org_info['name']} 과목 리스트")
            course_infos = get_api_data() # course/list -> ['courses']
            
            course_names = []
            course_ids = []
            course_urls = []
            origin_org_name = st.session_state['origin_org_name']
            for course in course_infos:
                lectures_in_course = get_lecture_list(st.session_state['origin_org_name'], course['id'], 
                                                      0, 10, st.session_state['sessionkey'])
                st.session_state['course_lecture_map'][str(course['id'])] = lectures_in_course
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{origin_org_name}.elice.io/courses/{course_id_str}/info')

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
    st.info('🔼 위의 과목 목록에서 수업공개 예약 일괄 처리할 과목을 체크박스로 선택해주세요')

    selected_course_rows = grid_table['selected_rows']
    selected_df = pd.DataFrame(selected_course_rows)

    st.write('#### 2️⃣ 과목 선택하기', selected_df)

    st.write('---')
    st.write('#### 3️⃣ 선택한 과목의 전체 수업 비공개 처리하기')

    if st.button("수업 일괄 비공개 🛎"): # check if no data in '변경 과목명'
        progress_text = "선택한 과목의 수업 비공개를 진행중입니다. 🏄‍♂️"
        my_bar = st.progress(0, text=progress_text)

        for percent_complete in range(100):
            time.sleep(0.025)
            my_bar.progress(percent_complete + 1, text=progress_text)

        for _, row in selected_df.iterrows():
            course_id = row['과목 ID']
            lecs_in_course = st.session_state['course_lecture_map'][course_id]
            for lec_info in lecs_in_course:
                st.session_state['selected_lec_ids'].append(lec_info['id'])
                edit_lecture_open_json = lecture_edit_open(st.session_state['origin_org_name'], course_id, 
                                                           lec_info['id'], False, st.session_state['sessionkey'])
                # st.info(f"수업 비공개 처리 업데이트: {course_name}:{course_id}")
                logger.info("Result edit lec open json: " + json.dumps(edit_lecture_open_json, indent = 1, ensure_ascii=False))

        my_bar.empty()
        st.success("수업 전체 비공개 처리를 완료했습니다.")                                
    else: st.info("🔼 [수업 일괄 비공개 🛎] 버튼을 눌러주세요.")

    st.write('---')
    st.write('#### 4️⃣ 공개 예약 일자 설정하기')

    with st.container():
        open_date_col, open_time_col = st.columns(2)
        # initializing format
        time_format = "%H:%M:%S"
        with open_date_col:
            open_d = st.date_input("게시 일시", datetime.date(2023, 1, 1)) # date of begin_datetime 
            st.write('게시 일시:', open_d)    
        with open_time_col:
            open_t = st.text_input('게시 일시의 시간', 
                                    value='00:00:00',
                                    placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
            
            # checking if format matches the date
            res = True
            # using try-except to check for truth value
            try:
                res = bool(datetime.datetime.strptime(open_t, time_format))
            except ValueError:
                res = False
            if res:
                hh_mm_ss_str_list = open_t.split(':')
                st.write('게시 일시의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))
            else:
                st.error('포맷에 맞춰 입력해주세요.')

    st.warning("🔽 게시 종료 일시 설정이 필요하면 아래 체크박스 클릭(미설정시 '미정')")
    is_end = st.checkbox("게시 종료 일시")
    if is_end:
        with st.container():
            close_date_col, close_time_col = st.columns(2)
            # initializing format
            time_format = "%H:%M:%S"
            with close_date_col:
                close_d = st.date_input("게시 종료 일시", datetime.date(2023, 1, 1)) # date of begin_datetime 
                st.write('게시 종료 일자:', close_d)    
            with close_time_col:
                close_t = st.text_input('게시 종료 일자의 시간', 
                                        value='00:00:00',
                                        placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
                
                # checking if format matches the date
                res = True
                # using try-except to check for truth value
                try:
                    res = bool(datetime.datetime.strptime(close_t, time_format))
                except ValueError:
                    res = False
                if res:
                    hh_mm_ss_str_list = close_t.split(':')
                    st.write('게시 종료 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))
                else:
                    st.error('포맷에 맞춰 입력해주세요.')                
    
    if st.button("공개예약 시간 설정하기 🛎"):
        if selected_df.empty:
            st.error('과목이 선택되지 않았습니다. 🚫')
        else:
            progress_text = "요청한 공개예약 시간 설정을 진행중입니다. 🏄‍♂️"
            my_bar = st.progress(0, text=progress_text)

            # show operation log
            for percent_complete in range(100):
                time.sleep(0.05)
                my_bar.progress(percent_complete + 1, text=progress_text)

            open_schedule_ts_datetime = convert_ts_datetime(open_d, open_t)
            # st.write(open_schedule_ts_datetime)
            close_schedule_ts_datetime = convert_ts_datetime(close_d, close_t) if is_end else None
            # st.write(close_schedule_ts_datetime)
            schedule_ts_datetime_info = {
                "open_schedule_datetime": open_schedule_ts_datetime,
                "close_schedule_datetime": close_schedule_ts_datetime
            }

            for lec_id in st.session_state['selected_lec_ids']:
                schedule_lec_reuslt_json = schedule_lecture(st.session_state['origin_org_name'], 
                                                            lec_id, 
                                                            schedule_ts_datetime_info,
                                                            st.session_state['sessionkey'])
                logger.info("Result json: " + json.dumps(schedule_lec_reuslt_json, indent = 1, ensure_ascii=False))
            my_bar.empty()
            st.success("업데이트를 완료했습니다. 🎉")
    else: st.info("🔼 [공개예약 시간 설정하기 🛎] 버튼을 눌러주세요.")