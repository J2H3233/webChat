
const socket = io({
    transports: ['websocket']
});

socket.on('connect', function () {
    console.log('서버에 성공적으로 연결되었습니다!');
});




let roomNumber = null;
// let nickname = "{{nickname}}";
let nicknameDisplay = document.getElementById('nicknameDisplay')
let RoomNumberDisplay = document.getElementById('RoomNumberDisplay')
let selectRoom_button = document.getElementById("selectRoom_button")
let leaveRoom_button = document.getElementById("leaveRoom_button")
let MessageParent = document.getElementById("messages");
let content = document.getElementById("content");

// // 닉네임 설정 임시
// let setName_button = document.getElementById("setName_button")
// setName_button.addEventListener("click", () => {
//     let setName = document.getElementById('setName');
//     nickname = setName.value;
//     if (nickname.trim() != "") {
//         nicknameDisplay.textContent = "nickname : " + nickname;
//         setName.value = " ";
//         setName.disabled = true
//         setName_button.disabled = true;
//     }

// })

// 방 참가 버튼, enter 대응
selectRoom_button.addEventListener("click", () => { joinRoom(); })
document.getElementById('selectRoom').addEventListener("keydown", (e) => {
    if (e.key == "Enter") { joinRoom(); }
})

// 방 참가
function joinRoom() {
    let selectRoom = document.getElementById('selectRoom')
    roomNumber = selectRoom.value
    if (roomNumber.trim() != "") {
        document.getElementById('RoomNumberDisplay').textContent = "방 이름 : " + roomNumber;
        socket.emit('handle_join_room', { number: roomNumber, name: nickname });
        selectRoom.disabled = true
        selectRoom_button.disabled = true
        leaveRoom_button.disabled = false

        selectRoom.value = ""

    }
}

// 방 나가기
leaveRoom_button.addEventListener("click", () => {
    socket.emit('handle_leave_room', { number: roomNumber, name: nickname })
    RoomNumberDisplay.textContent = "방 이름 : "
    selectRoom.disabled = false
    selectRoom_button.disabled = false
    leaveRoom_button.disabled = true
    MessageParent.removeChild(MessageParent.firstChild);

})

// 키입력 버튼, enter 대응
document.getElementById("send_button").addEventListener("click", (e) => {
    e.preventDefault();
    sendMessage();
})
document.getElementById("message-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        sendMessage();
    }
});

// 패킷 로그 수신 및 출력
socket.on('packet_log', (logEntry) => {
    const logDiv = document.getElementById('logCheck');
    const logMessage = document.createElement('div');
    logMessage.textContent = logEntry;
    logDiv.appendChild(logMessage);
});

// 메세지 보내기
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    if (roomNumber && messageInput.value.trim() !== "") {
        socket.emit('send_message_event', {
            number: roomNumber,
            nickname: nickname,
            message: messageInput.value
        });
        messageInput.value = "";
    }
}

// 서버에서 받은 메세지 출력
socket.on('send_message_event', (data) => {
    let newMessage = document.createElement("div");
    let nicknameDiv = document.createElement("div");
    let messageDiv = document.createElement("div");
    if (data.nickname != nickname) {
        newMessage.classList.add("message")
    } else {
        newMessage.classList.add("myMessage")
    }
    nicknameDiv.classList.add("nickname")
    messageDiv.classList.add("messageContent")
    nicknameDiv.textContent = `${data.nickname}`;
    messageDiv.textContent = `${data.message}`;
    newMessage.appendChild(nicknameDiv);
    newMessage.appendChild(messageDiv);
    MessageParent.appendChild(newMessage);

    scrollToBottom();
})
// 스크롤 자동 이동
function scrollToBottom() {
    MessageParent.scrollTop = MessageParent.scrollHeight;
}

// 시스템 메세지 출력
socket.on('system', (system) => {
    let newMessage = document.createElement("div");
    newMessage.classList.add("system");
    newMessage.textContent = `${system}`;
    MessageParent.appendChild(newMessage);
})

// 추가 기능 서랍
let showExtra = document.getElementById("showExtra");
let extra = document.getElementById("extra");
showExtra.addEventListener("click", () => {
    if (extra.style.display === "none") {
        extra.style.display = "block"; // 출력하기
        showExtra.textContent = "-";

    } else {
        extra.style.display = "none"; // 출력 안되게 하기
        showExtra.textContent = "+";
        content.style.paddingRight = "20px";
    }
})

let logCheck = document.getElementById("logCheck")

        // 통신 로그 토글 버튼
        document.getElementById("showLog").addEventListener("click", () => {
            const logDiv = document.getElementById('logCheck');
            logDiv.style.display = logDiv.style.display === "none" ? "block" : "none";
        });