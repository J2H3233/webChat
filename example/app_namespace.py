from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, join_room, leave_room, \
    close_room, rooms, disconnect

# 이 변수를 "threading", "eventlet" 또는 "gevent"로 설정하여 다양한 비동기 모드를 테스트할 수 있습니다.
# 설치된 패키지에 따라 애플리케이션이 최적의 모드를 자동으로 선택하게 하려면 None으로 설정하십시오.
async_mode = None

app = Flask(__name__)  # Flask 애플리케이션 인스턴스를 생성합니다.
app.config['SECRET_KEY'] = 'secret!'  # 세션 보안을 위한 비밀 키를 설정합니다.
socketio = SocketIO(app, async_mode=async_mode)  # Flask 앱에 SocketIO를 추가합니다.
thread = None  # 백그라운드 스레드 객체를 초기화합니다.
thread_lock = Lock()  # 스레드 동기화를 위한 Lock 객체입니다.

def background_thread():
    """서버에서 생성한 이벤트를 클라이언트로 전송하는 예제입니다."""
    count = 0
    while True:
        socketio.sleep(10)  # 10초마다 이벤트를 전송합니다.
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')  # /test 네임스페이스로 이벤트를 전송합니다.

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)
# "/" 경로에 대해 index.html을 렌더링합니다. 웹소켓 비동기 모드 정보를 전달합니다.

class MyNamespace(Namespace):
    # Socket.IO 네임스페이스를 정의하는 클래스입니다.
    
    def on_my_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']})
    # 'my_event' 이벤트를 처리하고 클라이언트에 응답을 보냅니다.

    def on_my_broadcast_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             broadcast=True)
    # 메시지를 모든 클라이언트에 방송합니다.

    def on_join(self, message):
        join_room(message['room'])  # 지정된 방에 클라이언트를 추가합니다.
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})
    # 클라이언트가 방에 참여할 때 방 정보를 클라이언트에 전송합니다.

    def on_leave(self, message):
        leave_room(message['room'])  # 지정된 방에서 클라이언트를 제거합니다.
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})
    # 클라이언트가 방을 떠날 때 방 정보를 클라이언트에 전송합니다.

    def on_close_room(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                             'count': session['receive_count']},
             room=message['room'])
        close_room(message['room'])  # 방을 닫고 모든 클라이언트를 제거합니다.
    # 특정 방을 닫고 방에 있는 모든 클라이언트에 알립니다.

    def on_my_room_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             room=message['room'])
    # 특정 방에만 이벤트를 전송합니다.

    def on_disconnect_request(self):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()  # 클라이언트를 안전하게 연결 해제합니다.
    # 클라이언트가 연결 해제를 요청할 때 처리합니다.

    def on_my_ping(self):
        emit('my_pong')  # 클라이언트에 'my_pong' 이벤트를 전송합니다.
    # 핑-퐁 테스트를 위해 핑 메시지를 수신할 때 클라이언트에 퐁을 보냅니다.

    def on_connect(self):
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(background_thread)
        emit('my_response', {'data': 'Connected', 'count': 0})
    # 클라이언트가 연결될 때 백그라운드 스레드를 시작하고 연결을 확인하는 메시지를 전송합니다.

    def on_disconnect(self):
        print('Client disconnected', request.sid)
    # 클라이언트가 연결 해제될 때 서버에 로그를 출력합니다.

socketio.on_namespace(MyNamespace('/'))
# MyNamespace를 '/' 네임스페이스에 연결합니다.

if __name__ == '__main__':
    socketio.run(app)  # 앱을 실행하고 SocketIO를 사용하여 요청을 처리합니다.
