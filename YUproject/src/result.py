from flask import Blueprint, request, render_template
from init import variable

blue_result = Blueprint("result", __name__, url_prefix="/result")

@blue_result.route("", methods=["GET", "POST"])
def getDataFromDB(): # view DB data to web
    if request.method == "POST":
        address = request.form
    total_addr=""
    total_addr = address['1']+"%"+address['2']+"%"+address['3']
    real_addr = "%"+total_addr+"%"
    print(real_addr)
    sql = "SELECT * FROM img_path WHERE addr LIKE %s ORDER BY priority DESC"
    variable.CUR_DB.execute(sql, real_addr)
    variable.CONN_DB.commit()
    result = variable.CUR_DB.fetchall()
    print(result)
    return render_template('result/new.html', data=result)
    
@blue_result.route("/details/<img_path>/<float:latitude>/<float:longitude>/<addr>/", methods=['GET', 'POST'])
def potholeImg(img_path, latitude, longitude, addr):
    return render_template("result/details/test.html", data=(img_path, latitude, longitude, addr))

