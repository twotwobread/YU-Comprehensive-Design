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

# IP, API_KEY, DB 연결, 소켓으로 보낼 데이터를 위한 버퍼, 임계구역을 위한 초기 세팅
IP=""
API_KEY = ""
CONN_DB = pymysql.connect(host='127.0.0.1', user='root', password='', db='pothole', charset='utf8')
CUR_DB = CONN_DB.cursor()
SOCKET_DATA = []
LOCK = threading.Lock()

####################[ web server using flask ]###########################

# flask를 이용해서 web server 기능을 구현하기 위함.
webRemoteControlServer = Flask(__name__)

@webRemoteControlServer.route("/") # root web site (pothole_server.html) # pothole_server.html : 검색 기능이 있는 초기 화면을 띄움.
def index():
    return render_template('pothole_server.html')

@webRemoteControlServer.route("/result", methods=['GET', 'POST']) # root web site (pothole_dataPrint.html)
def result_fuction():
    if request.method == 'POST': # 검색 기능을 사용할 때 무조건 post를 이용
        address = request.form
    print(len(address))
    # pothole_server.html에서 request data가 비어있으면 
    # 검색 시 문제가 생길 수 있다 생각하여 넣은 구문
    total_addr=""; # 최종적으로 찾고 싶은 주소를 담기 위한 변수
    cnt = 0
    list_addr = []
    # 결과적으로는 post로 날라온 address 정보를 이용해서 쿼리문을 짜고 DB에서 값을 들고 와야함. ( address는 array 형식으로 날라옴 )
    # 만약 address 중간이 ""가 아니라도 '%' 얘를 붙여도 되는지 생각해보자
    # 경상북도%경산시%삼풍동 이렇게 해도 될거 같은데 일단 확인을 해봐야할 부분인 것 같다.
    # 만약 address 중간이 ""면 '%' 이놈이 무조건 필요할 것이다.
    # 그걸 위한 if문인 것 같다.
    if address['1']!="" and address['2']=="" and address['3']!="":
        total_addr = address['1']+"%"+address['3']
    else: # 중간만 ""인 경우 말고 전부.
        for i in range(len(address)):
            str_num = str(i+1)
            if address[str_num] == "": # 이부분을 만나면 마지막이라는 의미.
                pass
            else: # 마지막이 아니면
                if cnt==0: # 맨 처음인 경우를 생각
                    total_addr=address[str_num] # total address에 주소를 넣음
                else:# 맨 처음이 아니면
                    total_addr+=" "+address[str_num] # 공백을 넣기 위함.
                cnt+=1 # cnt 하나씩 증가시키면서 
    real_addr = "%"+total_addr+"%" # 마지막으로 앞뒤에 '%'를 붙여줌으로 다 찾을 수 있게 하는데
    # 이걸 봤을 때, %경상북도%경산시%삼풍동% 이것도 가능할꺼 같다.
    print(real_addr)
    sql = "SELECT * FROM img_path WHERE addr LIKE %s" # DB에서 데이터를 찾기 위한 쿼리문
    CUR_DB.execute(sql, real_addr) # get DB data that addr(attribute) equal to real_addr 
    # 모든 데이터를 찾기위해 '%'를 이용 해서 쿼리문 완성
    CONN_DB.commit() # DB로 접근
    result = CUR_DB.fetchall() # 해당하는 array를 들고옴.
    print(result)
   
    return render_template('pothole_dataPrint.html', data=result) # data로 result를 보내면서 pothole_dataPrint.html 띄움.

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
                # 이 부분은 사진을 받기 위한 부분 사진을 받기 위해서 사진의 크기가 있으니까 잘려서 날라올테니까 먼저 잘려날라오는 길이를 받고
                # decode해서 길이를 파악한 후 길이만큼 데이터를 전부 다 받아서 버퍼에 넣어놓고 decode해서 이용
                # 그리고 gps 정보도 소켓을 이용해서 받아주는 부분.
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
                # 아래 라인이 카카오 지도 api에 위도, 경도를 넣어서 request를 하기 위한 url을 만드는 라인
                base_url='https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x='+str(self.gps_longitude)+"&y="+str(self.gps_latitude)+'&input_coord=WGS84'
                # 이미지를 저장하기 위해서 이미지의 이름을 위도, 경도를 이용해서 만듬.
                # 소숫점 5번째까지 trunk하여 대략 1m 이내의 포트홀은 같은 포트홀로 인식.
                path=str(self.gps_latitude)+'_'+str(self.gps_longitude)+'.jpg' 
                sql_path="SELECT * FROM img_path WHERE img_path=%s;" # 쿼리문을 작성하고 이미지가 있는 지 먼저 확인 
                CUR_DB.execute(sql_path, path)
                result = CUR_DB.fetchall()
                if len(result) == 0: # data 중복 저장을 막기 위함. 이미지가 없는 경우, 이 부분 개선하면 좋을 듯.
                    cv2.imwrite("static/"+path, decimg) # static 디렉토리에 이미지를 저장
                    val = (path, str(self.gps_latitude), str(self.gps_longitude), base_url) # DB에 넣을 정보를 튜플로 구성
                    
                    LOCK.acquire()
                    SOCKET_DATA.append(val) # 소켓 데이터에 넣음, 이 부분도 개선 가능할 것 같음.
                    LOCK.release()
                else: # 이미지가 존재하는 경우
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
            api_req=requests.get(i[3], headers=headers) # kakao api에 실제로 request하는 부분
            jsonObjects=json.loads(api_req.text)
            if jsonObjects.get('msg') == None: # 제대로 값을 들고 왔는지를 확인하기 위한 부분.
                address=jsonObjects.get('documents')[0]['address_name'] # 위도 경도에 맞는 주소를 가져오는 부분.
                print("database start")
                LOCK.acquire()
                sql = "INSERT INTO img_path ( img_path, latitude, longitude, addr ) VALUES (%s, %s, %s, %s);" # 주소까지 포함해서 쿼리문 작성
                val = (i[0], i[1], i[2], address) # DB에 저장.
                CUR_DB.execute(sql, val)
                CONN_DB.commit()
                LOCK.release()
            else:
                print("잘못된 위도 경도 입니다 !!")
            SOCKET_DATA.pop(0) # 맨 처음들어온 주소부터 처리하기 위함.
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
    save_data_thread = threading.Thread(target=save_data) # 저장하는 부분이랑 데이터를 받는 부분을 따로 만들어서 스레드로 동작.
    save_data_thread.start()
    gps=ServerSocket(IP, 20)
    main()

