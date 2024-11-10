import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit, join_room, leave_room, close_room, rooms, disconnect
from flask_cors import CORS
import pymysql



app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
CORS(app)
socketio = SocketIO(app, async_mode='eventlet')

db = pymysql.connect(host='43.203.195.110', port=3306, user ='id_j2h', password='Password_j2h!12345', database='chat_app')
cursor = db.cursor()

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

@app.route('/login/set/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_info = request.form
        
        user_id = login_info['username'] 

        sql = "SELECT * FROM users WHERE id=%s"
        rows_count = cursor.execute(sql, (user_id))

        if rows_count > 0:
            user_info = cursor.fetchone()
            print("user info: ", user_info)
            # 데이터는 user_index, nickname, id, password, email 순서로 정렬

            is_pw_correct = user_info[3]  
            print("password check: ", is_pw_correct)

            # 로그인 성공하면 채팅 페이지로
            return render_template('chat.html',nickname = user_info[1])

        else:
            print('user does not exist')
            return render_template('login.html', info='user does not exist')

    return render_template('login.html')


@app.route('/signup/set/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        signup_info = request.form

        email = signup_info['email']
        user_id = signup_info['id']
        password = signup_info['password']
        nickname = signup_info['nickname']
        
        sql = """
            INSERT INTO users (nickname, id, password, email)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(sql, (nickname, user_id, password, email))
        db.commit()

        print(nickname, user_id, password, email)

        return render_template('login.html')

    return render_template('login.html')


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



if __name__ == '__main__':
    socketio.run(app, debug=True)