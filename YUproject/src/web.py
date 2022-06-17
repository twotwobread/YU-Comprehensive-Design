from flask import Flask, render_template, request, Blueprint
from result import blue_result
from init.variable import *
import os

####################[ web using flask ]###########################
app = Flask(__name__)

app.register_blueprint(blue_result) # /result
# url을 방문 시 준비된 함수가 트리거되도록 바인딩하기 위해 route() 데코레이터 사용
@app.route("/") # root web site (pothole_server.html)
def index():
    return render_template('pothole_server.html')
    # html 자체를 렌더링 하는 것이 아니라 render_template()를 이용해서 해당 문서를 렌더링해서
    # 반환

@app.route('/delete/<img_path>', methods=['POST'])
def delete(img_path):
    sql_path="DELETE FROM img_path WHERE img_path=%s;"
    CUR_DB.execute(sql_path, img_path)
    CONN_DB.commit()
    os.remove('static/'+img_path)
    return index()