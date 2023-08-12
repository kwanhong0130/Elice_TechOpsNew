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
    org_get_endpoint = "/global/organization/get/" # org_id or organization_short_name required

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    st.header('⚒️ 과목 시간 정보 일괄 변경')

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

    def course_setting_edit_single(org_name: str, course_id: int, to_change_datetime, sessionkey: str):
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

        # course_time
        # TODO: to_change_datetime tuple to namedtuple
        temp_edit_data['begin_datetime'] = to_change_datetime[0]
        temp_edit_data['end_datetime'] = to_change_datetime[1]
        if len(to_change_datetime) > 4:
            temp_edit_data['complete_datetime'] = to_change_datetime[2] 
            temp_edit_data['enroll_begin_datetime'] = to_change_datetime[3]
            temp_edit_data['enroll_end_datetime'] = to_change_datetime[4]
        else:
            del temp_edit_data['complete_datetime']
            temp_edit_data['enroll_begin_datetime'] = to_change_datetime[2]
            temp_edit_data['enroll_end_datetime'] = to_change_datetime[3]

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

    st.subheader('과목 수강기간 정보 업데이트')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="change_time_org_input")
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
            # course_roles = []
            # course_enroll_types = []
            # course_enroll_type_names = []
            for course in course_infos:
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{org_name}.elice.io/courses/{course_id_str}/info')
                # course_roles.append(course['course_role'])
                # course_enroll_types.append(course['enroll_type'])
                # course_enroll_type_names.append(enroll_type_map[course['enroll_type']])

            df = pd.DataFrame({
                '과목 명': course_names,
                '과목 ID': course_ids,
                '과목 URL': course_urls # https://salestest.elice.io/courses/36207/info
                # '과목 권한': course_roles,
                # '과목 수강방법 코드': course_enroll_types,
                # '현재 수강 방법': course_enroll_type_names
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
    st.write('#### 3️⃣ 변경하려는 수강기간 정보(To-Update) 입력하기')
    with st.container():
        begin_date_col, begin_time_col = st.columns(2)
        # initializing format
        time_format = "%H:%M:%S"
        with begin_date_col:
            begin_d = st.date_input("교육기간 시작 일자", datetime.date(2023, 1, 1)) # date of begin_datetime 
            st.write('교육기간 시작 일자:', begin_d)    
        with begin_time_col:
            begin_t = st.text_input('교육기간 시작 일자의 시간', 
                                    value='00:00:00',
                                    placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
            
            # checking if format matches the date
            res = True
            # using try-except to check for truth value
            try:
                res = bool(datetime.datetime.strptime(begin_t, time_format))
            except ValueError:
                res = False
            if res:
                hh_mm_ss_str_list = begin_t.split(':')
                st.write('교육기간 시작 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))
            else:
                st.error('포맷에 맞춰 입력해주세요.')

        end_date_col, end_time_col = st.columns(2)
        with end_date_col:
            end_d = st.date_input("교육기간 종료 일자", datetime.date(2023, 1, 1)) # date of end_datetime 
            st.write('교육기간 종료 일자:', end_d)    
        with end_time_col:
            end_t = st.text_input('교육기간 종료 일자의 시간', 
                                value='23:59:59',
                                placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
            # checking if format matches the date
            res_sec = True
            # using try-except to check for truth value
            try:
                res_sec = bool(datetime.datetime.strptime(end_t, time_format))
            except ValueError:
                res_sec = False
            if res_sec:
                hh_mm_ss_str_list = end_t.split(':')
                st.write('교육기간 종료 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))
            else:
                st.error('포맷에 맞춰 입력해주세요.')

    # 추가 교육 기간 '상시' optional 반영
    is_comp_date_avail = st.checkbox('추가 교육기간 설정 ON/OFF')
    st.info("추가 교육기간 설정 체크박스를 OFF할 시, '종료일 없음(상시)'로 변경합니다.")
    complete_d, complete_t = None, None
    if is_comp_date_avail:
        comp_date_col, comp_time_col = st.columns(2)
        with comp_date_col:
            complete_d = st.date_input("추가 교육기간 종료 일자", datetime.date(2023, 1, 1)) # date of complete_datetime
            st.write('추가 교육기간 종료 일자:', complete_d)
        with comp_time_col:
            complete_t = st.text_input('추가 교육기간 종료 일자의 시간', 
                                    value='23:59:59',
                                    placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
            hh_mm_ss_str_list = complete_t.split(':')
            st.write('추가 교육기간 종료 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))

    enroll_begin_date_col, enroll_begin_time_col = st.columns(2)
    with enroll_begin_date_col:
        enroll_begin_d = st.date_input("수강 신청기간 시작 일자", datetime.date(2023, 1, 1)) # date of enroll_begin_datetime
        st.write('수강 신청기간 시작 일자:', enroll_begin_d)
    with enroll_begin_time_col:
        enroll_begin_t = st.text_input('수강 신청기간 시작 일자의 시간', 
                                value='00:00:00',
                                placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
        hh_mm_ss_str_list = enroll_begin_t.split(':')
        st.write('수강 신청기간 시작 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))

    enroll_end_date_col, enroll_end_time_col = st.columns(2)
    with enroll_end_date_col:
        enroll_end_d = st.date_input("수강 신청기간 종료 일자", datetime.date(2023, 1, 1)) # date of enroll_end_datetime
        st.write('수강 신청기간 종료 일자:', enroll_end_d)  
    with enroll_end_time_col:
        enroll_end_t = st.text_input('수강 신청기간 종료 일자의 시간', 
                                value='23:59:59',
                                placeholder='hh:mm:ss(00:00:00) 형태로 입력해주세요.')
        hh_mm_ss_str_list = enroll_end_t.split(':')
        st.write('수강 신청기간 종료 일자의 시간', datetime.time(int(hh_mm_ss_str_list[0]), int(hh_mm_ss_str_list[1]), int(hh_mm_ss_str_list[2])))


    # convert begin/end datetime
    to_update_datatime = (begin_d, begin_t, end_d, end_t)
    logger.info(to_update_datatime)

    begin_y_str = datetime.datetime.strftime(to_update_datatime[0], '%Y')
    begin_m_str = datetime.datetime.strftime(to_update_datatime[0], '%m')
    begin_d_str = datetime.datetime.strftime(to_update_datatime[0], '%d')

    to_change_begin_date_str = begin_y_str+'/'+begin_m_str+'/'+begin_d_str
    to_change_begin_datetime_str = to_change_begin_date_str + ' ' + begin_t
    logger.info("Begin datetime: " + to_change_begin_datetime_str)

    date_format = '%Y/%m/%d %H:%M:%S'

    # Convert date string to datetime object in GMT+9 timezone
    begin_datetime_obj = datetime.datetime.strptime(to_change_begin_datetime_str, date_format).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

    # Convert datetime object to Unix timestamp in milliseconds
    to_change_begin_ts_datetime = int(begin_datetime_obj.timestamp() * 1000)
    logger.info("Begin datetime timestamp " + str(to_change_begin_ts_datetime))

    end_y_str = datetime.datetime.strftime(to_update_datatime[2], '%Y')
    end_m_str = datetime.datetime.strftime(to_update_datatime[2], '%m')
    end_d_str = datetime.datetime.strftime(to_update_datatime[2], '%d')

    to_change_end_date_str = end_y_str+'/'+end_m_str+'/'+end_d_str
    to_change_end_datetime_str = to_change_end_date_str + ' ' + end_t
    logger.info("End datetime: " + to_change_end_datetime_str)

    # Convert date string to datetime object in GMT+9 timezone
    end_datetime_obj = datetime.datetime.strptime(to_change_end_datetime_str, date_format).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

    # Convert datetime object to Unix timestamp in milliseconds
    to_change_end_ts_datetime = int(end_datetime_obj.timestamp() * 1000)
    logger.info("Begin datetime timestamp " + str(to_change_end_ts_datetime))

    # to_change_end_datetime = math.trunc(time.mktime(datetime.datetime.strptime(to_change_end_datetime_str, '%Y/%m/%d %H:%M:%S').timetuple()))
    logger.info("End datetime timestamp " + str(to_change_end_ts_datetime))

    to_change_ts_str = (str(to_change_begin_ts_datetime), str(to_change_end_ts_datetime))

    # convert complete datetime
    to_change_complete_datetime_str = None
    to_change_complete_ts_datetime = None
    if complete_t is not None and complete_d is not None:
        to_update_complete_datatime = (complete_d, complete_t)
        logger.info(to_update_complete_datatime)

        complete_y_str = datetime.datetime.strftime(to_update_complete_datatime[0], '%Y')
        complete_m_str = datetime.datetime.strftime(to_update_complete_datatime[0], '%m')
        complete_d_str = datetime.datetime.strftime(to_update_complete_datatime[0], '%d')

        to_change_complete_date_str = complete_y_str+'/'+complete_m_str+'/'+complete_d_str
        to_change_complete_datetime_str = to_change_complete_date_str + ' ' + complete_t
        logger.info("Complete datetime: " + to_change_complete_datetime_str)

        # Convert date string to datetime object in GMT+9 timezone
        complete_datetime_obj = datetime.datetime.strptime(to_change_complete_datetime_str, date_format).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

        # Convert datetime object to Unix timestamp in milliseconds
        to_change_complete_ts_datetime = int(complete_datetime_obj.timestamp() * 1000)
        logger.info("Complete datetime timestamp " + str(to_change_complete_ts_datetime))

    # convert enroll begin/end datetime
    to_update_enroll_datatime = (enroll_begin_d, enroll_begin_t, enroll_end_d, enroll_end_t)
    logger.info(to_update_enroll_datatime)

    enroll_begin_y_str = datetime.datetime.strftime(to_update_enroll_datatime[0], '%Y')
    enroll_begin_m_str = datetime.datetime.strftime(to_update_enroll_datatime[0], '%m')
    enroll_begin_d_str = datetime.datetime.strftime(to_update_enroll_datatime[0], '%d')

    to_change_enroll_begin_date_str = enroll_begin_y_str+'/'+enroll_begin_m_str+'/'+enroll_begin_d_str
    to_change_enroll_begin_datetime_str = to_change_enroll_begin_date_str + ' ' + enroll_begin_t
    logger.info("Enroll begin datetime: " + to_change_enroll_begin_datetime_str)

    # Convert date string to datetime object in GMT+9 timezone
    enroll_begin_datetime_obj = datetime.datetime.strptime(to_change_enroll_begin_datetime_str, date_format).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

    # Convert datetime object to Unix timestamp in milliseconds
    to_change_enroll_begin_ts_datetime = int(enroll_begin_datetime_obj.timestamp() * 1000)
    logger.info("Enroll begin datetime timestamp " + str(to_change_enroll_begin_ts_datetime))

    enroll_end_y_str = datetime.datetime.strftime(to_update_enroll_datatime[2], '%Y')
    enroll_end_m_str = datetime.datetime.strftime(to_update_enroll_datatime[2], '%m')
    enroll_end_d_str = datetime.datetime.strftime(to_update_enroll_datatime[2], '%d')

    to_change_enroll_end_date_str = enroll_end_y_str+'/'+enroll_end_m_str+'/'+enroll_end_d_str
    to_change_enroll_end_datetime_str = to_change_enroll_end_date_str + ' ' + enroll_end_t
    logger.info("Enroll end datetime: " + to_change_enroll_end_datetime_str)

    # Convert date string to datetime object in GMT+9 timezone
    enroll_end_datetime_obj = datetime.datetime.strptime(to_change_enroll_end_datetime_str, date_format).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

    # Convert datetime object to Unix timestamp in milliseconds
    to_change_enroll_end_ts_datetime = int(enroll_end_datetime_obj.timestamp() * 1000)
    logger.info("Enroll end datetime timestamp " + str(to_change_enroll_end_ts_datetime))

    to_change_enroll_ts_str = (str(to_change_enroll_begin_ts_datetime), str(to_change_enroll_end_ts_datetime))

    # final value to update
    st.write("#### 🔽 업데이트 할 시간정보는 다음과 같습니다. 값을 확인해주세요")
    st.info("과목 교육 기간 시작일: " + to_change_begin_datetime_str)
    st.info("과목 교육 기간 종료일: " + to_change_end_datetime_str)
    if to_change_complete_datetime_str:
        st.info("과목 추가 교육 기간 종료일: " + to_change_complete_datetime_str)
    st.info("과목 수강신청 기간 시작일: " + to_change_enroll_begin_datetime_str)
    st.info("과목 수강신청 기간 종료일: " + to_change_enroll_end_datetime_str)

    logger.info("업데이트 하려는 교육 기간 정보(YYYY-MM-DD hh:mm:ss): " + to_change_begin_datetime_str + " / " +  to_change_end_datetime_str)
    logger.info("업데이트 하려는 교육 기간 정보(timestamp): " + ' '.join(to_change_ts_str))
    logger.info("업데이트 하려는 수강신청 기간 정보(YYYY-MM-DD hh:mm:ss): " + to_change_enroll_begin_datetime_str + " / " +  to_change_enroll_end_datetime_str)
    logger.info("업데이트 하려는 수강신청 기간 정보(timestamp): " + ' '.join(to_change_enroll_ts_str))

    if to_change_complete_ts_datetime:
        to_chanage_datetimes = (to_change_begin_ts_datetime, to_change_end_ts_datetime, 
                                to_change_complete_ts_datetime,
                                to_change_enroll_begin_ts_datetime, to_change_enroll_end_ts_datetime) # final update datetime info
    else:
        to_chanage_datetimes = (to_change_begin_ts_datetime, to_change_end_ts_datetime,
                                to_change_enroll_begin_ts_datetime, to_change_enroll_end_ts_datetime) # final update datetime info
        

    st.write('---')

    if st.button("시간정보 바꾸기 🛎"):
        if selected_df.empty:
            st.error('과목이 선택되지 않았습니다. 🚫')
        else:
            progress_text = "요청한 시간정보 변경을 진행중입니다. 🏄‍♂️"
            my_bar = st.progress(0, text=progress_text)
            logger.info(len(selected_df.index))

            # show operation log
            for percent_complete in range(100):
                time.sleep(0.05)
                my_bar.progress(percent_complete + 1, text=progress_text)

            for _, row in selected_df.iterrows():
                course_name = row['과목 명']
                course_id = row['과목 ID']
                # st.info(f"{course_name} 변경 중...🏏")
                edit_result_json = course_setting_edit_single(org_name, course_id, to_chanage_datetimes, st.session_state['sessionkey'])
                st.info(f"과목 시간정보 업데이트: {course_name}:{course_id}")
                logger.info("Result json: " + json.dumps(edit_result_json, indent = 1, ensure_ascii=False))
            my_bar.empty()
            st.success("업데이트를 완료했습니다. 🎉")
    else: st.info("🔼 [시간정보 바꾸기 🛎] 버튼을 눌러주세요.")