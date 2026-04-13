import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="학생 관리 시스템", layout="wide")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 구글 시트 주소 (선생님의 시트 주소입니다)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N3lkoOiGgCwme1zHX9URJ-0MFYagjdV4RqnwokUr0v0"

# 데이터 불러오기 함수 (주소를 직접 지정하도록 수정)
def load_data():
    # spreadsheet=SHEET_URL 를 추가하여 경로를 확실히 지정합니다.
    students = conn.read(spreadsheet=SHEET_URL, worksheet="students")
    attendance = conn.read(spreadsheet=SHEET_URL, worksheet="attendance")
    return students, attendance

# 데이터 로드
try:
    df_students, df_attendance = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다. 시트 이름(students, attendance)이 정확한지 확인해주세요. 오류 내용: {e}")
    st.stop()

st.title("🏫 2026 학생회 관리 (구글 연동 완료)")

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
    # '반이름' 컬럼이 있는지 확인 후 리스트 생성
    if '반이름' in df_students.columns:
        classes = df_students['반이름'].unique().tolist()
        sel_class = st.selectbox("반 선택", classes)
    else:
