'''
#
# filename : pothole_server_single.py
# jetson nano에서 pothole을 인식하여 img 파일과 함께 gps 측정값을 보내면
# 이 server에서 해당 정보들을 DB에 저장하고 웹에서 해당 데이터를 이용하여
# pothole 위치를 쉽게 파악하여 유지/보수가 가능하게 만듬.
# author : 이수영 ( 2021.12.27 )
# - version 1.0 (2021.12.27), 
#   현재 하나의 client와 socket을 통한 통신을 가능하게 만듬
#   img, gps 값을 다 받아옴. (web 구성x)
# - update version 1.0 (2021.12.29),
#   data를 받아 db 저장만 했는데 web에 data 출력 update
#
'''

from flask import *
import time
import json
import requests
import threading
import os
import socket
import cv2
import numpy
import base64
from datetime import datetime
import pymysql

IP=""
API_KEY = ""
CONN_DB = pymysql.connect(host='127.0.0.1', user='root', password='', db='pothole', charset='utf8')
CUR_DB = CONN_DB.cursor()
SOCKET_DATA = []
LOCK = threading.Lock()

####################[ web server using flask ]###########################

webRemoteControlServer = Flask(__name__)

@webRemoteControlServer.route("/") # root web site (pothole_server.html)
def index():
    return render_template('pothole_server.html')

@webRemoteControlServer.route("/result", methods=['GET', 'POST']) # root web site (pothole_dataPrint.html)
def result_fuction():
    if request.method == 'POST':
        address = request.form
    print(len(address))
    # pothole_server.html에서 request data가 비어있으면 
    # 검색 시 문제가 생길 수 있다 생각하여 넣은 구문
    total_addr="";
    cnt = 0
    list_addr = []
    if address['1']!="" and address['2']=="" and address['3']!="":
        total_addr = address['1']+"%"+address['3']
    else:
        for i in range(len(address)):
            str_num = str(i+1)
            if address[str_num] == "":
                pass
            else:
                if cnt==0:
                    total_addr=address[str_num]
                else:

                    total_addr+=" "+address[str_num]
                cnt+=1
    real_addr = "%"+total_addr+"%"
    print(real_addr)
    sql = "SELECT * FROM img_path WHERE addr LIKE %s"
    CUR_DB.execute(sql, real_addr) # get DB data that addr(attribute) equal to real_addr 
    CONN_DB.commit()
    result = CUR_DB.fetchall()
    print(result)
   
    return render_template('pothole_dataPrint.html', data=result)

##################[ socket & data manage ]########################

class ServerSocket: # class for communication with clients
    def __init__(self, ip, port): # init
        self.gps_latitude = 0
        self.gps_longitude = 0
        self.TCP_IP = ip
        self.TCP_PORT = port
        self.socketOpen() # server socket open 
        self.receiveThread = threading.Thread(target=self.receiveImages)
        self.receiveThread.start()  # receive thread start

    def setGpsLatitude(self, lat):
        self.gps_latitude = lat

    def setGpsLongitude(self, lng):
        self.gps_longitude = lng

    def getGpsLatitude(self):
        return self.gps_latitude

    def getGpsLongitude(self):
        return self.gps_longitude

    def receiveImages(self): # receive images to clients
        global SOCKET_DATA, API_KEY, CONN_DB, CUR_DB, LOCK
        cnt=0.0
        try:
            while True:
                length = self.recvall(self.conn, 64) # first, receive length of one image
                length = length.decode('utf-8') # decode length data because encoded length data fly away 
                stringData = self.recvall(self.conn, int(length)) 
                stringPosition = self.recvall(self.conn, 64)
                lat, lng = stringPosition.decode('utf-8').split('/')
                self.setGpsLatitude(round(float(lat),5)); self.setGpsLongitude(round(float(lng),5)) # round up because of error range
                print('receive time: '+datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                data = numpy.frombuffer(base64.b64decode(stringData), numpy.uint8)
                print("latitude : ", self.gps_latitude)
                print("longitude : ", self.gps_longitude)
                decimg = cv2.imdecode(data, 1)
                print("get img file !!!!")
                base_url='https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x='+str(self.gps_longitude)+"&y="+str(self.gps_latitude)+'&input_coord=WGS84'
                path=str(self.gps_latitude)+'_'+str(self.gps_longitude)+'.jpg' 
                sql_path="SELECT * FROM img_path WHERE img_path=%s;"
                CUR_DB.execute(sql_path, path)
                result = CUR_DB.fetchall()
                if len(result) == 0: # data 중복 저장을 막기 위함.
                    cv2.imwrite("static/"+path, decimg)
                    val = (path, str(self.gps_latitude), str(self.gps_longitude), base_url)
                    
                    LOCK.acquire()
                    SOCKET_DATA.append(val)
                    LOCK.release()
                else:
                    print("같은 위치의 포트홀입니다!!!!!")
                #cv2.imshow("image", decimg)
                #cv2.waitKey(1)

        except Exception as e: 
            print(e)
            self.socketClose()
            cv2.destroyAllWindows()
            self.socketOpen()
            self.receiveThread = threading.Thread(target=self.receiveImages)
            self.receiveThread.start()

    def recvall(self, conn, bytes):  # 데이터를 원하는 길이만큼 받는 함수.
        buf = b''
        while bytes:
            newbuf = conn.recv(bytes)
            if not newbuf: return None
            buf+=newbuf
            bytes -= len(newbuf)
        return buf
    
    def socketClose(self):
        self.sock.close()
        print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is close')

    def socketOpen(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.TCP_IP, self.TCP_PORT))
        self.sock.listen(1)
        print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is open')
        self.conn, self.addr = self.sock.accept()
        print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is connected with client')


def save_data():
    print("save in")
    global API_KEY, CONN_DB, CUR_DB, SOCKET_DATA,LOCK
    while True:
        for i in SOCKET_DATA: # SOCKET_DATA에 값이 있으면 DB에 저장
            print(SOCKET_DATA)
            headers={'Authorization':'KakaoAK '+API_KEY}
            api_req=requests.get(i[3], headers=headers)
            jsonObjects=json.loads(api_req.text)
            if jsonObjects.get('msg') == None:
                address=jsonObjects.get('documents')[0]['address_name']
                print("database start")
                LOCK.acquire()
                sql = "INSERT INTO img_path ( img_path, latitude, longitude, addr ) VALUES (%s, %s, %s, %s);"
                val = (i[0], i[1], i[2], address)
                CUR_DB.execute(sql, val)
                CONN_DB.commit()
                LOCK.release()
            else:
                print("잘못된 위도 경도 입니다 !!")
            SOCKET_DATA.pop(0)
            print("database end")
        time.sleep(0.1) 

def main(): # web server run
    try:
        webRemoteControlServer.run(host='165.229.185.201', port=8080)
    except Exception as e:
        print(e)
        print("End")

#########################[main]##############################

if __name__ == "__main__":
    save_data_thread = threading.Thread(target=save_data)
    save_data_thread.start()
    gps=ServerSocket(IP, 20)
    main()

