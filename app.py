import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 환경 설정 ---
st.set_page_config(page_title="목포꿈의교회 학생회 관리", layout="wide", page_icon="🏫")
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
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

# --- 2. 사이드바 ---
st.sidebar.title("⛪ 메뉴")
menu = st.sidebar.selectbox("이동", ["명단 검색", "출석 체크", "출결 현황", "⚙️ 관리자 도구"])

# --- 3. 명단 검색 ---
if menu == "명단 검색":
    st.title("🔍 학생 명단 검색")
    c1, c2, c3, c4 = st.columns(4)
    schools = ["전체"] + sorted(df_students['학교'].dropna().unique().tolist())
    sel_school = c1.selectbox("학교", schools)
    grades = ["전체"] + sorted(df_students['학년'].dropna().unique().tolist())
    sel_grade = c2.selectbox("학년", grades)
    classes = ["전체"] + sorted(df_students['반이름'].dropna().unique().tolist())
    sel_class = c3.selectbox("반", classes)
    search_name = c4.text_input("이름 검색")

    f_df = df_students.copy()
    if sel_school != "전체": f_df = f_df[f_df['학교'] == sel_school]
    if sel_grade != "전체": f_df = f_df[f_df['학년'] == sel_grade]
    if sel_class != "전체": f_df = f_df[f_df['반이름'] == sel_class]
    if search_name: f_df = f_df[f_df['이름'].astype(str).str.contains(search_name, na=False)]

    st.write(f"결과: {len(f_df)}명")
    f_df.index = range(1, len(f_df) + 1)
    st.dataframe(f_df, use_container_width=True)

# --- 4. 출석 체크 ---
elif menu == "출석 체크":
    st.title("✅ 주일 출석 체크")
    if '반이름' in df_students.columns:
        cls_list = sorted(df_students['반이름'].dropna().unique().tolist())
        sel_cls = st.selectbox("반 선택", cls_list)
        today = datetime.now().date()
        def_sun = today + timedelta(days=(6-today.weekday()) if today.weekday() != 6 else 0)
        check_date = st.date_input("날짜", def_sun)

        ex_att = df_attendance[(df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_cls)]
        c_sts = df_students[df_students['반이름'] == sel_cls]
        
        with st.form("att_form"):
            st.write(f"--- {sel_cls} ({check_date}) ---")
            res = []
            for i, (_, row) in enumerate(c_sts.iterrows(), 1):
                is_chk, ex_note = False, ""
                if not ex_att.empty:
                    m = ex_att[ex_att['이름'] == row['이름']]
                    if not m.empty:
                        is_chk = True if m.iloc[0]['출석여부'] == 1 else False
                        ex_note = m.iloc[0]['비고'] if '비고' in m.columns else ""
                
                col1, col2 = st.columns([1, 2])
                p = col1.checkbox(f"{i}. {row['이름']}", value=is_chk, key=f"at_{row['이름']}")
                n = col2.text_input("사유", value=ex_note, key=f"nt_{row['이름']}")
                res.append({'날짜': check_date, '이름': row['이름'], '반이름': sel_cls, '출석여부': 1 if p else 0, '비고': n})
            
            if st.form_submit_button("저장하기"):
                new_df = pd.DataFrame(res)
                other = df_attendance[~((df_attendance['날짜'] == check_date) & (df_attendance['반이름'] == sel_cls))]
                upd = pd.concat([other, new_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="attendance", data=upd)
                st.success("저장되었습니다!")
                st.balloons()
    else: st.error("반이름 컬럼 오류")

# --- 5. 출결 현황 ---
elif menu == "출결 현황":
    st.title("📊 출결 분석")
    t1, t2 = st.tabs(["일자별 통계", "학생별 누적 추이"])
    with t1:
        if not df_attendance.empty:
            dates = sorted(df_attendance['날짜'].unique(), reverse=True)
            s_date = st.selectbox("날짜 선택", dates)
            d_df = df_attendance[df_attendance['날짜'] == s_date].copy()
            
            st.subheader("🏫 반별 요약")
            sm = d_df.groupby('반이름')['출석여부'].agg(['count', 'sum']).reset_index()
            sm.columns = ['반이름', '대상', '출석']
            sm['결석'] = sm['대상'] - sm['출석']
            sm.index = range(1, len(sm) + 1)
            st.table(sm)

            d_df['상태'] = d_df['출석여부'].apply(lambda x: "✅" if x == 1 else "❌")
            v_df = d_df[['이름', '반이름', '상태', '비고']].sort_values("반이름")
            v_df.index = range(1, len(v_df) + 1)
            st.dataframe(v_df, use_container_width=True)
        else: st.info("기록 없음")

    with t2:
        st.subheader("📅 학생별 출결 추이")
        if not df_attendance.empty:
            pv = df_attendance.pivot_table(index=['반이름', '이름'], columns='날짜', values='출석여부')
            def check_l(r):
                cnt = 0
                for v in r.dropna():
                    if v == 0:
                        cnt += 1
                        if cnt >= 5: return "⚠️ 장기결석"
                    else: cnt = 0
                return ""
            pv['관리상태'] = pv.apply(check_l, axis=1)
            dp = pv.replace({1: "출석", 0: "결석"})
            cols = ['관리상태'] + [c for c in dp.columns if c != '관리상태']
            dp = dp[cols].sort_index().reset_index()
            dp.index = range(1, len(dp) + 1)
            dp.index.name = "번호"
            st.dataframe(dp, use_container_width=True)
        else: st.info("기록 없음")

# --- 6. 관리자 ---
elif menu == "⚙️ 관리자 도구":
    st.title("⚙️ 관리자")
    pw = st.text_input("비밀번호", type="password")
    if pw == "0498":
        st.success("인증 성공")
        c1, c2 = st.columns(2)
        c1.link_button("📊 구글 시트", SHEET_URL)
        c2.link_button("🎈 Streamlit", "https://share.streamlit.io/")
        c2.link_button("🐙 GitHub", "https://github.com/")
    elif pw != "": st.error("비밀번호 불일치")
