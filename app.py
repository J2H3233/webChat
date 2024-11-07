import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, join_room, leave_room, close_room, rooms, disconnect
import pymysql



app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
socketio = SocketIO(app, async_mode='eventlet')

db = pymysql.connect(host='43.203.195.110', port=3306, user ='id_j2h', password='Password_j2h!12345', database='chat_app')


# url - html 연결
@app.route('/')
def render_main_page():
    return render_template('index.html')
@app.route('/chat/')
def render_chat_page():
    return render_template('chat.html')
@app.route('/login/')
def render_login_page():
    return render_template('login.html')
@app.route('/signup/')
def render_signup_page():
    return render_template('signup.html')

# 클라이언트 - 서버 연결 이벤트
# 나중에 쓰지 않을까
@socketio.on('connect')
def handle_connect():
    print('클라이언트가 서버에 연결되었습니다!')

# 채팅방 참여
@socketio.event
def handle_join_room(data):
    room = data.get('number')
    name = data.get('name')
    join_room(room)
    emit('system',name+ '님이 채팅방에 참가하셨습니다.', to=room)
    print("참여한 방 " + data.get('number'))

# 메세지 수신, 발송
@socketio.event
def send_message_event(data):
    emit('send_message_event',
         {'message' : data.get('message'), 
          'nickname' : data.get('nickname') },
          room=data.get('number'))
    print("서버에서 보낸 메세지의 주소 " + data.get('number'))

# 채팅방 나감
@socketio.event
def handle_leave_room(data):
    name = data.get('name')
    room = data.get('number')
    leave_room(room)
    emit('system', name + '님이 채팅방에서 나갔습니다.', to=room, skip_sid=request.sid)
    print('방에서 나갔습니다.')







# 회원가입기능
# 미완성
@socketio.event
def signup(data):
    email = data.get(email)
    id = data.get(id)
    password = data.get(password)
    nickname = data.get(nickname)

# 로그인 기능
# 미완성
@socketio.event
def login(data):
    id = data.get(id)
    password = data.get(password)






if __name__ == '__main__':
    socketio.run(app, debug=True)