from init.variable import *
from web import app
from init.server import ServerSocket
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

result = KL.geo_coord2address(128.75456, 35.83135)
print(result)
if result['meta']['total_count']!=0:
    address=result['documents'][0]['address']['address_name']
    print("database start")
    #sql = "INSERT INTO img_path ( img_path, latitude, longitude, addr , priority) VALUES (%s, %s, %s, %s, %s);"
    #val = (img_path, latitude, longitude, address,0)
    #variableCUR_DB.execute(sql, val)
    #variable.CONN_DB.commit()
else: # can't point in map
    print("잘못된 위도 경도 입니다 !!")

