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
    # 컬럼명 공백 제거 및 문자열 변환
    df_s.columns = [c.strip() for c in df_s.columns]
    df_a.columns = [c.strip() for c in df_a.columns]
    # 날짜 컬럼 형변환
    if not df_a.empty:
        df_a['날짜'] = pd.to_datetime(df_a['날짜']).dt.date
    return df_s, df_a

# --- 데이터 로드 ---
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

    filtered_df = df_students.copy()
    if sel_school != "전체": filtered_df = filtered_df[filtered_df['학교'] == sel_school]
    if sel_grade != "전체": filtered_df = filtered_df[filtered_df['학년'] == sel_grade]
    if sel_class != "전체": filtered_df = filtered_df[filtered_df['반이름'] == sel_class]
    if search_name: filtered_df = filtered_df[filtered_df['이름'].astype(str).str.contains(search_name, na=False)]

    st.divider()
    st.write(f"검색 결과: {len(filtered_df)} 명")
    st.dataframe(filtered_df, use_container_width=True)

# --- 2. 출석 체크 화면 ---
elif menu == "출석 체크":
    st.title("✅ 주일 예배 출석 체크")
    
    if '반이름' in df_students.columns:
        classes = sorted(df_students['반이름'].dropna().unique().tolist())
        sel_class = st.selectbox("반 선택", classes)
        
        today = datetime.now().date()
        default_sun = today + timedelta(days=(6 - today.weekday()) if today.weekday() != 6 else 0)
        check_date = st.date_input("날짜 선택", default_sun)

        existing_att = df_attendance[(df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_class)]
        class_sts = df_students[df_students['반이름'] == sel_class]
        
        with st.form("att_form"):
            st.write(f"--- {sel_class} 출석부 ({check_date}) ---")
            results = []
            for _, row in class_sts.iterrows():
                is_checked = False
                if not existing_att.empty:
                    match = existing_att[existing_att['이름'] == row['이름']]
                    if not match.empty and match.iloc[0]['출석여부'] == 1:
                        is_checked = True
                
                pres = st.checkbox(str(row['이름']), value=is_checked, key=f"att_{row['이름']}")
                results.append({'날짜': check_date, '이름': row['이름'], '반이름': sel_class, '출석여부': 1 if pres else 0})
            
            if st.form_submit_button("출석 정보 저장/수정하기"):
                new_entry_df = pd.DataFrame(results)
                other_data = df_attendance[~((df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_class))]
                updated_att = pd.concat([other_data, new_entry_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated_att)
                st.success(f"{check_date} {sel_class} 데이터가 반영되었습니다!")
                st.balloons()
    else:
        st.error("시트의 '반이름' 컬럼을 확인하세요.")

# --- 3. 출결 현황 화면 ---
elif menu == "출결 현황":
    st.title("📊 출결 현황 통계")
    
    if not df_attendance.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            all_dates = sorted(df_attendance['날짜'].unique(), reverse=True)
            sel_date = st.selectbox("📅 날짜 선택", all_dates)
        with col_f2:
            all_classes = ["전체"] + sorted(df_attendance['반이름'].unique().tolist())
            sel_class_filter = st.selectbox("🏫 반별 필터", all_classes)
        
        date_df = df_attendance[df_attendance['날짜'] == sel_date].copy()
        
        total_sts = len(date_df)
        present_sts = len(date_df[date_df['출석여부'] == 1])
        absent_sts = total_sts - present_sts
        att_rate = (present_sts / total_sts * 100) if total_sts > 0 else 0
        
        st.subheader(f"📍 {sel_date} 전체 요약")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("대상 인원", f"{total_sts}명")
        m2.metric("출석 인원", f"{present_sts}명", delta=f"-{absent_sts}명", delta_color="inverse")
        m3.metric("결석 인원", f"{absent_sts}명")
        m4.metric("출석률", f"{att_rate:.1f}%")
        
        st.divider()

        st.subheader("🏫 반별 집계 요약")
        class_summary = date_df.groupby('반이름')['출석여부'].agg(['count', 'sum']).reset_index()
        class_summary.columns = ['반이름', '대상자', '출석']
        class_summary['결석'] = class_summary['대상자'] - class_summary['출석']
        class_summary['출석률'] = (class_summary['출석'] / class_summary['대상자'] * 100).round(1).astype(str) + '%'
        
        total_row = pd.DataFrame([['합계', total_sts, present_sts, absent_sts, f"{att_rate:.1f}%"]], columns=class_summary.columns)
        class_summary_with_total = pd.concat([class_summary, total_row], ignore_index=True)
        st.table(class_summary_with_total.set_index('반이름'))

        st.divider()

        st.subheader("📄 상세 명단")
        view_df = date_df.copy()
        if sel_class_filter != "전체":
            view_df = view_df[view_df['반이름'] == sel_class_filter]
        
        view_df['상태'] = view_df['출석여부'].apply(lambda x: "✅ 출석" if x == 1 else "❌ 결석")
        st.dataframe(view_df[['이름', '반이름', '상태']].sort_values("반이름"), use_container_width=True)
    else:
        st.info("기록된 출석 데이터가 없습니다.")

# --- 4. 관리자 도구 (GitHub 링크 추가됨) ---
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
            # GitHub 주소를 아래에 입력하세요 (현재는 기본 페이지)
            st.link_button("🐙 GitHub 저장소 이동", "https://github.com/")
            
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")
