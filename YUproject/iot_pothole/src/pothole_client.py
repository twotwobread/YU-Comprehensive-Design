'''
#
# filename : pothole_client.py
# server의 web server 동작을 실험하기 위함.
# author : 이수영 ( 2021.12.27 )
# - version 1.0 (2021.12.27), 
#  
'''
import socket
import threading

class clientSocket:
    def __init__(self, ip, port):
        self.TCP_IP = ip
        self.TCP_PORT = port
        self.socketConnect()
        self.sendThread = threading.Thread(target=self.sendImg)
    def socketConnect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.TCP_IP, self.TCP_PORT))
        print("Client is connected now ( Server IP : " + self.TCP_IP + ', Server PORT: ' + str(self.TCP_PORT)+' )')
    def sendImg(self):
        while(True):
            pass
def main():

    pass

if __name__ == "__main__":
    gps=clientSocket("165.229.185.201", 20)
    main()
