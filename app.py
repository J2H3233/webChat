import eventlet
eventlet.monkey_patch()
import re
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import pymysql
from scapy.all import sniff, IP, TCP, Ether
import threading
import os

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# Flask 및 환경 설정
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = '비밀번호 설정'
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
CORS(app)
socketio = SocketIO(app, async_mode='eventlet')

# Flask-Login 설정
login_manager = LoginManager(app)
login_manager.login_view = 'render_login_page'

# 데이터베이스 연결
db = pymysql.connect(host='43.203.195.110', port=3306, user='id_j2h', password='Password_j2h!12345', database='chat_app')
cursor = db.cursor()

# Flask-Login 사용자 클래스
class User(UserMixin):
    def __init__(self, user_index, id, nickname, email):
        self.user_index = user_index  # Primary Key
        self.id = id                  # 로그인 ID
        self.nickname = nickname
        self.email = email

    def get_id(self):
        """Flask-Login이 사용자 세션을 관리하기 위해 사용"""
        return str(self.user_index)

# Flask-Login 사용자 로드
@login_manager.user_loader
def load_user(user_index):
    """
    사용자 ID(user_index)를 기반으로 사용자 객체 반환
    """
    sql = "SELECT user_index, id, nickname, email FROM users WHERE user_index=%s"
    cursor.execute(sql, (user_index,))
    result = cursor.fetchone()

    if result:
        return User(user_index=result[0], id=result[1], nickname=result[2], email=result[3])
    return None

# 라우트: 로그인 페이지
@app.route('/')
def render_login_page():
    if current_user.is_authenticated:  # 이미 로그인된 상태라면
        return redirect(url_for('render_chat_page'))  # 채팅 페이지로 리다이렉트
    return render_template('login.html')

# 라우트: 회원가입 페이지
@app.route('/signup/')
def render_signup_page():
    return render_template('signup.html')

@app.route('/chat/')
@login_required
def render_chat_page():
    # 전달받은 nickname을 사용
    nickname = request.args.get('nickname', current_user.nickname)
    return render_template('chat.html', nickname=nickname)

# 로그인 처리
@app.route('/login/', methods=['POST'])
def login():
    # HTML에서 전달된 데이터 가져오기
    login_id = request.form.get('id')  # 사용자가 입력한 ID
    password = request.form.get('password')  # 사용자가 입력한 비밀번호

    # 데이터베이스 쿼리
    sql = "SELECT user_index, id, nickname, email FROM users WHERE id=%s AND password=%s"
    cursor.execute(sql, (login_id, password))
    result = cursor.fetchone()

    # 쿼리 결과 확인
    if result:
        # 로그인 성공: 사용자 세션 생성
        user = User(user_index=result[0], id=result[1], nickname=result[2], email=result[3])
        login_user(user)

        # 채팅 페이지로 닉네임 전달
        return redirect(url_for('render_chat_page', nickname=user.nickname))
    else:
        # 로그인 실패
        flash("아이디 또는 비밀번호가 잘못되었습니다.", "danger")
        return redirect(url_for('render_login_page'))

# 로그아웃 처리
@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('render_login_page'))

# 회원가입 처리
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

# Socket.IO 이벤트: 채팅방 나감 처리
@socketio.event
def handle_leave_room(data):
    leave_room(data.get('number'))
    emit('system', f"{data.get('name')}님이 채팅방에서 나갔습니다.", to=data.get('number'))













# 클라이언트 - 서버 연결 이벤트
@socketio.on('connect')
def handle_connect():
    print('클라이언트가 서버에 연결되었습니다!')

