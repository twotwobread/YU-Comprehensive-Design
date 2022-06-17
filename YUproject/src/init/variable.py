import PyKakao
import pymysql
import threading

IP="165.229.185.243"
API_KEY = "a00649b953ccf10495e69f5fbae7cd73"
KL = PyKakao.KakaoLocal(API_KEY)
CONN_DB = pymysql.connect(host='127.0.0.1', user='root', password='1234', db='pothole', charset='utf8')
CUR_DB = CONN_DB.cursor()
LOCK = threading.Lock()
