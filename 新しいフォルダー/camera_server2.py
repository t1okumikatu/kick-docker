import cv2
from flask import Flask, render_template, Response

app = Flask(__name__)

def gen_frames(camera_id):
    """
    指定されたカメラIDからフレームを取得し、ストリーミング形式に変換するジェネレーター
    """
    # カメラの初期化
    cap = cv2.VideoCapture(camera_id)
    
    # 解像度の設定（ネットワーク負荷を抑えるための推奨値）
    #cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    #cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    # フレームレートの設定
    cap.set(cv2.CAP_PROP_FPS, 20)

    if not cap.isOpened():
        print(f"Error: Camera {camera_id} could not be opened.")
        return

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            else:
                # JPEG形式にエンコード
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                frame = buffer.tobytes()
                
                # マルチパート形式で送信
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cap.release()

@app.route('/')
def index():
    return "Robot Camera Server is Running."

# --- 【重要】カメラ0番（ウェブ広角）用エンドポイント ---
@app.route('/video_feed_0')
def video_feed_0():
    return Response(gen_frames(0),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- 【重要】カメラ2番（通常カメラ）用エンドポイント ---
@app.route('/video_feed_2')
def video_feed_2():
    return Response(gen_frames(2),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# 以前のパスも予備として残しておく場合（404回避）
@app.route('/video_feed')
def video_feed_default():
    return Response(gen_frames(0),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # 外部（HTML側）からのアクセスを許可するため host='0.0.0.0' を指定
    # ポートはHTML側の設定と一致させる
    app.run(host='0.0.0.0', port=5000, threaded=True)