@socketio.on('send_image_event')
def handle_send_image_event(data):
    room = data.get('room')  # 방 번호 가져오기
    url = data.get('url')
    nickname = data.get('nickname')
    
    # 특정 방으로 이미지 브로드캐스트
    emit('send_image_event', {'url': url, 'nickname': nickname, 'room': room}, to=room)


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
        log.append(f"[응용층] {nickname}의 메세지: {message}")

        # 데이터 링크 계층 (Ether)
        if Ether in packet:
            if packet[Ether].type == 0x0800:  # IPv4
                packet_type = "IPv4"
            elif packet[Ether].type == 0x0806:  # ARP
                packet_type = "ARP"
            elif packet[Ether].type == 0x0842:  # Wake-on-LAN
                packet_type = "Wake-on-LAN"
            elif packet[Ether].type == 0x86DD:  # IPv6
                packet_type = "IPv6"
            elif packet[Ether].type == 0x8808:  # Ethernet Flow Control
                packet_type = "Ethernet Flow Control"
            elif packet[Ether].type == 0x88CC:  # LLDP
                packet_type = "LLDP"
            else:  # Unknown type
                packet_type = "Unknown"
            src_mac = ":".join(packet[Ether].src.split(":")[:3]) + ":xx:xx"
            dst_mac = ":".join(packet[Ether].dst.split(":")[:3]) + ":xx:xx"
            ether_layer = {
                '출발지 MAC주소': src_mac,
                '목적지 MAC주소': dst_mac,
                '패킷 유형': f"{hex(packet[Ether].type)} ({packet_type})",
                '체크섬': hex(packet[Ether].chksum) if hasattr(packet[Ether], 'chksum') else "N/A"
            }
            log.append(f"[데이터 링크층] {ether_layer}")

        # 네트워크 계층 (IP)
        if IP in packet:
            if packet[IP].proto == 1:  # ICMP
                protocol = "ICMP"
            elif packet[IP].proto == 6:  # TCP
                protocol = "TCP"
            elif packet[IP].proto == 17:  # UDP
                protocol = "UDP"
            elif packet[IP].proto == 41:  # IPv6 Encapsulation
                protocol = "IPv6 Encapsulation"
            elif packet[IP].proto == 50:  # ESP
                protocol = "ESP"
            elif packet[IP].proto == 89:  # OSPF
                protocol = "OSPF"
            else:  # Unknown protocol
                protocol = "Unknown"

            src_ip = ".".join(packet[IP].src.split(".")[:2]) + ".x.x"
            dst_ip = ".".join(packet[IP].dst.split(".")[:2]) + ".x.x"

            ip_layer = {
                '출발지 IP': src_ip,
                '목적지 IP': dst_ip,
                '패킷 생존시간': packet[IP].ttl,  # Time-to-Live
                '프로토콜': f"{packet[IP].proto} ({protocol})",
                '헤더 길이': packet[IP].ihl * 4,  # IP Header Length (bytes)
                '전체 길이': packet[IP].len,  # Total Length (bytes)
                'ID': packet[IP].id,
                '체크섬': hex(packet[IP].chksum)  # IP 체크섬
            }
            log.append(f"[네트워크층] {ip_layer}")

        # 전송 계층 (TCP)
        if TCP in packet:
            tcp_layer = {
                '출발 포트': packet[TCP].sport,
                '도착 포트': packet[TCP].dport,
                '순서 번호': packet[TCP].seq,
                '확인 응답 번호': packet[TCP].ack,
                '플래그': {
                    'URG': packet[TCP].flags & 0x20 != 0,
                    'ACK': packet[TCP].flags & 0x10 != 0,
                    'PSH': packet[TCP].flags & 0x08 != 0,
                    'RST': packet[TCP].flags & 0x04 != 0,
                    'SYN': packet[TCP].flags & 0x02 != 0,
                    'FIN': packet[TCP].flags & 0x01 != 0
                },
                '윈도우 크기': packet[TCP].window,
                '체크섬': hex(packet[TCP].chksum)  # IP 체크섬
            }
            log.append(f"[전송층] {tcp_layer}")

        # 캡처하지 못한 계층에 대한 예외 처리
        else:
            log.append("TCP 계층 정보 없음")

        # 로그를 클라이언트에 전송
        for entry in log:
            socketio.emit('packet_log', entry, to=room)



def safe_filename(filename):
    # 파일 이름에서 허용되지 않는 문자를 제거 (알파벳, 숫자, 밑줄, 하이픈, 마침표만 허용)
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return safe_name.strip("._")  # 앞뒤 불필요한 마침표, 밑줄 제거

# 확장자 확인 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    nickname = request.form.get('nickname', '홍길동')  # 닉네임 받기
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = safe_filename(file.filename)  # 안전한 파일 이름 생성
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)  # 파일 저장
        return jsonify({'url': f'/static/uploads/{filename}', 'nickname': nickname}), 200
    else:
        return jsonify({'error': 'File not allowed'}), 400
# 업로드된 파일을 직접 제공하는 라우트
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
