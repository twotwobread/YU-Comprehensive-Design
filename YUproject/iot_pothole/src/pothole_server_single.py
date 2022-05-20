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
# - update version 2.0 (2022.05.19)
#   다중 접속을 허용하고 full duplex로 구현, 포트홀이 인식된 횟수를 이용하여 우선순위 
#
'''
import PyKakao
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
from collections import deque

IP="IP"
API_KEY = "KEY"
KL = PyKakao.KakaoLocal(API_KEY)
CONN_DB = pymysql.connect(host='127.0.0.1', user='root', password='password', db='pothole', charset='utf8')
CUR_DB = CONN_DB.cursor()
LOCK = threading.Lock()

####################[ web using flask ]###########################

webRemoteControlServer = Flask(__name__)

@webRemoteControlServer.route("/") # root web site (pothole_server.html)
def index():
    return render_template('pothole_server.html')

@webRemoteControlServer.route("/result", methods=["GET", "POST"])
def getDataFromDB(): # view DB data to web
    if request.method == "POST":
        address = request.form
    total_addr=""
    total_addr = address['1']+"%"+address['2']+"%"+address['3']
    real_addr = "%"+total_addr+"%"
    print(real_addr)
    sql = "SELECT * FROM img_path WHERE addr LIKE %s ORDER BY priority DESC"
    CUR_DB.execute(sql, real_addr)
    CONN_DB.commit()
    result = CUR_DB.fetchall()
    print(result)
   
    return render_template('pothole_dataPrint.html', data=result)

def save_data(data): # saving data
    img_path, latitude, longitude, sql_path, img = data
    sql_path="SELECT * FROM img_path WHERE img_path=%s;"
    CUR_DB.execute(sql_path, img_path)
    length = CUR_DB.fetchall()
    if len(length) == 0:
        cv2.imwrite(img_path, img)
        print("save in")
        result = KL.geo_coord2address(latitude, longitude)
        if result['meta']['total_count']!=0:
            address=result['documents'][0]['address']['address_name']
            print("database start")
            sql = "INSERT INTO img_path ( img_path, latitude, longitude, addr , priority) VALUES (%s, %s, %s, %s, %s);"
            val = (img_path, latitude, longitude, address,0)
            CUR_DB.execute(sql, val)
            CONN_DB.commit()
        else: # can't point in map
            print("잘못된 위도 경도 입니다 !!")
    else:
        for i in length:
            sql_path="UPDATE img_path SET priority=%s WHERE img_path=%s;"
            CUR_DB.execute(sql_path, (i[4]+1, img_path))
            CONN_DB.commit()
        # 우선순위 증가 DB
                                                
##################[ socket & data manage ]########################
class ServerSocket: # class for communication with clients
    CLIENT_INFO = dict()
    def __init__(self, ip, port): 
        self.TCP_IP = ip
        self.TCP_PORT = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.TCP_IP, self.TCP_PORT))
        self.sock.listen()
        self.receiveThread = threading.Thread(target=self.connect) # receive thread start
        self.receiveThread.start()

    def connect(self):
        while True:
            print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is open')
            conn, addr = self.sock.accept()
            print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is connected with client')
            self.CLIENT_INFO[addr]=ClientData(conn, addr)
            print(self.CLIENT_INFO)
            time.sleep(0.1)
    def destroy(self, addr):
        instance = self.CLIENT_INFO.pop(addr)
        del instance
        print(self.CLIENT_INFO)
        print("complete")

    def socketClose(self):
        self.sock.close()
        print(u'Server socket [ TCP_IP: ' + self.TCP_IP + ', TCP_PORT: ' + str(self.TCP_PORT) + ' ] is close')


class ClientData(ServerSocket):
    def __init__(self, conn, addr):
        print("client")
        self.gps_latitude = 0
        self.gps_longitude = 0
        self.conn = conn
        self.addr = addr
        self.que = deque()
        self.sendThread = threading.Thread(target=self.send) # receive thread start
        self.sendThread.start()
        self.receiveThread = threading.Thread(target=self.receive) # receive thread start
        self.receiveThread.start()
    def setGpsLatitude(self, lat):
        self.gps_latitude = lat
    def setGpsLongitude(self, lng):
        self.gps_longitude = lng
    def getGpsLatitude(self):
        return self.gps_latitude
    def getGpsLongitude(self):
        return self.gps_longitude

    def send(self):
        print("receive run")
        while True:
            if self.que:
                self.conn.send("ACK".encode())
                self.que.popleft()
            time.sleep(0.1)           
    def receive(self): # receive images to clients
        global API_KEY, CONN_DB, CUR_DB, LOCK
        print("receive run")
        try:
            while True:
                length = self.recvall(self.conn, 64)
                length = self.recvall(self.conn, 64) # receive length of one image
                length = length.decode('utf-8') # decode length data because encoded length data fly away 
                stringData = self.recvall(self.conn, int(length)) 
                stringPosition = self.recvall(self.conn, 64)
                lat, lng = stringPosition.decode('utf-8').split('/')
                self.setGpsLatitude(round(float(lat),6)); self.setGpsLongitude(round(float(lng),6)) # round up because of error range
                print('receive time: '+datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                data = numpy.frombuffer(base64.b64decode(stringData), numpy.uint8) 
                print("latitude : ", self.gps_latitude)
                print("longitude : ", self.gps_longitude)
                decimg = cv2.imdecode(data, 1) # get img data
                path=(self.gps_latitude)+'_'+str(self.gps_longitude)+'.jpg'
                sql_path="SELECT * FROM img_path WHERE img_path=%s;"
                val = (path, lat, lng, sql_path, decimg)
                LOCK.acquire()
                save_data(val)
                LOCK.release()
                self.que.append(1)
                #cv2.imshow("image", decimg)
                #cv2.waitKey(1)
                time.sleep(0.1)

        except Exception as e:
            print(e)
            super().destroy(self.addr)

    def recvall(self, conn, bytes): # 데이터를 원하는 길이만큼 받는 함수.
        buf = b''
        print("receive all")
        while bytes:
            newbuf = conn.recv(bytes)
            if not newbuf: return None
            buf+=newbuf
            bytes -= len(newbuf)
        return buf





def main(): # web server run
    try:
        webRemoteControlServer.run(host=IP, port=8080)
    except Exception as e:
        print(e)
        print("End")

#########################[main]##############################

if __name__ == "__main__":
    #save_data(("0",0.0,0.0,"0",0))
    gps=ServerSocket(IP, 20)
    main()
