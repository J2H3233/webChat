from threading import Lock
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect

# 필요한 라이브러리 및 모듈을 임포트합니다. Flask는 웹 애플리케이션을 구축하는 데 사용되며, Flask-SocketIO는 WebSocket을 활용한 실시간 통신을 제공합니다. `Lock`은 백그라운드 스레드의 동시 실행을 방지하기 위해 사용됩니다.

async_mode = None  # 비동기 모드를 자동 선택하도록 설정합니다.

app = Flask(__name__)  # Flask 애플리케이션 생성
app.config['SECRET_KEY'] = 'secret!'  # 세션 데이터 보호를 위한 시크릿 키 설정
socketio = SocketIO(app, async_mode=async_mode, logger=True, engineio_logger=True)  # WebSocket을 지원하는 SocketIO 객체 생성
thread = None
thread_lock = Lock()  # 백그라운드 스레드 동기화용 Lock 생성

def background_thread():
    """서버에서 클라이언트로 주기적으로 이벤트를 전송하는 백그라운드 작업"""
    count = 0
    while True:
        socketio.sleep(10)  # 10초마다 타이머를 사용하여 대기
        count += 1
        socketio.emit('my_response', {'data': 'Server generated event', 'count': count})  # 이벤트 전송

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)  # 클라이언트에게 index.html 렌더링

@socketio.event
def my_event(message):
    # 클라이언트로부터 받은 메시지를 처리하고 응답을 보냅니다.
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': message['data'], 'count': session['receive_count']})

@socketio.event
def my_broadcast_event(message):
    # 받은 메시지를 모든 클라이언트에게 브로드캐스트합니다.
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': message['data'], 'count': session['receive_count']}, broadcast=True)

@socketio.event
def join(message):
    # 클라이언트가 특정 방에 참여하도록 처리합니다.
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'In rooms: ' + ', '.join(rooms()), 'count': session['receive_count']})

@socketio.event
def leave(message):
    # 클라이언트를 특정 방에서 나가게 처리합니다.
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'In rooms: ' + ', '.join(rooms()), 'count': session['receive_count']})

@socketio.on('close_room')
def on_close_room(message):
    # 특정 방을 닫고, 그 방에 있는 모든 클라이언트에게 알림을 보냅니다.
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.', 'count': session['receive_count']}, to=message['room'])
    close_room(message['room'])

@socketio.event
def my_room_event(message):
    # 특정 방에 있는 클라이언트에게 메시지를 보냅니다.
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': message['data'], 'count': session['receive_count']}, to=message['room'])

@socketio.on('*')
def catch_all(event, data):
    # 모든 이벤트를 포착하여 처리합니다.
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': [event, data], 'count': session['receive_count']})

@socketio.event
def disconnect_request():
    # 클라이언트의 연결 해제를 처리합니다.
    @copy_current_request_context
    def can_disconnect():
        disconnect()  # 클라이언트를 안전하게 연결 해제

    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Disconnected!', 'count': session['receive_count']}, callback=can_disconnect)

@socketio.event
def my_ping():
    # 핑 이벤트에 응답하여 퐁 이벤트를 보냅니다.
    emit('my_pong')

@socketio.event
def connect():
    # 클라이언트가 연결되었을 때 백그라운드 스레드를 시작합니다.
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

@socketio.on('disconnect')
def test_disconnect():
    # 클라이언트가 연결 해제되었을 때 로그에 출력합니다.
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app)  # 애플리케이션 실행 및 WebSocket 서버 시작
