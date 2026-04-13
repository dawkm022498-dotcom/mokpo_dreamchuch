import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 기본 설정 ---
st.set_page_config(page_title="목포꿈의교회 학생회 관리", layout="wide", page_icon="🏫")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1N3lkoOiGgCwme1zHX9URJ-0MFYagjdV4RqnwokUr0v0"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df_s = conn.read(spreadsheet=SHEET_URL, worksheet="students", ttl=0)
    df_a = conn.read(spreadsheet=SHEET_URL, worksheet="attendance", ttl=0)
    df_s.columns = [c.strip() for c in df_s.columns]
    df_a.columns = [c.strip() for c in df_a.columns]
    return df_s, df_a

# --- 사이드바 메뉴 ---
st.sidebar.title("⛪ 메뉴")
menu = st.sidebar.selectbox("이동할 화면을 선택하세요", ["출석 체크", "명단 검색", "출결 현황", "⚙️ 관리자 도구"])

# --- 데이터 로드 ---
try:
    df_students, df_attendance = load_data()
except Exception as e:
    st.error(f"데이터 로딩 오류: {e}")
    st.stop()

# --- 1. 출석 체크 화면 ---
if menu == "출석 체크":
    st.title("✅ 일요 출석 체크")
    if '반이름' in df_students.columns:
        classes = df_students['반이름'].unique().tolist()
        sel_class = st.selectbox("반 선택", classes)
        
        today = datetime.now()
        sun = today + timedelta(days=(6 - today.weekday()))
        check_date = st.date_input("날짜", sun)

        class_sts = df_students[df_students['반이름'] == sel_class]
        
        with st.form("att_form"):
            st.write(f"--- {sel_class} 명단 ---")
            results = []
            for _, row in class_sts.iterrows():
                pres = st.checkbox(str(row['이름']), key=str(row['이름']))
                results.append([str(check_date), row['이름'], sel_class, 1 if pres else 0])
            
            if st.form_submit_button("출석 저장하기"):
                new_data = pd.DataFrame(results, columns=['날짜', '이름', '반이름', '출석여부'])
                updated_att = pd.concat([df_attendance, new_data], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated_att)
                st.success("성공적으로 저장되었습니다!")
                st.balloons()
    else:
        st.error("시트 설정을 확인하세요.")

# --- 2. 명단 검색 화면 ---
elif menu == "명단 검색":
    st.title("🔍 학생 명단 검색")
    search = st.text_input("학생 이름을 입력하세요")
    if search:
        res = df_students[df_students['이름'].astype(str).str.contains(search, na=False)]
        st.dataframe(res, use_container_width=True)
    else:
        st.dataframe(df_students, use_container_width=True)

# --- 3. 출결 현황 화면 ---
elif menu == "출결 현황":
    st.title("📊 전체 출결 기록")
    if not df_attendance.empty:
        st.dataframe(df_attendance.sort_values(by="날짜", ascending=False), use_container_width=True)
    else:
        st.info("아직 기록된 출석 데이터가 없습니다.")

# --- 4. 관리자 도구 (바로가기 센터) ---
elif menu == "⚙️ 관리자 도구":
    st.title("⚙️ 관리자 제어 센터")
    st.write("관련 사이트로 바로 이동할 수 있는 도구 모음입니다.")
    
    # 간단한 비밀번호 확인 (예: 1234)
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if password == "1234": # <--- 원하는 비밀번호로 바꾸세요!
        st.success("인증되었습니다. 아래 버튼을 사용하여 관리하세요.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📂 데이터 관리")
            st.link_button("📊 구글 스프레드시트 열기 (명단 수정)", SHEET_URL)
            st.caption("학생 명단을 추가하거나 수정할 때 사용하세요.")
            
        with col2:
            st.warning("💻 시스템 관리")
            st.link_button("🐙 GitHub 저장소 (코드 수정)", "https://github.com/여러분의_아이디/저장소이름")
            st.link_button("🎈 Streamlit 대시보드 (서버 설정)", "https://share.streamlit.io/")

        st.divider()
        st.info("💡 팁: 핸드폰 바탕화면에 이 사이트를 즐겨찾기 해두면 훨씬 편합니다!")
        
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")
