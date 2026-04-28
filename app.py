import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 기본 설정 ---
st.set_page_config(page_title="목포꿈의교회 학생회 관리", layout="wide", page_icon="🏫")

# 구글 스프레드시트 URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1N3lkoOiGgCwme1zHX9URJ-0MFYagjdV4RqnwokUr0v0"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df_s = conn.read(spreadsheet=SHEET_URL, worksheet="students", ttl=0)
    df_a = conn.read(spreadsheet=SHEET_URL, worksheet="attendance", ttl=0)
    df_s.columns = [c.strip() for c in df_s.columns]
    df_a.columns = [c.strip() for c in df_a.columns]
    if not df_a.empty:
        df_a['날짜'] = pd.to_datetime(df_a['날짜']).dt.date
    return df_s, df_a

try:
    df_students, df_attendance = load_data()
except Exception as e:
    st.error(f"데이터 로딩 오류: {e}")
    st.stop()

# --- 사이드바 메뉴 ---
st.sidebar.title("⛪ 메뉴")
menu = st.sidebar.selectbox("이동할 화면을 선택하세요", ["명단 검색", "출석 체크", "출결 현황", "⚙️ 관리자 도구"])

# --- 1. 명단 검색 화면 ---
if menu == "명단 검색":
    st.title("🔍 학생 명단 검색 및 필터")
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

    f_df = df_students.copy()
    if sel_school != "전체": f_df = f_df[f_df['학교'] == sel_school]
    if sel_grade != "전체": f_df = f_df[f_df['학년'] == sel_grade]
    if sel_class != "전체": f_df = f_df[f_df['반이름'] == sel_class]
    if search_name: f_df = f_df[f_df['이름'].astype(str).str.contains(search_name, na=False)]

    st.divider()
    st.write(f"검색 결과: {len(f_df)} 명")
    f_df.index = range(1, len(f_df) + 1)
    st.dataframe(f_df, use_container_width=True)

# --- 2. 출석 체크 화면 ---
elif menu == "출석 체크":
    st.title("✅ 주일 예배 출석 체크")
    if '반이름' in df_students.columns:
        classes = sorted(df_students['반이름'].dropna().unique().tolist())
        sel_class = st.selectbox("반 선택", classes)
        today = datetime.now().date()
        default_sun = today + timedelta(days=(6 - today.weekday()) if today.weekday() != 6 else 0)
        check_date = st.date_input("날짜 선택", default_sun)

        ex_att = df_attendance[(df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_class)]
        c_sts = df_students[df_students['반이름'] == sel_class]
        
        with st.form("att_form"):
            st.write(f"--- {sel_class} 출석부 ({check_date}) ---")
            res = []
            for i, (_, row) in enumerate(c_sts.iterrows(), 1):
                is_checked = False
                ex_note = ""
                if not ex_att.empty:
                    match = ex_att[ex_att['이름'] == row['이름']]
                    if not match.empty:
                        is_checked = True if match.iloc[0]['출석여부'] == 1 else False
                        ex_note = match.iloc[0]['비고'] if '비고' in match.columns else ""
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    pres = st.checkbox(f"{i}. {row['이름']}", value=is_checked, key=f"att_{row['이름']}")
                with c2:
                    note = st.text_input("사유", value=ex_note, key=f"note_{row['이름']}", placeholder="결석 사유 입력")
                res.append({'날짜': check_date, '이름': row['이름'], '반이름': sel_class, '출석여부': 1 if pres else 0, '비고': note})
            
            if st.form_submit_button("출석 저장하기"):
                new_df = pd.DataFrame(res)
                other = df_attendance[~((df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_class))]
                updated = pd.concat([other, new_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated)
                st.success("출석 정보가 반영되었습니다!")
                st.balloons()
    else:
        st.error("반이름 컬럼을 확인하세요.")

# --- 3. 출결 현황 화면 ---
elif menu == "출결 현황":
    st.title("📊 출결 현황 분석")
    tab1, tab2 = st.tabs(["일자별 통계", "학생별 누적 추이"])
    with tab1:
        if not df_attendance.empty:
            c_f1, c_f2 = st.columns(2)
            all_dates = sorted(df_attendance['날짜'].
