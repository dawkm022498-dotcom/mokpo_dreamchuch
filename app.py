import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="학생 관리 시스템", layout="wide")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수
def load_data():
    students = conn.read(worksheet="students")
    attendance = conn.read(worksheet="attendance")
    return students, attendance

df_students, df_attendance = load_data()

st.title("🏫 2026 학생회 관리 (구글 시트 연동)")

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
    classes = df_students['반이름'].unique().tolist()
    sel_class = st.selectbox("반 선택", classes)
    
    # 이번주 일요일 계산
    today = datetime.now()
    sun = today + timedelta(days=(6 - today.weekday()))
    check_date = st.date_input("날짜", sun)

    class_sts = df_students[df_students['반이름'] == sel_class]
    
    with st.form("att_form"):
        results = []
        for _, row in class_sts.iterrows():
            pres = st.checkbox(f"{row['이름']}", key=row['이름'])
            results.append([str(check_date), row['이름'], sel_class, 1 if pres else 0])
        
        if st.form_submit_button("저장하기"):
            # 구글 시트의 기존 데이터에 추가
            new_data = pd.DataFrame(results, columns=['날짜', '이름', '반이름', '출석여부'])
            updated_att = pd.concat([df_attendance, new_data], ignore_index=True)
            conn.update(worksheet="attendance", data=updated_att)
            st.success("구글 시트에 저장 완료!")

elif menu == "출결 현황":
    st.header("📊 통계")
    if not df_attendance.empty:
        st.write("최근 출석 기록")
        st.dataframe(df_attendance.tail(20))