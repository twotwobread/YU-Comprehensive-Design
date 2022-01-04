'''
#
# filename : pothole_server.py
# server에 다수의 client가 들어올때를 고려 ( 미완 )
# author : 이수영 ( 2021.12.28 )
# - version 1.0 (2021.12.28), 
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



webRemoteControlServer = Flask(__name__)

@webRemoteControlServer.route("/") # root web site (pothole_server.html)
def index():
    return render_template('pothole_server.html')

@webRemoteControlServer.route("/Daegu") # root web site (pothole_server.html)
def Daegu_fuction():
    pass

#################################################################################

class ServerSocket(threading.Thread): # class for communication with clients
    def __init__(self, socket): # init
        super().__init__()
        self.SOCKET_DATA=[]
        self.sock = socket
        self.gps_latitude = 0
        self.gps_longitude = 0
        
    def run(self):
        global count
        self.socketOpen()
        count = count+1
        create_thread(self.sock)
        self.receiveThread=threading.Thread(target=self.receiveImages)
        self.receiveThread.daemon=True
        self.receiveThread.start()

    def setGpsLatitude(self, lat):
        self.gps_latitude = lat

    def setGpsLongitude(self, lng):
        self.gps_longitude = lng

    def getGpsLatitude(self):
        return self.gps_latitude

    def getGpsLongitude(self):
        return self.gps_longitude

    def receiveImages(self): # receive images to clients
        try:
            while True:
                length = self.recvall(self.conn, 64) # first, receive length of one image
                length = length.decode('utf-8') # decode length data because encoded length data fly away 
                stringData = self.recvall(self.conn, int(length)) # 길이만큼 이미지 데이터를 받는다.
                stringPosition = self.recvall(self.conn, 64)
                lat, lng = stringPosition.decode('utf-8').split('/')
                self.setGpsLatitude(float(lat)); self.setGpsLongitude(float(lng))
                print('receive time: '+datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                data = numpy.frombuffer(base64.b64decode(stringData), numpy.uint8) # 이미지 데이터를 받으면 마찬가지로 encoding 되어있으니까 decode해준다.
                #print(type(data))
                decimg = cv2.imdecode(data, 1)
                path='D:/pothole_img/'+lat+'_'+lng+'.jpg' 
                cv2.imwirte(path, decimg)
                base_url='https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x='+lng+"&y="+lat+'&input_coord=WGS84'
                val = (path, lat, lng, base_url)
                self.SOCKET_DATA.append(val)

                #headers={'Authorization':'KakaoAK '+self.api_key}
                #api_req=requests.get(base_url, headers=headers)
                #jsonObjects=json.loads(api_req.text)
                #address=jsonObjects.get('documents')[0]['address_name']

                #sql = "insert into img_path(img_num, img_path, latitude, longitude, address) values (%s, %s, %s, %s, %s)"
                #val = (path, lat, lng, address)
                #self.cur_DB.execute(sql, val)
                #cv2.imshow("image", decimg)
                #cv2.waitKey(1)

        except Exception as e: # 예외 발생 시 소켓을 죽였다가 다시 열어서 연결되기를 기다린다.
            print(e)
            self.socketClose()
            cv2.destroyAllWindows()
            #self.socketOpen()
            #self.receiveThread = threading.Thread(target=self.receiveImages)
            #self.receiveThread.start()
    def recvall(self, conn, bytes):
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
        self.conn, self.addr = self.sock.accept()
        print('Server socket is connected with client[ IP: '+str(self.addr)+' ]')

def create_thread(socket):
    global count, socket_list
    socket_list.append(ServerSocket(socket))
    socket_list[count].deamon = True
    socket_list[count].start()

def main(): # web server run
    try:
        webRemoteControlServer.run(host="165.229.185.201", port=8080)
    except Exception as e:
        print(e)
        print("End")


API_KEY = "a00649b953ccf10495e69f5fbae7cd73"
CONN_DB = pymysql.connect(host="localhost", user='root', password="qhal9137@", charset='utf8', db='pothole')
CUR_DB = CONN_DB.cursor()
if __name__ == "__main__":
    socket_list = []
    count = 0
    IP = "165.229.185.201"
    PORT = 9090
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((IP, PORT))
    sock.listen(1)
    print('Server socket [ TCP_IP: ' + str(IP) + ', TCP_PORT: ' + str(PORT) + ' ] is open')
    create_thread(sock)
    #gps=ServerSocket("165.229.185.201", 9090)
    main()