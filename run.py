from flask import Flask, jsonify, request

# Flask객체생성 이걸 보고 어디서 실행되는지 판단
app = Flask(__name__)

# 기본 라우팅 페이지
@app.route('/')
def home():
    return jsonify({"message": "Kiosk API is running!"})


# POST 방식으로 /api/users 주소로 요청시 함수 실행
@app.route('/api/users', methods=['POST'])
def create_user():
     # 클라이언트(앱, 프론트엔드)가 보낸 JSON 데이터를 읽어옴
    data = request.get_json()

    print(data)



# 파이썬 파일을 직접 실행했을 때만 아래 코드가 작동하게 하는 조건문
# (다른 파일에서 import될 때는 실행되지 않게 함)
if __name__ == '__main__':
    app.run(debug=True)  # 개발모드, 기본포트 5000
