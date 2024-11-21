import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import pymysql
from scapy.all import sniff, IP, TCP, Ether
import threading
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # 폴더가 없으면 생성  # static/uploads 폴더 사용
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
CORS(app)
socketio = SocketIO(app, async_mode='eventlet')

db = pymysql.connect(host='43.203.195.110', port=3306, user='id_j2h', password='Password_j2h!12345', database='chat_app')
cursor = db.cursor()

@app.route('/')
def render_login_page():
    return render_template('login.html')

@app.route('/chat/')
def render_chat_page():
    nickname = request.args.get('nickname')
    return render_template('chat.html', nickname=nickname)

@app.route('/signup/')
def render_signup_page():
    return render_template('signup.html')

@app.route('/login/', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    sql = "SELECT * FROM users WHERE id=%s AND password=%s"
    result = cursor.execute(sql, (username, password))

    if result > 0:
        user_info = cursor.fetchone()
        flash(f"환영합니다, {user_info[1]}!", "success")
        return redirect(url_for('render_chat_page', nickname=user_info[1]))  # 닉네임 전달
    else:
        flash("아이디 또는 비밀번호가 잘못되었습니다.", "danger")
        return redirect(url_for('render_login_page'))

@app.route('/signup/set/', methods=['POST'])
def signup():
    user_data = {
        "id": request.form.get('id'),
        "password": request.form.get('password'),
        "nickname": request.form.get('nickname'),
        "email": request.form.get('email'),
    }
    sql = """
        INSERT INTO users (id, password, nickname, email)
        VALUES (%s, %s, %s, %s);
    """
    try:
        cursor.execute(sql, (user_data["id"], user_data["password"], user_data["nickname"], user_data["email"]))
        db.commit()
        flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")
        return redirect(url_for('render_login_page'))
    except Exception as e:
        db.rollback()
        flash(f"회원가입 실패: {str(e)}", "danger")
        return redirect(url_for('render_signup_page'))

# 클라이언트 - 서버 연결 이벤트
@socketio.on('connect')
def handle_connect():
    print('클라이언트가 서버에 연결되었습니다!')

@socketio.on('send_image_event')
def handle_send_image(data):
    emit('send_image_event', data, broadcast=True)

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

    packets = sniff(filter="tcp", count=1)  # TCP 패킷 하나 캡처
    for packet in packets:
        log = []

        # 애플리케이션 계층 데이터
        log.append(f"[Application Layer] {nickname}'s Message: {message}")

        # 데이터 링크 계층 (Ether)
        if Ether in packet:
            ether_layer = {
                'Source MAC': packet[Ether].src,
                'Destination MAC': packet[Ether].dst,
                'Type': hex(packet[Ether].type)  # 패킷 유형 (IPv4, ARP 등)
            }
            log.append(f"[Data Link Layer] {ether_layer}")

        # 네트워크 계층 (IP)
        if IP in packet:
            ip_layer = {
                'Source IP': packet[IP].src,
                'Destination IP': packet[IP].dst,
                'TTL': packet[IP].ttl,  # Time-to-Live
                'Protocol': packet[IP].proto  # 프로토콜 번호
            }
            log.append(f"[Network Layer] {ip_layer}")

        # 전송 계층 (TCP)
        if TCP in packet:
            tcp_layer = {
                'Source Port': packet[TCP].sport,
                'Destination Port': packet[TCP].dport,
                'Sequence Number': packet[TCP].seq,
                'Acknowledgment Number': packet[TCP].ack,
                'Flags': packet[TCP].flags,  # SYN, ACK 등 플래그
                'Window Size': packet[TCP].window
            }
            log.append(f"[Transport Layer] {tcp_layer}")

        # Raw 데이터 (원시 페이로드)
        if packet.haslayer('Raw'):
            raw_data = packet['Raw'].load
            log.append(f"[Raw Layer] Payload: {raw_data}")

        # 로그를 클라이언트에 전송
        for entry in log:
            socketio.emit('packet_log', entry, to=room)

# 채팅방 나감
@socketio.event
def handle_leave_room(data):
    leave_room(data.get('number'))
    emit('system', f"{data.get('name')}님이 채팅방에서 나갔습니다.", to=data.get('number'))

# 확장자 확인 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 업로드된 파일 처리
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    nickname = request.form.get('nickname', '홍길동')  # 닉네임 받기
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'url': f'/static/uploads/{filename}', 'nickname': nickname}), 200
    else:
        return jsonify({'error': 'File not allowed'}), 400

# 업로드된 파일을 직접 제공하는 라우트
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
