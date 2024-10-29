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
    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown(
        """
        ### Ops overview
        #### 작업이 수행하는 내용(사용자)
        목적
        - 기관에 등록된 과목들의 이수조건을 일괄적으로 업데이트.

        기존방식 1️⃣
        - 과목마다 들어가서 변경하고 싶은 설정값으로 한땀한땀 바꾼다. 👀🤚💦

        Background(Context)
        - 기관 관리자 계정
        - 동일한 설정 변경 값을 과목 전체 또는 대부분에 일괄 수정할 필요가 있거나, 그것이 더 효율적일때
        
        """
    )

    base_url = "https://api-rest.elice.io"
    org_get_endpoint = "/global/organization/get/"

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

    def certificate_edit(certi_edit_url, certi_edit_data, sessionkey):
        headers = {
            "Authorization": "Bearer " + sessionkey,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        logger.info("To POST data: " + json.dumps(certi_edit_data, indent = 1, ensure_ascii=False))

        # encoded_data = urlencode(certi_edit_data, doseq=True)

        response = requests.post(certi_edit_url, headers=headers, data=certi_edit_data)

        res_json = response.json()
        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            logger.info("Certificate edit got response")
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)
        return res_json

    def course_setting_edit_single(org_name: str, course_id: int, course_comp_data, sessionkey: str):
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
        
        def _get_certi_status(org_name, course_id, sessionkey):
            get_certi_url = f"https://api-rest.elice.io/org/{org_name}/course/certificate/get/?course_id={course_id}"
            headers = {
                "Authorization": "Bearer " + sessionkey
            }

            response = requests.get(get_certi_url, headers=headers)

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
        # temp_edit_data['attend_info'] = json.dumps(temp_edit_data['attend_info'])
        temp_edit_data['class_times'] = json.dumps(temp_edit_data['class_times'])
        temp_edit_data['objective'] = json.dumps(temp_edit_data['objective'])
        temp_edit_data['faq'] = json.dumps(temp_edit_data['faq'])
        temp_edit_data['target_audience'] = json.dumps(temp_edit_data['target_audience'])
        temp_edit_data['leaderboard_info'] = json.dumps(temp_edit_data['leaderboard_info'])
        logger.info("Coppied prev course data: " + json.dumps(temp_edit_data, indent = 1, ensure_ascii=False))

        # completion_info
        to_edit_comp_data = json.loads(temp_edit_data['completion_info'])
        to_edit_comp_data['condition']['is_enabled'] = True if course_comp_data['complete_cond'] == '자동 이수' else False
        to_edit_comp_data['condition']['score'] = course_comp_data['test_score']
        to_edit_comp_data['condition']['progress'] = course_comp_data['progress_percent']

        certificiate_info_dict = {
            'is_enabled': True,
            'template_id': '4127d141-be5d-4e41-9d66-ab304de776b2'
        }
        if 'certificate_info' not in to_edit_comp_data:
            certificiate_info_dict['is_enabled'] = course_comp_data['is_certi_issue']
            to_edit_comp_data['certificate_info'] = json.dumps(certificiate_info_dict)
        else:
            if type(to_edit_comp_data['certificate_info']) == str:
                # interim code
                # after certificate/edit post, it remains json string when cert non-initialized course
                to_edit_comp_data = json.loads(to_edit_comp_data['certificate_info'])
            certificiate_info_dict['is_enabled'] = course_comp_data['is_certi_issue']
            to_edit_comp_data['certificate_info']['is_enabled'] = course_comp_data['is_certi_issue']

        # completion_info update with course/edit
        temp_edit_data['completion_info'] = json.dumps(to_edit_comp_data)
        logger.info(to_edit_comp_data)
        logger.info(json.dumps(temp_edit_data))

        """ 
        "certificate_info": {
            "is_enabled": true,
            "template_id": "4127d141-be5d-4e41-9d66-ab304de776b2"
        }
        # 엘리스 기본 이수증 템플릿 아이디: "4127d141-be5d-4e41-9d66-ab304de776b2"
        """
        # 이수증 발급 설정 변경시에, 연속적으로 호출됨
        # https://api-rest.elice.io/org/dip/course/certificate/edit/
        # course_id: 66881
        # certificate_info: {"is_enabled":true,"template_id":"4127d141-be5d-4e41-9d66-ab304de776b2"}

        # certificate update call
        # to_post_certi_info_json_str = json.dumps(certificiate_info_dict)
        # logger.info(to_post_certi_info_json_str) # {"is_enabled": true, "template_id": "4127d141-be5d-4e41-9d66-ab304de776b2"}
        # certi_edit_info = {
        #     'course_id': course_id,
        #     'certificate_info': to_post_certi_info_json_str
        # }
        
        # certi_edit_result_json = certificate_edit(base_url+edit_certi_endpoint, certi_edit_info, sessionkey)
        # logger.info("Result of Certi edit api call: " + json.dumps(certi_edit_result_json, indent = 1, ensure_ascii=False))

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

    st.subheader('과목 이수조건 업데이트')
    st.write("#### 1️⃣ 기관에서 과목 불러오기")

    org_name = st.text_input("기관 도메인 이름을 입력해주세요. 'https://______.elice.io/", key="comp_cond_org_input")
    course_list_endpoint = f"/org/{org_name}/course/list/"
    edit_certi_endpoint = f"/org/{org_name}/course/certificate/edit/"
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
            course_comp_conditions = []
            course_comp_progress = []
            course_comp_scores = []
            course_certi_enables = []
            for course in course_infos:
                course_id_str = str(course['id'])
                course_names.append(course['title'])
                course_ids.append(course_id_str)
                course_urls.append(f'http://{org_name}.elice.io/courses/{course_id_str}/info')
                
                course_comp_info = course['completion_info']
                logger.info(course_comp_info)
                course_comp_conditions.append('자동 이수' if course_comp_info['condition']['is_enabled'] else '수동 이수')
                course_comp_progress.append(course_comp_info['condition']['progress'])
                course_comp_scores.append(course_comp_info['condition']['score'])
                if 'certificate_info' not in course_comp_info:
                    course_certi_enables.append(False)
                else:
                    if type(course_comp_info['certificate_info']) == str:
                        # interim code
                        # after certificate/edit post, it remains json string when cert non-initialized course
                        certi_info = json.loads(course_comp_info['certificate_info'])
                        course_certi_enables.append(certi_info['is_enabled'])
                    else:
                        course_certi_enables.append(course_comp_info['certificate_info']['is_enabled'])

            df = pd.DataFrame({
                '과목 명': course_names,
                '과목 ID': course_ids,
                '이수 조건': course_comp_conditions,
                '이수 학습 진행률':course_comp_progress,
                '이수 테스트 점수': course_comp_scores,
                '이수증 발급 여부': course_certi_enables,
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
    st.info('🔼 위의 과목 목록에서 이수 설정을 변경할 과목을 체크박스로 선택해주세요')

    selected_course_rows = grid_table['selected_rows']
    selected_df = pd.DataFrame(selected_course_rows)

    st.write('#### 2️⃣ 과목 선택하기(선택 과목 확인용/개별 수정 X)', selected_df)

    st.write('#### 3️⃣ 이수조건 설정하기(일괄적용)')
    is_certi_issue = False
    is_certi_issue = st.checkbox("이수증 발급(체크하면 발급) ▶️ 엘리스 이수증 기본 템플릿 고정")
    complete_cond = st.radio("이수 조건을 선택해주세요.", ('자동 이수', '수동 이수'))

    if complete_cond == '자동 이수':
        progress_percent_str = st.text_input("학습 진행률(%)", "80")
        progress_percent = int(progress_percent_str)
        test_score_str = st.text_input("총 테스트 점수(점)", "0")
        test_score = int(test_score_str)
    else:
        progress_percent_str, test_score_str = "0", "0"
        progress_percent, test_score = 0, 0
        st.info("수동 이수 처리합니다.")

    st.info(f'''🔽 이수조건 설정값은 다음과 같습니다. 
                이수증 발급: {is_certi_issue} 이수 조건: {complete_cond} 
                학습 진행률: {progress_percent_str}, 테스트 점수: {test_score_str}''')
    
    if st.button("이수조건 업데이트 🛎"):
        if selected_df.empty:
            st.error('과목이 선택되지 않았습니다. 🚫')
        else:
            progress_text = "요청한 이수조건 업데이트를 진행중입니다. 🏄‍♂️"
            my_bar = st.progress(0, text=progress_text)

            for percent_complete in range(100):
                time.sleep(0.05)
                my_bar.progress(percent_complete + 1, text=progress_text)

            for _, row in selected_df.iterrows():
                course_name = row['과목 명']
                course_id = row['과목 ID']
                course_comp_data = {
                    'is_certi_issue': is_certi_issue,
                    'complete_cond': complete_cond,
                    'progress_percent': progress_percent,
                    'test_score': test_score
                }
                edit_result_json = course_setting_edit_single(org_name, course_id, course_comp_data, st.session_state['sessionkey'])
                
                certificiate_info_dict = {
                    'is_enabled': True,
                    'template_id': '4127d141-be5d-4e41-9d66-ab304de776b2'
                }
                certificiate_info_dict['is_enabled'] = course_comp_data['is_certi_issue']

                # certificate update call
                to_post_certi_info_json_str = json.dumps(certificiate_info_dict)
                logger.info(to_post_certi_info_json_str) # {"is_enabled": true, "template_id": "4127d141-be5d-4e41-9d66-ab304de776b2"}
                certi_edit_info = {
                    'course_id': course_id,
                    'certificate_info': to_post_certi_info_json_str
                }
                
                certi_edit_result_json = certificate_edit(base_url+edit_certi_endpoint, certi_edit_info, st.session_state['sessionkey'])
                logger.info("Result of Certi edit api call: " + json.dumps(certi_edit_result_json, indent = 1, ensure_ascii=False))
                st.info(f"과목 이수조건 업데이트: {course_name}:{course_id}")
                logger.info("Result json: " + json.dumps(edit_result_json, indent = 1, ensure_ascii=False))
            my_bar.empty()
            st.success("업데이트를 완료했습니다. 🎉")                                   
    else: st.info("🔼 [이수조건 업데이트 🛎] 버튼을 눌러주세요.")