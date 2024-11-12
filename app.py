import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import pymysql
from scapy.all import sniff, IP, TCP, Ether
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
CORS(app)
socketio = SocketIO(app, async_mode='eventlet')

db = pymysql.connect(host='43.203.195.110', port=3306, user='id_j2h', password='Password_j2h!12345', database='chat_app')
cursor = db.cursor()

# URL과 HTML 연결
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
            return render_template('chat.html', nickname=user_info[1])
        else:
            return render_template('login.html', info='user does not exist')

    return render_template('login.html')

@app.route('/signup/set/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        signup_info = request.form
        sql = """
            INSERT INTO users (nickname, id, password, email)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(sql, (signup_info['nickname'], signup_info['id'], signup_info['password'], signup_info['email']))
        db.commit()
        return render_template('login.html')

    return render_template('login.html')

# 클라이언트 - 서버 연결 이벤트
@socketio.on('connect')
def handle_connect():
    print('클라이언트가 서버에 연결되었습니다!')

# 채팅방 참여
@socketio.event
def handle_join_room(data):
    join_room(data.get('number'))
    emit('system', f"{data.get('name')}님이 채팅방에 참가하셨습니다.", to=data.get('number'))

# 메세지 수신 및 발송, 패킷 로그 기능 추가
@socketio.event
def send_message_event(data):
    room = data.get('number')
    nickname = data.get('nickname')
    message = data.get('message')
    emit('send_message_event', {'message': message, 'nickname': nickname}, room=room)

    # 패킷 캡처 시작
    threading.Thread(target=capture_packets, args=(message, room, nickname)).start()

def capture_packets(message, room, nickname):
    packets = sniff(filter="tcp", count=1)  # TCP 패킷 하나만 캡처
    for packet in packets:
        log = []

        # 애플리케이션 계층
        log.append(f"Application Layer: Message = {message}")

        # 데이터 링크 계층 (MAC 주소)
        if Ether in packet:
            data_link_layer = {
                'source_mac': packet[Ether].src,
                'destination_mac': packet[Ether].dst
            }
            log.append(f"Data Link Layer: {data_link_layer}")

        # 네트워크 계층 (IP 주소)
        if IP in packet:
            network_layer = {
                'source_ip': packet[IP].src,
                'destination_ip': packet[IP].dst,
                'ttl': packet[IP].ttl
            }
            log.append(f"Network Layer: {network_layer}")

        # 전송 계층 (TCP 포트 및 체크섬)
        if TCP in packet:
            transport_layer = {
                'source_port': packet[TCP].sport,
                'destination_port': packet[TCP].dport,
                'sequence_number': packet[TCP].seq,
                'checksum': packet[TCP].chksum
            }
            log.append(f"Transport Layer: {transport_layer}")

        # 각 계층별 로그를 클라이언트에 전송
        for entry in log:
            socketio.emit('packet_log', entry, to=room)

# 채팅방 나감
@socketio.event
def handle_leave_room(data):
    leave_room(data.get('number'))
    emit('system', f"{data.get('name')}님이 채팅방에서 나갔습니다.", to=data.get('number'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
