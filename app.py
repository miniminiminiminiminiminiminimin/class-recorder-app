import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pyrebase
from datetime import date

# Firebase 초기화
cred = credentials.Certificate("firebase_service_account.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': '<YOUR_FIREBASE_STORAGE_BUCKET>'
    })

db = firestore.client()

firebaseConfig = {
    "apiKey": "<YOUR_API_KEY>",
    "authDomain": "class-recorder0729.firebaseapp.com",
    "databaseURL": "https://class-recorder0729-default-rtdb.firebaseio.com/",
    "projectId": "class-recorder0729",
    "storageBucket": "class-recorder0729.appspot.com",
    "messagingSenderId": "<YOUR_SENDER_ID>",
    "appId": "<YOUR_APP_ID>"
}


pb = pyrebase.initialize_app(firebaseConfig)
auth_pb = pb.auth()

# 세션 상태 초기화
if 'user' not in st.session_state:
    st.session_state.user = None

# 로그인 페이지
def login_page():
    st.title("로그인 / 회원가입")
    email = st.text_input("이메일")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        try:
            user = auth_pb.sign_in_with_email_and_password(email, password)
            st.session_state.user = user
            st.success("로그인 성공")
        except:
            st.error("로그인 실패. 계정을 확인하세요.")

    if st.button("회원가입"):
        try:
            auth_pb.create_user_with_email_and_password(email, password)
            st.success("회원가입 성공. 로그인 해주세요.")
        except:
            st.error("회원가입 실패.")

# 교과 관리 페이지
def subject_page():
    st.header("교과 관리")
    if st.button("교과 추가"):
        st.session_state.add_subject = True

    if st.session_state.get("add_subject", False):
        name = st.text_input("교과명")
        year = st.number_input("학년도", min_value=2000, max_value=2100, step=1)
        semester = st.selectbox("학기", [1, 2])
        file = st.file_uploader("수업계획 및 평가계획서 (PDF)", type=["pdf"])
        if st.button("등록"):
            if file:
                blob = storage.bucket().blob(f"subjects/{file.name}")
                blob.upload_from_file(file, content_type="application/pdf")
                url = blob.public_url
                db.collection("subjects").add({
                    "name": name,
                    "year": year,
                    "semester": semester,
                    "file_url": url
                })
                st.success("교과 등록 완료")
                st.session_state.add_subject = False

    st.subheader("등록된 교과 목록")
    subjects = db.collection("subjects").stream()
    for s in subjects:
        data = s.to_dict()
        st.write(f"{data['year']}년 {data['semester']}학기 - {data['name']}")
        st.write(f"[계획서 다운로드]({data['file_url']})")

# 수업 반 관리 페이지
def class_page():
    st.header("수업 반 관리")
    year = st.number_input("학년도", min_value=2000, max_value=2100, step=1)
    semester = st.selectbox("학기", [1, 2])
    subjects = db.collection("subjects").stream()
    subject_options = {s.id: s.to_dict()['name'] for s in subjects}
    subject_id = st.selectbox("교과 선택", options=list(subject_options.keys()), format_func=lambda x: subject_options[x])
    class_name = st.text_input("반 이름")
    day = st.selectbox("요일", ["월", "화", "수", "목", "금"])
    period = st.number_input("교시", min_value=1, max_value=10)

    if st.button("반 등록"):
        db.collection("classes").add({
            "year": year,
            "semester": semester,
            "subject_id": subject_id,
            "class_name": class_name,
            "day": day,
            "period": period
        })
        st.success("반 등록 완료")

# 학생 관리 페이지
def student_page():
    st.header("학생 관리")
    classes = db.collection("classes").stream()
    class_options = {c.id: c.to_dict()['class_name'] for c in classes}
    class_id = st.selectbox("반 선택", options=list(class_options.keys()), format_func=lambda x: class_options[x])

    student_name = st.text_input("학생 이름")
    student_id = st.text_input("학번")

    if st.button("학생 추가"):
        db.collection("classes").document(class_id).collection("students").add({
            "student_name": student_name,
            "student_id": student_id
        })
        st.success("학생 등록 완료")

    file = st.file_uploader("CSV 업로드", type=["csv"])
    if file:
        df = pd.read_csv(file)
        for _, row in df.iterrows():
            db.collection("classes").document(class_id).collection("students").add({
                "student_name": row['성명'],
                "student_id": row['학번']
            })
        st.success("CSV 학생 등록 완료")

# 진도 관리 페이지
def progress_page():
    st.header("진도 관리")
    classes = db.collection("classes").stream()
    class_options = {c.id: c.to_dict()['class_name'] for c in classes}
    class_id = st.selectbox("반 선택", options=list(class_options.keys()), format_func=lambda x: class_options[x])

    d = st.date_input("일자")
    period = st.number_input("교시", min_value=1, max_value=10)
    content = st.text_area("진도 내용")
    note = st.text_area("특기사항")

    if st.button("진도 기록"):
        db.collection("classes").document(class_id).collection("progress").add({
            "date": d.isoformat(),
            "period": period,
            "content": content,
            "note": note
        })
        st.success("진도 기록 완료")

# 출결 관리 페이지
def attendance_page():
    st.header("출결 관리")
    classes = db.collection("classes").stream()
    class_options = {c.id: c.to_dict()['class_name'] for c in classes}
    class_id = st.selectbox("반 선택", options=list(class_options.keys()), format_func=lambda x: class_options[x])

    d = st.date_input("일자")
    students = db.collection("classes").document(class_id).collection("students").stream()

    for student in students:
        data = student.to_dict()
        status = st.radio(f"{data['student_name']} 출결", ["출석", "지각", "결석", "조퇴"], key=data['student_id'])
        note = st.text_input(f"{data['student_name']} 특기사항", key=f"note_{data['student_id']}")
        if st.button(f"{data['student_name']} 저장", key=f"save_{data['student_id']}"):
            db.collection("classes").document(class_id).collection("attendance").add({
                "student_id": data['student_id'],
                "date": d.isoformat(),
                "status": status,
                "note": note
            })
            st.success(f"{data['student_name']} 출결 저장 완료")

# 메인 실행
if not st.session_state.user:
    login_page()
else:
    menu = st.sidebar.selectbox("메뉴", ["교과 관리", "수업 반 관리", "학생 관리", "진도 관리", "출결 관리"])
    if menu == "교과 관리":
        subject_page()
    elif menu == "수업 반 관리":
        class_page()
    elif menu == "학생 관리":
        student_page()
    elif menu == "진도 관리":
        progress_page()
    elif menu == "출결 관리":
        attendance_page()
