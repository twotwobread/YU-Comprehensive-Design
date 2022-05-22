from flask import Flask, render_template, request, Blueprint
from result import blue_result

####################[ web using flask ]###########################
app = Flask(__name__)

app.register_blueprint(blue_result) # /result
# url을 방문 시 준비된 함수가 트리거되도록 바인딩하기 위해 route() 데코레이터 사용
@app.route("/") # root web site (pothole_server.html)
def index():
    return render_template('pothole_server.html')
    # html 자체를 렌더링 하는 것이 아니라 render_template()를 이용해서 해당 문서를 렌더링해서
    # 반환