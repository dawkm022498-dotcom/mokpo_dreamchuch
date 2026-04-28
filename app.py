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

    filtered_df = df_students.copy()
    if sel_school != "전체": filtered_df = filtered_df[filtered_df['학교'] == sel_school]
    if sel_grade != "전체": filtered_df = filtered_df[filtered_df['학년'] == sel_grade]
    if sel_class != "전체": filtered_df = filtered_df[filtered_df['반이름'] == sel_class]
    if search_name: filtered_df = filtered_df[filtered_df['이름'].astype(str).str.contains(search_name, na=False)]

    st.divider()
    st.write(f"검색 결과: {len(filtered_df)} 명")
    st.dataframe(filtered_df, use_container_width=True)

# --- 2. 출석 체크 화면 (결석 사유 추가) ---
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
                existing_note = ""
                if not existing_att.empty:
                    match = existing_att[existing_att['이름'] == row['이름']]
                    if not match.empty:
                        is_checked = True if match.iloc[0]['출석여부'] == 1 else False
                        existing_note = match.iloc[0]['비고'] if '비고' in match.columns else ""
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    pres = st.checkbox(str(row['이름']), value=is_checked, key=f"att_{row['이름']}")
                with c2:
                    # 결석일 때만 사유를 적도록 유도하거나, 모든 학생에게 비고란 제공
                    note = st.text_input("사유/비고", value=existing_note, key=f"note_{row['이름']}", placeholder="결석 사유 등")
                
                results.append({'날짜': check_date, '이름': row['이름'], '반이름': sel_class, '출석여부': 1 if pres else 0, '비고': note})
            
            if st.form_submit_button("출석 정보 저장/수정하기"):
                new_entry_df = pd.DataFrame(results)
                other_data = df_attendance[~((df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_class))]
                updated_att = pd.concat([other_data, new_entry_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=updated_att)
                st.success(f"{check_date} {sel_class} 데이터가 반영되었습니다!")
                st.balloons()
    else:
        st.error("시트의 '반이름' 컬럼을 확인하세요.")

# --- 3. 출결 현황 및 개인별 통계 화면 ---
elif menu == "출결 현황":
    st.title("📊 출결 현황 및 분석")
    
    tab1, tab2 = st.tabs(["일자별 통계", "학생별 누적 현황"])
    
    with tab1:
        if not df_attendance.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                all_dates = sorted(df_attendance['날짜'].unique(), reverse=True)
                sel_date = st.selectbox("📅 날짜 선택", all_dates, key="date_sel")
            with col_f2:
                all_classes = ["전체"] + sorted(df_attendance['반이름'].unique().tolist())
                sel_class_filter = st.selectbox("🏫 반별 필터", all_classes, key="class_sel")
            
            date_df = df_attendance[df_attendance['날짜'] == sel_date].copy()
            
            # 요약 지표
            total_sts = len(date_df)
            present_sts = len(date_df[date_df['출석여부'] == 1])
            absent_sts = total_sts - present_sts
            
            m1, m2, m3 = st.columns(3)
            m1.metric("대상", f"{total_sts}명")
            m2.metric("출석", f"{present_sts}명")
            m3.metric("결석", f"{absent_sts}명")
            
            st.subheader("🏫 반별 요약")
            summary = date_df.groupby('반이름')['출석여부'].agg(['count', 'sum']).reset_index()
            summary.columns = ['반이름', '대상', '출석']
            summary['결석'] = summary['대상'] - summary['출석']
            st.table(summary.set_index('반이름'))

            st.subheader("📄 상세 명단 (사유 포함)")
            view_df = date_df.copy()
            if sel_class_filter != "전체":
                view_df = view_df[view_df['반이름'] == sel_class_filter]
            view_df['상태'] = view_df['출석여부'].apply(lambda x: "✅" if x == 1 else "❌")
            st.dataframe(view_df[['이름', '반이름', '상태', '비고']].sort_values("반이름"), use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    with tab2:
        st.subheader("📅 학생별 출석 타임라인")
        if not df_attendance.empty:
            # 개인별 가로 출력용 피벗 테이블 생성
            # 날짜를 가로 컬럼으로, 이름을 세로 인덱스로
            pivot_df = df_attendance.pivot_table(index=['반이름', '이름'], columns='날짜', values='출석여부')
            
            # 5회 연속 결석 체크 함수
            def check_long_absent(row):
                # 결석은 0, 출석은 1이므로 0이 5번 연속되는지 확인
                count = 0
                for val in row.dropna(): # 데이터가 있는 날짜만 검사
                    if val == 0:
                        count += 1
                        if count >= 5: return "⚠️ 장기결석"
                    else:
                        count = 0
                return ""

            # 장기결석 여부 계산
            pivot_df['관리상태'] = pivot_df.apply(check_long_absent, axis=1)
            
            # 보기 좋게 변환 (1 -> O, 0 -> X)
            display_pivot = pivot_df.replace({1: "O", 0: "X"})
            
            # 관리상태 컬럼을 맨 앞으로 이동
            cols = ['관리상태'] + [c for c in display_pivot.columns if c != '관리상태']
            display_pivot = display_pivot[cols]
            
            st.dataframe(display_pivot.sort_index(), use_container_width=True)
            st.caption("※ X가 연속 5회 이상 발생한 학생은 '장기결석'으로 표시됩니다.")
        else:
            st.info("데이터가 없습니다.")

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
            st.link_button("🐙 GitHub 저장소 이동", "https://github.com/")
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")
