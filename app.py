from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect


app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
socketio = SocketIO(app)

@app.route('/')
def render_main_page():
    return render_template('index.html')

@socketio.event
def join_event(data):
    join_room(data.get('number'))
    print("참여한 방 " + data.get('number'))

@socketio.event
def send_message_event(data):
    emit('send_message_event',
         {'message' : data.get('message'), 
          'nickname' : data.get('nickname') },
          room=data.get('number'))
    print("서버에서 보낸 메세지의 주소 " + data.get('number'))


if __name__ == '__main__':
    socketio.run(app, debug=True)