import pickle
from re import L
import time
import threading
import socket
import cv2
import numpy
import base64
from datetime import datetime
from collections import deque
from . import variable
import os
###################[ Server for pothole data ]####################
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
        print("receive run")
        try:
            while True:
                length = self.recvall(self.conn, 64) 
                length = length.decode('utf-8') 
                stringData = self.recvall(self.conn, int(length))
                decimg = pickle.loads(stringData, fix_imports=True, encoding="bytes")
                stringPosition = self.recvall(self.conn, 64)
                lat, lng = stringPosition.decode('utf-8').split('/')
                self.setGpsLatitude(round(float(lat),5)); self.setGpsLongitude(round(float(lng),5)) 
                # print("latitude : ", self.gps_latitude)
                # print("longitude : ", self.gps_longitude)
                print("latitude : ", 35.83061)
                print("longitude : ", 128.75411)
                #path=str(self.gps_latitude)+'_'+str(self.gps_longitude)+'.jpg'
                path = str(35.83061)+'_'+str(128.75411)+'.jpg'
                sql_path="SELECT * FROM img_path WHERE img_path=%s;"
                #val = (path, self.gps_latitude, self.gps_longitude, sql_path, decimg)
                val = (path, 35.83061, 128.75411, sql_path, decimg)
                variable.LOCK.acquire()
                save_data(val)
                variable.LOCK.release()
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
def save_data(data): # saving data
    img_path, latitude, longitude, sql_path, img = data
    variable.CUR_DB.execute(sql_path, img_path)
    length = variable.CUR_DB.fetchall()
    if len(length) == 0: #위도 경도를 이용해서 검색
        result = variable.KL.geo_coord2address(longitude, latitude)
        if result['meta']['total_count']!=0:
            cv2.imwrite("static/"+img_path, img)
            address=result['documents'][0]['address']['address_name']
            print("database start")
            sql = "INSERT INTO img_path ( img_path, latitude, longitude, addr , priority) VALUES (%s, %s, %s, %s, %s);"
            val = (img_path, latitude, longitude, address,0)
            variable.CUR_DB.execute(sql, val)
            variable.CONN_DB.commit()
        else: # can't point in map
            print("잘못된 위도 경도 입니다 !!")
    else:
        print("중복된 포트홀입니다")
        for i in length:
            sql_path="UPDATE img_path SET priority=%s WHERE img_path=%s;"
            variable.CUR_DB.execute(sql_path, (i[4]+1, img_path))
            variable.CONN_DB.commit()
        # 우선순위 증가 DB