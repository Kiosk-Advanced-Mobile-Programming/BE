from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app, origins='*')

@app.route("/")                 # 주소 선언
def index():
    return "헬로 파이썬"

if __name__ == "__main__":      # 파일을 직접 실행할 경우 엔트리 포인트 적용
    app.run(debug=True)  # 웹 프로세스 실행, 디버그 모드로, 기본 포트 5000번
