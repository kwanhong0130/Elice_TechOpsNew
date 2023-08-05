# -*- coding: utf-8 -*-
import streamlit as st
import requests
import time
import pandas as pd
import json
import copy
import os
import re
import math

from urllib.parse import urlencode
from loguru import logger
from openpyxl import load_workbook
from datetime import datetime
from collections import OrderedDict
from pytz import timezone


def app():
    # Set the API endpoint URL
    base_url = "https://api-rest.elice.io"
    track_report_endpoint = "/global/organization/stats/track/report/request/"
    remote_file_endpoint = "/global/remote_file/temp/get/"
    org_id = 2252 # military23

    now_datetime = datetime.now(timezone('Asia/Seoul'))
    formatted_now_date = now_datetime.strftime("%Y%m%d_%H%M%S")

    st.markdown("""
    <style>
    div.stButton > button:first-child {
    background-color: #A961DC; color:white;
    }
    </style>""", unsafe_allow_html=True)

    course_name_map = {
        "_고급_ 웹 개발 프로젝트": "웹 개발 프로젝트 (웹 심화)",
        "_중급_ 웹 개발 프로젝트": "웹 개발 프로젝트 (데이터베이스)",
        "_초급_ 웹 개발 프로젝트": "웹 개발 프로젝트 (웹 기초)",
        "_입문_ 웹 개발 프로젝트": "웹 개발 프로젝트 (프로그래밍 언어)",
        "_고급-자연어처리_ 인공지능 프로젝트": "인공지능 프로젝트 (딥러닝-언어)",
        "_고급-이미지처리_ 인공지능 프로젝트": "인공지능 프로젝트 (딥러닝-시각)",
        "_중급_ 인공지능 프로젝트": "인공지능 프로젝트 (머신러닝)",
        "_초급_ 인공지능 프로젝트": "인공지능 프로젝트 (프로그래밍 기초)",
        "_입문_ 인공지능 프로젝트": "인공지능 프로젝트 (블록코딩)"
    }

    st.header('🪖 군인공지능 수료 현황 리포트')

    def request_track_report(endpoint, sessionkey, org_id, filter_cond={"$and":[]}):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        params = f"?organization_id={org_id}&filter_condition={filter_cond}"
        request_url = base_url+endpoint+params
        response = requests.get(request_url, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            logger.info("Request of track report success")
            # st.write("트랙 리포트 다운로드 요청이 성공하였습니다. 🥳")
            res_json = response.json()
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)
            logger.error("Request failed for some reason.")

        return res_json['download_token']

    def get_remote_file(endpoint, sessionkey, download_token):
        headers = {
            "Authorization": "Bearer " + sessionkey
        }

        params = f"?download_token={download_token}"
        request_url = base_url+endpoint+params
        response = requests.get(request_url, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            res_json = response.json()
        else:
            # Response was not successful, print the error message
            print("Error: " + response.reason)

        return res_json['url']

    def cal_track_stats(report_filename):
        track_student_stat_dict = OrderedDict()
        track_student_stat_dict = {
            "_입문_ 인공지능 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_입문_ 웹 개발 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_초급_ 인공지능 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_초급_ 웹 개발 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_중급_ 인공지능 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_중급_ 웹 개발 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_고급-이미지처리_ 인공지능 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_고급-자연어처리_ 인공지능 프로젝트": {"count": 0, "completion_count": 0, "students": []},
            "_고급_ 웹 개발 프로젝트": {"count": 0, "completion_count": 0, "students": []}
        }

        data_frame = pd.read_excel(report_filename, sheet_name=None, header=[0,1])
        sheet_names = ["_입문_ 인공지능 프로젝트", "_입문_ 웹 개발 프로젝트", "_초급_ 인공지능 프로젝트",
                       "_초급_ 웹 개발 프로젝트", "_중급_ 인공지능 프로젝트", "_중급_ 웹 개발 프로젝트",
                       "_고급-이미지처리_ 인공지능 프로젝트", "_고급-자연어처리_ 인공지능 프로젝트", "_고급_ 웹 개발 프로젝트"]

        # 입문_웹 개발 프로젝트: [웹 개발-입문] 사전 평가 / HTML/CSS / 자바스크립트 기초 / 프로젝트: 크로켓 경기 소개 페이지 만들기	/ [웹 개발-입문] 성취도 평가 / [웹 개발-입문] 설문조사
            # 과목-학습진행률 10 13 프로젝트-이수 여부 18 성취도 평가-테스트 점수 20 (0점 이상)
        # 입문_인공지능 프로젝트: [인공지능-입문] 사전 평가	/ 알아두면 쓸데 있는 컴퓨터 사이언스 / 런잇런잇 스크래치 I : 사라진 도도새와 코더랜드 친구들 / 런잇런잇 스크래치 II : 하트여왕의 성	/ 런잇런잇 스크래치 III : 집을 향한 마지막 모험 / 런잇런잇 스크래치 IV : 나만의 게임 만들기	/ 프로젝트: 스크래치를 활용한 작품 만들기 / [인공지능-입문] 성취도 평가 / [인공지능-입문] 설문조사
            # 과목-학습진행률 10 13 16 19 22 프로젝트-이수 여부 27 성취도 평가-테스트 점수 29 (0점 이상)
        # 초급_웹 개발 프로젝트: [웹 개발-초급] 사전 평가 / Express.js 기초 I / Express.js 기초 II / 프로젝트: 자기소개 기능 만들기	/ [웹 개발-초급] 성취도 평가 / [웹 개발-초급] 설문조사		
            # 과목-학습진행률 10 13 프로젝트-이수 여부 18 성취도 평가-테스트 점수 20 (0점 이상)
        # 초급_인공지능 프로젝트: [인공지능-초급] 사전 평가	/ 파이썬 기초 1	/ 파이썬 기초 2	/ 파이썬 데이터 분석 기초 / 파이썬 실전 데이터 분석	/ 프로젝트: 북한 기상 데이터 분석 및 시각화	/ 프로젝트: 날씨 변화에 따른 군 감염병 정보 EDA 분석 및 데이터 시각화 / [인공지능-초급] 성취도 평가	/ [인공지능-초급] 설문조사		
            # 과목-학습진행률 10 13 16 19 프로젝트-이수 여부 24 27 성취도 평가-테스트 점수 29 (0점 이상)
        # 중급_웹 개발 프로젝트: [웹 개발-중급] 사전 평가 / 데이터베이스 기초 / 운영체제 / 프로젝트: 게시판 기능 만들기	/ [웹 개발-중급] 성취도 평가 / [웹 개발-중급] 설문조사		
            # 과목-학습진행률 10 13 프로젝트-이수 여부 18 성취도 평가-테스트 점수 20 (0점 이상)
        # 중급_인공지능 프로젝트: [인공지능-중급] 사전 평가	/ 비전공자를 위한 머신러닝 / 머신러닝을 위한 수학 / 머신러닝 기초 / 머신러닝 심화 / 프로젝트: 기계 시설물 센서 데이터 기반 고장 예지 프로젝트 / 프로젝트: 2차 세계대전 공중폭격 및 날씨 데이터 시계열 분석을 통한 폭격 시점 예측 프로젝트 / [인공지능-중급] 성취도 평가 / [인공지능-중급] 설문조사		
            # 과목-학습진행률 10 13 16 19 프로젝트-이수 여부 24 27 성취도 평가-테스트 점수 29 (0점 이상)
        # 고급_웹 개발 프로젝트: [웹 개발-고급] 사전 평가 / 자바스크립트 심화 / 핵심 네트워크 / 프로젝트: 페이지네이션 기능 만들기 / [웹 개발-고급] 성취도 평가	/ [웹 개발-고급] 설문조사		
            # 과목-학습진행률 10 13 프로젝트-이수 여부 18 성취도 평가-테스트 점수 20 (0점 이상)
        # 고급-이미지처리: [인공지능-고급(이미지)] 사전 평가 / [고급(이미지)] 딥러닝 기초 / [고급(이미지)] CNN과 RNN 이해하기 / [고급(이미지)] CNN과 RNN 활용하기 / 이미지 처리 / 프로젝트: 위성 사진을 이용한 객체 판독 프로젝트 / 프로젝트: GPR(지표투과레이더) 데이터를 이용한 매설물 탐지 CNN 모델 개발	/ [인공지능-고급(이미지)] 성취도 평가 / [인공지능-고급(이미지)] 설문조사		
            # 과목-학습진행률 10 13 16 19 프로젝트-이수 여부 24 27 성취도 평가-테스트 점수 29 (0점 이상)
        # 고급-자연어처리: [인공지능-고급(자연어)] 사전 평가 / [고급(자연어)] 딥러닝 기초 / [고급(자연어)] CNN과 RNN 이해하기 / [고급(자연어)] CNN과 RNN 활용하기 / 자연어 처리	/ 프로젝트: 텍스트 데이터 기반 문서 분류 프로젝트 / 프로젝트: 용도별 목적대화 데이터를 활용한 화자 의도 분류 프로젝트 / [인공지능-고급(자연어)] 성취도 평가 / [인공지능-고급(자연어)] 설문조사		
            # 과목-학습진행률 10 13 16 19 프로젝트-이수 여부 24 27 성취도 평가-테스트 점수 29 (0점 이상)

        for track_name in sheet_names:
            sheet_data = data_frame[track_name]

            # proj_re = re.compile(r'프로젝트.*')
            # proj_filtered_data = sheet_data.filter(regex=proj_re, axis=1) # 프로젝트 컬럼 필터링 데이터프레임
            # logger.info(sheet_data.head())
            # logger.info(sheet_data.columns)
            # logger.info(proj_filtered_data.head())

            course_idx = []
            proj_idx = []
            comp_test_idx = []
            if track_name == "_입문_ 웹 개발 프로젝트":
                course_idx = [10, 13]
                proj_idx = [18]
                comp_test_idx = [20]
            elif track_name == "_입문_ 인공지능 프로젝트":
                course_idx = [10, 13, 16, 19, 22]
                proj_idx = [27]
                comp_test_idx = [29]
            elif track_name == "_초급_ 웹 개발 프로젝트":
                course_idx = [10, 13]
                proj_idx = [18]
                comp_test_idx = [20]
            elif track_name == "_초급_ 인공지능 프로젝트":
                course_idx = [10, 13, 16, 19]
                proj_idx = [24, 27]
                comp_test_idx = [29]
            elif track_name == "_중급_ 웹 개발 프로젝트":
                course_idx = [10, 13]
                proj_idx = [18]
                comp_test_idx = [20]
            elif track_name == "_중급_ 인공지능 프로젝트":
                course_idx = [10, 13, 16, 19]
                proj_idx = [24, 27]
                comp_test_idx = [29]
            elif track_name == "_고급_ 웹 개발 프로젝트":
                course_idx = [10, 13]
                proj_idx = [18]
                comp_test_idx = [20]
            elif track_name == "_고급-이미지처리_ 인공지능 프로젝트":
                course_idx = [10, 13, 16, 19]
                proj_idx = [24, 27]
                comp_test_idx = [29]
            elif track_name == "_고급-자연어처리_ 인공지능 프로젝트":
                course_idx = [10, 13, 16, 19]
                proj_idx = [24, 27]
                comp_test_idx = [29]
            else:
                logger.error("에러 발생")        

            for idx, row in sheet_data.iterrows():
                if row[4] == "학생" and not row[2].startswith("admin"):
                    track_student_stat_dict[track_name]['students'].append((row[1], row[2]))
                    track_student_stat_dict[track_name]['count'] += 1
                    logger.info(f"Student {row[1]}: {row[2]} is added.")
                    
                    # 과목 학습 진행률 all 80% 이상 check
                    course_all_pass = True
                    for course_prog_idx in course_idx:
                        course_progress = int(row[course_prog_idx][:-1])
                        if  course_progress < 80: course_all_pass = False
                        else: course_all_pass = True
                    
                    proj_all_pass = True
                    for proj_pass_idx in proj_idx:
                        if row[proj_pass_idx] != "O": proj_all_pass= False
                
                    comp_test_pass = True
                    for comp_test_pass_idx in comp_test_idx:
                        if row[comp_test_pass_idx] < 10: comp_test_pass = False

                    if course_all_pass and proj_all_pass and comp_test_pass: track_student_stat_dict[track_name]['completion_count'] += 1

        os.remove(report_filename)
        return track_student_stat_dict

    def _get_stats_result():
        # report_download_token = request_track_report(track_report_endpoint, api_sessionkey, org_id)
        report_download_token = request_track_report(track_report_endpoint, st.session_state['sessionkey'], org_id)
        logger.info("Download token is: " + report_download_token)

        progress_text = "요청한 리포트 파일의 생성과 다운로드를 진행중입니다. 🏄‍♂️"
        my_bar = st.progress(0, text=progress_text)

        for percent_complete in range(100):
            time.sleep(0.1)
            my_bar.progress(percent_complete + 1, text=progress_text)

        down_report_file_name = f"report_organization_{org_id}_{formatted_now_date}.xlsx"
        report_blob_url = get_remote_file(remote_file_endpoint, st.session_state['sessionkey'], report_download_token)

        if report_blob_url is not None:
            response = requests.get(report_blob_url)
            if response.status_code == 200:
                with open(down_report_file_name, "wb") as f:
                    f.write(response.content)
            else:
                print("Error: " + response.reason)
            
            alive_student_info_dict = cal_track_stats(down_report_file_name)

            track_count_list = []
            track_comp_count_list = []
            for k, v in alive_student_info_dict.items():
                track_count = v['count']
                comp_count = v['completion_count']
                # logger.info(v['students'])
                track_count_list.append(track_count)
                track_comp_count_list.append(comp_count)
                print(k, track_count)

            display_track_names = [course_name_map[sheet_name] for sheet_name in alive_student_info_dict.keys()]

            def format(f):
                p = round(f * 100, 1)
                return f'{int(p)}%' if p == int(p) else f'{p}%'

            completion_percent_list = []
            for running_count, completion_count in zip(track_count_list, track_comp_count_list):
                # percent = round(completion_count / running_count, 3) * 100
                # percent_str = str(percent)+"%"
                completion_percent_list.append(format(completion_count / running_count))

            df = pd.DataFrame({
                '과정명': display_track_names,
                '수강인원': track_count_list,
                '수료인원': track_comp_count_list,
                '수료율': completion_percent_list
                })
            
            # calcuate the sum of the second column(인원 수)
            total_sum = df['수강인원'].sum()

            total_comp_sum = df['수료인원'].sum()

            # create a new row with the sum of the second column
            new_row = pd.DataFrame({'과정명': '총 인원', '수강인원': total_sum, '수료인원': total_comp_sum}, index=[len(df)])

            # concatenate the new row to the original DataFrame
            df = pd.concat([df, new_row])

            st.write(df)
            my_bar.empty()
        else:
            st.error("에러가 발생했습니다!", icon="😵")
            logger.info("Report blob url is None. Getting track stat file failed.")
    
    st.subheader(f"2023 군인공지능 과정별 인원 현황_{formatted_now_date}")
    if st.button("결과 확인 ✅"): 
        st.session_state.disabled = True
        _get_stats_result()
    else: st.info("🔼 [결과 확인 ✅] 버튼을 눌러주세요.")