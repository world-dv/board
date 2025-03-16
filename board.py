import streamlit as st
import sqlite3
import time as now
import uuid
import json
import os

# DB 연동 - db이름: example.db
conn = sqlite3.connect('example.db', check_same_thread=False)  
cursor = conn.cursor()

# DB 테이블 생성
cursor.execute('''
    CREATE TABLE IF NOT EXISTS boards (
        board_id INTEGER PRIMARY KEY AUTOINCREMENT,
        board_name VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        comment TEXT NOT NULL,
        likes INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# 좋아요 기록 테이블 생성 (사용자가 어떤 댓글에 좋아요를 눌렀는지 기록)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS like_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        UNIQUE(board_id, session_id)
    )
''')
conn.commit()

# 지속적인 세션 ID 관리를 위한 파일 기반 접근법
SESSION_FILE = "session_store.json"

def get_or_create_session_id():
    """파일에 저장된 세션 ID를 가져오거나 새로 생성"""
    # 1. 세션 스토어 파일 존재 확인
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
                
            # 브라우저 시그니처 생성 (간단한 식별자)
            browser_signature = get_browser_signature()
            
            # 저장된 세션 데이터에서 현재 브라우저 시그니처와 일치하는 세션 ID 찾기
            if browser_signature in session_data:
                return session_data[browser_signature]
        except:
            pass  # 파일 읽기 실패 시 새 세션 ID 생성
    
    # 2. 새 세션 ID 생성
    session_id = str(uuid.uuid4())
    
    # 3. 세션 ID 저장
    save_session_id(session_id)
    
    return session_id

def save_session_id(session_id):
    """세션 ID를 파일에 저장"""
    # 브라우저 시그니처 생성
    browser_signature = get_browser_signature()
    
    # 기존 세션 데이터 로드 또는 새로 생성
    session_data = {}
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
        except:
            pass
    
    # 브라우저 시그니처와 세션 ID 매핑
    session_data[browser_signature] = session_id
    
    # 파일에 저장
    with open(SESSION_FILE, 'w') as f:
        json.dump(session_data, f)

def get_browser_signature():
    """간단한 브라우저 시그니처 생성"""
    # 실제 환경에서는 User-Agent 등을 사용하여 더 정확한 시그니처 생성 가능
    # 여기서는 간단히 st.query_params를 사용
    return str(hash(str(st.query_params)))

# 세션 ID 초기화
if "session_id" not in st.session_state:
    st.session_state.session_id = get_or_create_session_id()

# 초기 세션 상태 설정
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_password" not in st.session_state:
    st.session_state.user_password = ""
if "user_review" not in st.session_state:
    st.session_state.user_review = ""
# 비밀번호 입력 상태 추가
if "delete_password" not in st.session_state:
    st.session_state.delete_password = {}

def info():
    """안내 메시지 출력"""
    st.write("사고닷을 사용해주셔서 감사합니다! 방명록을 남겨주세요 💖")
    # 디버깅용 (필요시 주석 해제)
    # st.write(f"현재 세션 ID: {st.session_state.session_id}")

def render_review_form():
    """후기 작성 폼 생성"""
    st.header("사용자 후기")
    with st.form(key='review_form'):
        user_name = st.text_input("이름", value=st.session_state.user_name, key="user_name")
        user_password = st.text_input("비밀번호", type="password", value=st.session_state.user_password, key="user_password")
        user_review = st.text_area("후기 작성", value=st.session_state.user_review, key="user_review")
        submit_button = st.form_submit_button("후기 제출")
    
    return user_name, user_password, user_review, submit_button

def handle_review_submission(user_name, user_password, user_review):
    """후기 제출 시 DB 저장"""
    if user_name and user_password and user_review:
        cursor.execute("INSERT INTO boards (board_name, password, comment) VALUES (?, ?, ?)", (user_name, user_password, user_review))
        conn.commit()
        
        st.success("소중한 후기 감사합니다 😊")

        # 세션 상태 초기화
        for key in ["user_name", "user_password", "user_review"]:
            if key in st.session_state:
                del st.session_state[key]

        now.sleep(1)
        st.rerun()
    else:
        st.error("이름과 비밀번호, 후기를 모두 작성해 주세요.")

