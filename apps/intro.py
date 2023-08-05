import streamlit as st
import requests
import json

from loguru import logger

def app():
    base_url = "https://api-rest.elice.io"
    auth_login_endpoint = "/global/auth/login/"

    st.markdown("""
                ### 🔽 먼저 API 세션 키 발급을 위해 아래에서 로그인을 진행해주세요.
                """)
    st.info("인증을 완료하여 세션 키를 발급받으셨다면, 위의 드롭다운에서 원하시는 메뉴를 선택해주세요")

    def get_auth_token(auth_url, post_data):
        response = requests.post(auth_url, data=post_data)
        res_json = response.json()
        logger.info(res_json)
        # Check the response status code
        if response.status_code == 200:
            # Response was successful, print the response content
            logger.info("Get auth token success")
        else:
            # Response was not successful, print the error message
            logger.error("Error: " + response.reason)
            logger.error("Auth Failed for some reason.")
        return res_json

    # Create an empty container
    placeholder = st.empty()

    # Insert a form in the container
    with placeholder.form("login"):
        st.markdown("### Enter your credentials")
        st.caption("#### API session key 획득을 위해 로그인을 합니다. (/global/auth/login/ 호출)")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Submit")

    if submit and (not email or not password):
        st.error("이메일과 비밀번호 모두 입력해주세요.")
    elif submit and email and password:
        auth_post_data = {
            "email": "testtest@elicer.com",
            "password": "password"
        }
        auth_post_data['email'] = email
        auth_post_data['password'] = password
        
        st.session_state['email'] = email

        get_auth_token_json = get_auth_token(base_url+auth_login_endpoint, auth_post_data)
        if get_auth_token_json['_result']['status'] == "ok":
            api_sessionkey = get_auth_token_json['sessionkey']
            st.success(f'''Auth 성공 🎉 
                        API Session key is: {api_sessionkey}''')
            logger.info("Sessionkey is: " + api_sessionkey)
            if 'sessionkey' not in st.session_state:
                st.session_state['sessionkey'] = api_sessionkey
        else:
            st.error("에러가 발생하였습니다. 인증 정보를 확인해주세요.")