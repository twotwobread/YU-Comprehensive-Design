import socket 
import threading 
from collections import deque
from time import sleep

def init_Server(file):
    """
    파일로 부터 정보를 읽어오는 부분
    초기 세팅 필수
    """
    print("init Server")
    """
    각 역에 어떤 기기가 있는지을 저장하는 dictinary
    """
    group=dict()
    line=list(file.readline().rsplit())
    group[line[0]]=line[1:] #line[0]=역 이름,  line[1:]=해당역에 있는 기기
    while True:
        line=list(file.readline().rsplit())
        if line==[]:
            break
        group[line[0]]=line[1:]
    """
    해당 기기들의 소켓정보를 저장해주는 list
    """
    socket_addr=dict()
    #역별 기기 등록
    for val in group.values():
        for i in val:
            socket_addr[i]=''
    #엘리베이터 관련 소켓 정보 저장공간
    print(group)
    print(socket_addr)
    return group, socket_addr

def save_server(file):
    """
    주기적으로 서버 변동사항을 기록
    각 Station별로 어떤 기기가 있는지 저장
    """
    global group
    print("Saving Start...")
    while True:
        sleep(10) #10초마다 한번씩 서버 변경사항 저장
        file.seek(0,0)
        for key, val in group.items():
            f.write(str(key))
            f.write(' ')
            for i in val:
                f.write(str(i))
                f.write(' ')
            f.write('\n')
        print("Saving Server...")
        



def Send(grp, send_q): 
    """
    사용자의 출발역 기준으로 주변기기들중 큐의 가장 바깥에 있는 기기에 정보를 보내줌
    """
    global group, send_queue, ACK_list, SEAT

    print('Thread Send Start')
    while True: 
        try: 
            flag=0
            
            if len(send_queue)!=0:
                recv = send_queue.popleft() #받아온 Message중 가장 오래된 것 부터 전송
                flag=1 #전송할 Message가 있음을 알려주는 flag
             #새롭게 추가된 클라이언트가 있을 경우 Send 쓰레드를 새롭게 만들기 위해 루프를 빠져나감 
            
            if flag==1: #만약 전송해야하는 Message가 있다면 전송
                if recv[2] in socket_addr:
                    msg=str(recv[0])
                    print("muchin_num = ", recv[2])
                    conn=socket_addr[recv[2]]
                    print(recv)
                    conn.send("SERVER ACK".encode())
                    sleep(1) 
                    if ACK_list[recv[2]]==1: 
                        print("Send : ", msg)
                        conn.send(bytes(msg.encode()))
                        flag=0 #추가적인 전송 방지
                        ACK_list[recv[2]]=0
                    else: #ACK를 못받았을 때
                        print("can not connect robot")
                        send_queue.append(recv)
                else:#처음부터 연결 한번도 한됐을때
                    send_queue.append(recv)
            
            sleep(1)
        except ConnectionResetError:
            print("send except")
            break
        except TimeoutError:
            print("send except2222")
            continue
        except ValueError:
            print("VVVVVVVVVVVVVVVV1")
            continue


def Recv(conn, cnt, send_queue):
    global count, group, move_state, SEAT, ACK_list #인원수와 그룹 구성원의 정보
    print('Thread Recv' + str(cnt) + ' Start')
    while True:
        try:
            data = conn.recv(1024).decode()
            if data=='':
                continue
            print("Received : ", data)
            data, option=data.split() #받아온 데이터와 option으로 분리
            print("data, option = ",data,option)

            cs_lock.acquire()
            if option=='app': #어플레케이션으로 부터 온 정보
                start, end = data.split('/')
                if len(group[start])!=0:
                    machin_num=group[start].pop()
                    move_state[end].append(muchin_num) #기기 이동중
                    send_queue.append(["SEAT app", conn, "SEAT"])
                    send_queue.append([data+" app", conn, str(machin_num)]) #각각의 클라이언트의 메시지, 소켓정보, 보내야하는 기기의 번호를 큐에 담아줌  
                else:
                    #주변에 할당 가능한 기기가 없음
                    print("주변에 기기가 없습니다.")
                    send_queue.append(["False", conn, conn])
          
                raise(ConnectionResetError)
            
            elif option=='init': #클라이언트로 온 정보 머신넘버 등록과정
                socket_addr[data]=conn
                ACK_list[data]=0
                print("socket_addr = ", socket_addr)
                print("group = ", group)
            elif option=='subway': #젯슨->라즈베리파이->서버 넘어온 정보 
                #data/machin_number jetson                                      s                                                                                        
                machin_num,jetson_data =data.split('/')
                if jetson_data=='BSUB':
                    if len(SEAT)!=0: #좌석 예약 부분, 만약 여러 좌석 선택해야하면 pop해서 붙히면됨.
                        send_queue.append(["GO/"+str(SEAT[0])+" server", conn, str(machin_num)])
                    else:
                        send_queue.append(["GO/FAIL server", conn, str(machin_num)])
                    sleep(120)
                    send_queue.append(["OUT/ASUB server", conn, str(machin_num)])


                elif jetson_data=='Goal_set':
                    for key in move_state:
                        if machin_num in move_state[key]:
                            group[key].append(str(machin_num))
                            move_state[key].remove(str(machin_num))
            elif option=='ELV':
                send_queue.append(["PUSH ELV", conn, data])
            elif option=='seat': #좌석 조회
                SEAT=data
            elif option=='ACK':
                ACK_list[data]=1
            cs_lock.release() 
            sleep(0.01)

        except ConnectionResetError as e: #
            #접속이 종료된 경우 구성원의 정보를 변경해줌
            print('Thread Recv' + str(cnt) + ' Close')
            cs_lock.release() 
            cs_lock.acquire()
            #socket_addr[str(cnt+1)]=''
            count-=1 #구성원의 수를 1 감소
            cs_lock.release()
            break
        except ConnectionAbortedError:
            break
        except TimeoutError:
            continue
        except ValueError:
            continue


        

if __name__ == '__main__': 
    ACK_list = dict();
    SEAT=0
    send_queue = deque()
    HOST = '1.1.1.1' #Server ipAddr
    PORT = 8080 #포트포워딩한 포트
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP Socket 
    server_sock.bind((HOST, PORT)) # 소켓에 수신받을 IP주소와 PORT를 설정 
    server_sock.listen(100) # 소켓 연결, 접속 가능한 수 10
    count = 0
    f=open('C:/why_ws/control_server+client/Station.txt', 'r+', encoding='UTF8')
    group, socket_addr=init_Server(f) # 서버 정보 초기화 부분
    move_state={'영남대':[], '임당':[]}
    Save=threading.Thread(target=save_server, args=(f,)).start() #서버를 10분마다 save 해주는 부분
    cs_lock=threading.Lock()
    cs_queue=threading.Lock()
    while True: 
        conn, addr = server_sock.accept() # 해당 소켓을 열고 대기 
        print('Connected ' + str(addr))
        if count==0: #초기상태
            start_rx=threading.Thread(target=Recv, args=(conn, count, send_queue)).start()
            start_tx=threading.Thread(target=Send, args=(group, send_queue)).start()
        elif count>=1: #추가적인 클라이언트 연결
            """
            클라이언트 구성원 정보가 변경됨을 알려줌
            이를 통해 현재 동작중인 tx스레드를 종료하고
            새로 그룹 구성원의 정보를 갱신 한 후 새로운 스레드를 실행함
            """
            start_rx=threading.Thread(target=Recv, args=(conn, count, send_queue)).start()
        count = count + 1 #구성원 수 추가
        sleep(0.5)
