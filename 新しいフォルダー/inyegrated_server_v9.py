import cv2
import cv2.aruco as aruco
import threading
import time
import numpy as np
from flask import Flask, Response, jsonify, request, render_template
from flask_cors import CORS
import robot_2wd_new

app = Flask(__name__)
CORS(app)

robot_state = {"mode": "manual", "status": "stop", "left_rpm": 0.0, "right_rpm": 0.0}

# --- ArUco初期化 (最新のOpenCV 4.7+ に対応した書き方) ---
dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
# Detectorオブジェクトを作成（これにより検出が安定します）
detector = aruco.ArucoDetector(dictionary, parameters)

try:
    robot = robot_2wd_new.Robot2WD("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B0001KJH-if00-port0", 
                                   "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B003725S-if00-port0")
    robot.enable()
except:
    robot = None

def auto_drive_logic(frame):
    """マーカー検知と制御計算"""
    # 1. 念のためグレースケール化
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. マーカー検出 (detectorオブジェクトを使用)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    l_rpm, r_rpm = 0.0, 0.0
    
    if ids is not None:
        # 検出成功：画面に枠を描画
        aruco.drawDetectedMarkers(frame, corners, ids)
        
        # 最初のマーカーの重心を計算
        c = corners[0][0]
        marker_center_x = np.mean(c[:, 0]) # 全角のX座標の平均
        frame_center_x = frame.shape[1] / 2
        
        # 画面中心からの偏差
        diff = marker_center_x - frame_center_x
        
        # 制御パラメータ（まずはゆっくり動く設定）
        base_speed = 70.0 
        turn_gain = 0.15  
        
        l_rpm = base_speed + (diff * turn_gain)
        r_rpm = base_speed - (diff * turn_gain)
        
        # デバッグ用：Beelinkの画面に検出情報を出す
        print(f"Marker Found! ID: {ids[0]} Diff: {diff:.1f}")
        
    return l_rpm, r_rpm

def gen_frames(camera_id):
    cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
    # 高解像度で取り込み
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    # 露出（明るさ）の自動調整を有効にする（暗いと検出できないため）
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    while True:
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue

        # カメラ2かつAUTO RUN時に実行
        if camera_id == 2 and robot_state["mode"] == "auto" and robot_state["status"] == "run":
            try:
                l, r = auto_drive_logic(frame)
                if robot:
                    robot.run(l, r)
                robot_state["left_rpm"], robot_state["right_rpm"] = l, r
            except Exception as e:
                print(f"Logic Error: {e}")

        # 配信用リサイズ
        display_frame = cv2.resize(frame, (320, 240))
        ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 45])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.04)

# --- 以下、Flaskのルート等は変更なし ---
@app.route('/')
def index(): return render_template('robot3_v3.html')

@app.route('/video_feed_<int:id>')
def video_feed(id): return Response(gen_frames(id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    global robot_state
    data = request.json
    if 'mode' in data: robot_state["mode"] = data['mode']
    if 'status' in data:
        robot_state["status"] = data['status']
        if robot_state["status"] == "stop" and robot: robot.run(0, 0)
    
    if robot_state["mode"] == "manual" and robot_state["status"] == "run":
        l, r = float(data.get("left", 0)), float(data.get("right", 0))
        if robot: robot.run(l, r)
        robot_state["left_rpm"], robot_state["right_rpm"] = l, r
    return jsonify({"status": "ok"})

@app.route('/robot_data')
def get_data(): return jsonify(robot_state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)