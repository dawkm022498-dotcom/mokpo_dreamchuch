import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="학생 관리 시스템", layout="wide")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 구글 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N3lkoOiGgCwme1zHX9URJ-0MFYagjdV4RqnwokUr0v0"

# 데이터 불러오기 함수
def load_data():
    students = conn.read(spreadsheet=SHEET_URL, worksheet="students")
    attendance = conn.read(spreadsheet=SHEET_URL, worksheet="attendance")
    return students, attendance

# 데이터 로드 시도
try:
    df_students, df_attendance = load_data()
except Exception as e:
    st.error(f"데이터 로딩 실패: {e}")
    st.stop()

st.title("🏫 목포꿈의교회 학생회 관리 시스템")

menu = st.sidebar.selectbox("메뉴", ["명단 검색", "출석 체크", "출결 현황"])

if menu == "명단 검색":
    st.header("🔍 학생 검색")
    search = st.text_input("이름 입력")
    if search:
        res = df_students[df_students['이름'].str.contains(search, na=False)]
        st.dataframe(res)
    else:
        st.dataframe(df_students)

elif menu == "출석 체크":
    st.header("✅ 일요 출석 체크")