def display_reviews():
    """저장된 후기 목록을 출력"""
    st.write("### 방명록")
    cursor.execute("SELECT * FROM boards ORDER BY board_id DESC")
    all_reviews = cursor.fetchall()

    for idx, row in enumerate(all_reviews):
        review_id, name, password, review, likes = row[:5]

        with st.expander(f"💛 {name}님의 리뷰"):
            st.write(f"**후기 내용:** {review}")
            st.write(f"좋아요 수: {likes}")

            # 버튼 행 추가 (좋아요, 수정, 삭제)
            col1, col2, col3 = st.columns(3)
            
            # 좋아요 버튼 상태 확인 (이미 좋아요를 눌렀는지)
            cursor.execute("SELECT * FROM like_records WHERE board_id = ? AND session_id = ?", 
                          (review_id, st.session_state.session_id))
            already_liked = cursor.fetchone() is not None
            
            # 좋아요 버튼
            like_button = col1.button(
                "이미 좋아요 누름" if already_liked else "좋아요", 
                key=f"like_{idx}",
                disabled=already_liked
            )
            # 수정 버튼
            edit_button = col2.button("수정", key=f"edit_{idx}")
            # 삭제 버튼
            delete_button = col3.button("삭제", key=f"delete_{idx}")

            if like_button:
                handle_like(review_id)

            # 수정 버튼 클릭 시
            if edit_button:
                st.session_state[f"show_edit_form_{review_id}"] = True
                
            # 수정 폼 표시
            if st.session_state.get(f"show_edit_form_{review_id}", False):
                password_input = st.text_input(f"리뷰 수정을 위한 비밀번호를 입력하세요", 
                                              type="password", 
                                              key=f"edit_pwd_{review_id}")
                if st.session_state.get(f"edit_verified_{review_id}", False):
                    # 비밀번호 인증 완료 시 수정 폼 표시
                    new_review = st.text_area("수정할 내용", 
                                             value=review, 
                                             key=f"edit_content_{review_id}")
                    save_button = st.button("저장", key=f"save_{review_id}")
                    cancel_button = st.button("취소", key=f"cancel_{review_id}")
                    
                    if save_button:
                        # 수정 내용 저장
                        cursor.execute("UPDATE boards SET comment = ?, updated_at = CURRENT_TIMESTAMP WHERE board_id = ?", 
                                      (new_review, review_id))
                        conn.commit()
                        # 수정 관련 상태 초기화
                        del st.session_state[f"show_edit_form_{review_id}"]
                        del st.session_state[f"edit_verified_{review_id}"]
                        st.success("리뷰가 수정되었습니다.")
                        now.sleep(1)
                        st.rerun()
                    
                    if cancel_button:
                        # 수정 취소 시 상태 초기화
                        del st.session_state[f"show_edit_form_{review_id}"]
                        del st.session_state[f"edit_verified_{review_id}"]
                        st.rerun()
                else:
                    # 비밀번호 확인 버튼
                    verify_button = st.button("비밀번호 확인", key=f"verify_edit_{review_id}")
                    if verify_button:
                        if password_input == password:
                            st.session_state[f"edit_verified_{review_id}"] = True
                            st.success("비밀번호가 확인되었습니다. 내용을 수정해주세요.")
                            st.rerun()
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")

            # 삭제 버튼 클릭 시
            if delete_button:
                st.session_state[f"show_delete_form_{review_id}"] = True
            
            # 삭제 폼 표시
            if st.session_state.get(f"show_delete_form_{review_id}", False):
                password_input = st.text_input(f"리뷰 삭제를 위한 비밀번호를 입력하세요", 
                                              type="password", 
                                              key=f"del_pwd_{review_id}")
                confirm_button = st.button("확인", key=f"confirm_del_{review_id}")
                cancel_button = st.button("취소", key=f"cancel_del_{review_id}")
                
                if confirm_button:
                    delete_with_password(review_id, name, password, password_input)
                
                if cancel_button:
                    del st.session_state[f"show_delete_form_{review_id}"]
                    st.rerun()

def handle_like(review_id):
    """좋아요 버튼 클릭 시 좋아요 수 증가 (중복 방지)"""
    session_id = st.session_state.session_id
    
    # 이미 좋아요를 눌렀는지 확인
    cursor.execute("SELECT * FROM like_records WHERE board_id = ? AND session_id = ?", 
                  (review_id, session_id))
    
    existing_like = cursor.fetchone()
    
    if existing_like is None:  # 아직 좋아요를 누르지 않았다면
        try:
            # 좋아요 수 증가
            cursor.execute("UPDATE boards SET likes = likes + 1 WHERE board_id = ?", (review_id,))
            
            # 좋아요 기록 추가
            cursor.execute("INSERT INTO like_records (board_id, session_id) VALUES (?, ?)", 
                          (review_id, session_id))
            
            conn.commit()
            st.success("좋아요를 눌렀습니다!")
        except sqlite3.Error as e:
            st.error(f"데이터베이스 오류: {e}")
            conn.rollback()
    else:
        st.warning("이미 좋아요를 누른 댓글입니다.")
    
    # 1초 대기 후 페이지 새로고침
    now.sleep(1)
    st.rerun()

def delete_with_password(review_id, name, stored_password, input_password):
    """비밀번호 확인 후 댓글 삭제"""
    if input_password == stored_password:
        # 비밀번호가 일치하면 삭제
        cursor.execute("DELETE FROM boards WHERE board_id = ?", (review_id,))
        # 관련 좋아요 기록도 삭제
        cursor.execute("DELETE FROM like_records WHERE board_id = ?", (review_id,))
        conn.commit()
        
        # 삭제 폼 상태 초기화
        if f"show_delete_form_{review_id}" in st.session_state:
            del st.session_state[f"show_delete_form_{review_id}"]
            
        st.success(f"{name}님의 리뷰가 삭제되었습니다.")
        now.sleep(1)
        st.rerun()
    else:
        st.error("비밀번호가 일치하지 않습니다.")

def main():
    """메인 실행 함수"""
    st.title("사고닷 방명록")
    info()

    # 후기 작성 폼 실행
    user_name, user_password, user_review, submit_button = render_review_form()
    
    # 제출 버튼 클릭 시 처리
    if submit_button:
        handle_review_submission(user_name, user_password, user_review)

    # 저장된 리뷰 목록 표시
    display_reviews()

if __name__ == "__main__":
    main()