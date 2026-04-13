import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="목포꿈의교회 학생회 관리", layout="wide")

# 구글 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N3lkoOiGgCwme1zHX9URJ-0MFYagjdV4RqnwokUr0v0"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 데이터를 불러오고 제목(컬럼)의 앞뒤 공백을 자동으로 제거합니다.
    df_s = conn.read(spreadsheet=SHEET_URL, worksheet="students", ttl=0)
    df_a = conn.read(spreadsheet=SHEET_URL, worksheet="attendance", ttl=0)
    df_s.columns = [c.strip() for c in df_s.columns]
    df_a.columns = [c.strip() for c in df_a.columns]
    return df_s, df_a

st.title("🏫 목포꿈의교회 학생회 관리 시스템")

try:
    df_students, df_attendance = load_data()
except Exception as e:
    st.error(f"구글 시트 연결 오류: {e}")
    st.stop()

menu = st.sidebar.selectbox("메뉴", ["출석 체크", "명단 검색", "출결 현황"])

if menu == "명단 검색":
    st.header("🔍 학생 검색")
    search = st.text_input("이름 입력")
    if search:
        # '이름' 컬럼이 있는지 확인
        if '이름' in df_students.columns:
            res = df_students[df_students['이름'].astype(str).str.contains(search, na=False)]
            st.dataframe(res)
        else:
            st.error("시트에 '이름' 이라는 제목의 칸이 없습니다. 확인해주세요.")
    else:
        st.dataframe(df_students)

elif menu == "출석 체크":
    st.header("✅ 일요 출석 체크")
    
    # 컬럼 존재 여부 확인
    if '반이름' in df_students.columns and '이름' in df_students.columns:
        classes = df_students['반이름'].unique().tolist()
        sel_class = st.selectbox("반 선택", classes)
        
        # 날짜 설정
        today = datetime.now()
        sun = today + timedelta(days=(6 - today.weekday()))
        check_date = st.date_input("날짜", sun)

        class_sts = df_students[df_students['반이름'] == sel_class]
        
        if not class_sts.empty:
            with st.form("att_form"):
                st.write(f"--- {sel_class} 명단 ---")
                results = []
                for _, row in class_sts.iterrows():
                    # 체크박스 생성
                    pres = st.checkbox(str(row['이름']), key=str(row['이름']))
                    results.append([str(check_date), row['이름'], sel_class, 1 if pres else 0])
                
                if st.form_submit_button("출석 저장하기"):
                    new_data = pd.DataFrame(results, columns=['날짜', '이름', '반이름', '출석여부'])
                    updated_att = pd.concat([df_attendance, new_data], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated_att)
                    st.success(f"{sel_class}반 출석 저장 완료!")
                    st.balloons()
        else:
            st.warning("선택한 반에 학생이 없습니다.")
    else:
        st.error("구글 시트의 첫 번째 줄(제목)을 확인해주세요. '이름'과 '반이름'이 반드시 있어야 합니다.")
        st.write("현재 인식된 제목들:", list(df_students.columns))

elif menu == "출결 현황":
    st.header("📊 통계")
    if not df_attendance.empty:
        st.dataframe(df_attendance)
    else:
        st.info("저장된 기록이 없습니다.")
