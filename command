docker compose exec app bash  コンテナ入る
ls /dev/video*
docker compose down
docker compose up -d
docker compose down
docker compose up -d --force-recreate
dev/video0   魚眼
dev/video2   通常
# ロボット側で実行
docker compose exec app python3 -m http.server 8080
docker compose restart go2rtc
sudo docker compose restart
