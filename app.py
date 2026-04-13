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
    # 컬럼명 공백 제거 및 문자열 변환
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
    st.title("✅ 주일 예배 출석 체크")
    if '반이름' in df_students.columns:
        classes = sorted(df_students['반이름'].dropna().unique().tolist())
        sel_class = st.selectbox("반 선택", classes)
        
        today = datetime.now()
        # 이번주 주일 날짜 계산 (오늘이 월~토면 이번주 주일, 오늘이 주일이면 오늘)
        sun = today + timedelta(days=(6 - today.weekday()))
        check_date = st.date_input("날짜", sun)

        class_sts = df_students[df_students['반이름'] == sel_class]
        
        with st.form("att_form"):
            st.write(f"--- {sel_class} 명단 ---")
            results = []
            for _, row in class_sts.iterrows():
                pres = st.checkbox(str(row['이름']), key=f"att_{row['이름']}")
                results.append([str(check_date), row['이름'], sel_class, 1 if pres else 0])
            
            if st.form_submit_button("출석 저장하기"):
                new_data = pd.DataFrame(results, columns=['날짜', '이름', '반이름', '출석여부'])
                updated_att = pd.concat([df_attendance, new_data], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated_att)
                st.success("성공적으로 저장되었습니다!")
                st.balloons()
    else:
        st.error("시트의 '반이름' 컬럼을 확인하세요.")

# --- 2. 명단 검색 화면 (필터 기능 강화) ---
elif menu == "명단 검색":
    st.title("🔍 학생 명단 검색 및 필터")
    
    # 필터 레이아웃 구성
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        schools = ["전체"] + sorted(df_students['학교'].dropna().unique().tolist()) if '학교' in df_students.columns else ["전체"]
        sel_school = st.selectbox("학교 필터", schools)
        
    with col2:
        grades = ["전체"] + sorted(df_students['학년'].dropna().unique().tolist()) if '학년' in df_students.columns else ["전체"]
        sel_grade = st.selectbox("학년 필터", grades)
        
    with col3:
        classes = ["전체"] + sorted(df_students['반이름'].dropna().unique().tolist()) if '반이름' in df_students.columns else ["전체"]
        sel_class = st.selectbox("반 필터", classes)
        
    with col4:
        search_name = st.text_input("이름 검색", "")

    # 데이터 필터링 로직
    filtered_df = df_students.copy()
    
    if sel_school != "전체":
        filtered_df = filtered_df[filtered_df['학교'] == sel_school]
    if sel_grade != "전체":
        filtered_df = filtered_df[filtered_df['학년'] == sel_grade]
    if sel_class != "전체":
        filtered_df = filtered_df[filtered_df['반이름'] == sel_class]
    if search_name:
        filtered_df = filtered_df[filtered_df['이름'].astype(str).str.contains(search_name, na=False)]

    st.divider()
    st.write(f"검색 결과: {len(filtered_df)} 명")
    st.dataframe(filtered_df, use_container_width=True)

# --- 3. 출결 현황 화면 ---
elif menu == "출결 현황":
    st.title("📊 전체 출결 기록")
    if not df_attendance.empty:
        # 날짜순 정렬
        st.dataframe(df_attendance.sort_values(by="날짜", ascending=False), use_container_width=True)
    else:
        st.info("아직 기록된 출석 데이터가 없습니다.")

# --- 4. 관리자 도구 ---
elif menu == "⚙️ 관리자 도구":
    st.title("⚙️ 관리자 제어 센터")
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if password == "0498":
        st.success("인증되었습니다.")
        col1, col2 = st.columns(2)
        with col1:
            st.info("📂 데이터 관리")
            st.link_button("📊 구글 스프레드시트 열기", SHEET_URL)
        with col2:
            st.warning("💻 시스템 관리")
            st.link_button("🎈 Streamlit 대시보드", "https://share.streamlit.io/")
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")
