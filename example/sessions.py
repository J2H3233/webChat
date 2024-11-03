from flask import Flask, render_template, session, request, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_user, \
    logout_user
from flask_session import Session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret!'  # 세션 보안을 위한 비밀 키를 설정합니다.
app.config['SESSION_TYPE'] = 'filesystem'  # 세션 데이터를 파일 시스템에 저장하도록 설정합니다.
login = LoginManager(app)  # Flask-Login으로 사용자 인증을 관리합니다.
Session(app)  # Flask-Session을 사용하여 서버 측 세션을 설정합니다.
socketio = SocketIO(app, manage_session=False)
# Flask-SocketIO로 웹소켓을 설정합니다. manage_session=False는 Flask-Session과의 충돌을 방지합니다.

class User(UserMixin, object):
    def __init__(self, id=None):
        self.id = id
# 사용자 모델 클래스입니다. UserMixin을 사용하여 Flask-Login이 이 클래스와 함께 작동하도록 합니다.

@login.user_loader
def load_user(id):
    return User(id)
# 주어진 ID로 사용자를 로드하는 함수입니다. Flask-Login에서 사용자 인증에 사용됩니다.

@app.route('/')
def index():
    return render_template('sessions.html')
# "/" 경로에 대해 sessions.html을 렌더링합니다. 기본 웹 페이지를 제공합니다.

@app.route('/session', methods=['GET', 'POST'])
def session_access():
    if request.method == 'GET':
        return jsonify({
            'session': session.get('value', ''),
            'user': current_user.id
                if current_user.is_authenticated else 'anonymous'
        })
    # GET 요청에 대해 세션과 사용자 정보를 JSON으로 반환합니다.
    
    data = request.get_json()
    if 'session' in data:
        session['value'] = data['session']
    elif 'user' in data:
        if data['user']:
            login_user(User(data['user']))
        else:
            logout_user()
    return '', 204
# POST 요청에 대해 세션 값을 설정하거나 사용자 인증을 처리합니다.

@socketio.on('get-session')
def get_session():
    emit('refresh-session', {
        'session': session.get('value', ''),
        'user': current_user.id
            if current_user.is_authenticated else 'anonymous'
    })
# 'get-session' 이벤트를 처리하여 클라이언트에 현재 세션과 사용자 정보를 전송합니다.

@socketio.on('set-session')
def set_session(data):
    if 'session' in data:
        session['value'] = data['session']
    elif 'user' in data:
        if data['user'] is not None:
            login_user(User(data['user']))
        else:
            logout_user()
# 'set-session' 이벤트를 처리하여 세션 값을 설정하거나 사용자 인증을 처리합니다.

if __name__ == '__main__':
    socketio.run(app)
# 애플리케이션을 실행하고 Flask-SocketIO로 웹소켓 연결을 처리합니다.
