import smbus #import SMBus module of I2C 
from time import sleep, time, localtime #import 
import math
import RPi.GPIO as GPIO
import pigpio
from threading import Thread
#MPU6050 Registers and their Address 
PWR_MGMT_1 = 0x6B 
SMPLRT_DIV = 0x19 
CONFIG = 0x1A 
GYRO_CONFIG = 0x1B 
INT_ENABLE = 0x38 
ACCEL_XOUT_H = 0x3B 
ACCEL_YOUT_H = 0x3D 
ACCEL_ZOUT_H = 0x3F 
GYRO_XOUT_H = 0x43 
GYRO_YOUT_H = 0x45 
GYRO_ZOUT_H = 0x47
FS_SEL=131
SAVE=[]
last_servo_x=0
last_servo_y=0

def MPU_Init(): 
    # write to sample rate register 
    bus.write_byte_data(Device_Address, SMPLRT_DIV, 7) # Write to power management register 
    bus.write_byte_data(Device_Address, PWR_MGMT_1, 1) #Write to Configuration register 
    bus.write_byte_data(Device_Address, CONFIG, 0) #Write to Gyro configuration register 
    bus.write_byte_data(Device_Address, GYRO_CONFIG, 24) #Write to interrupt enable register 
    bus.write_byte_data(Device_Address, INT_ENABLE, 1)

def read_raw_data(addr):
    #Accelero and Gyro value are 16-bit
    high = bus.read_byte_data(Device_Address, addr) 
    low = bus.read_byte_data(Device_Address, addr+1)
    #concatenate higher and lower value 
    value = ((high << 8) | low)
    #to get signed value from mpu6050 
    if(value > 32768):
        value = value - 65536 
    return value

def calibrate_sensor():
    x_accel=0
    y_accel=0
    z_accel=0
    x_gyro=0
    y_gyro=0
    z_gyro=0
    base=[]
    #처음값은 버림
    #Read Accelerometer raw value
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_YOUT_H)
    acc_z = read_raw_data(ACCEL_ZOUT_H)
    
    #Read Gyroscope raw value
    gyro_x = read_raw_data(GYRO_XOUT_H)
    gyro_y = read_raw_data(GYRO_YOUT_H)
    gyro_z = read_raw_data(GYRO_ZOUT_H)
    

    for i in range(10):
        #Read Accelerometer raw value
        acc_x = read_raw_data(ACCEL_XOUT_H)
        acc_y = read_raw_data(ACCEL_YOUT_H)
        acc_z = read_raw_data(ACCEL_ZOUT_H)
    
        #Read Gyroscope raw value
        gyro_x = read_raw_data(GYRO_XOUT_H)
        gyro_y = read_raw_data(GYRO_YOUT_H)
        gyro_z = read_raw_data(GYRO_ZOUT_H)
        
        x_accel+=acc_x
        y_accel+=acc_y
        z_accel+=acc_z
        x_gyro+=gyro_x
        y_gyro+=gyro_y
        z_gyro+=gyro_z
        sleep(0.1)
    
    base.append(x_accel/50)
    base.append(y_accel/50)
    base.append(z_accel/50)
    base.append(x_gyro/50)
    base.append(y_gyro/50)
    base.append(z_gyro/50)

    return base

def save_last(now_time, x, y, z, x_g, y_g, z_g):
    global SAVE
    SAVE=[now_time, x, y, z, x_g, y_g, z_g]

def cal_angle(base):
    global SAVE, last_servo_x, last_servo_y, x_ang, y_ang
    RAD_to_DEG=180/3.141592
    #Read Accelerometer raw value
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_YOUT_H)
    acc_z = read_raw_data(ACCEL_ZOUT_H)
    
    #Read Gyroscope raw value
    gyro_x = read_raw_data(GYRO_XOUT_H)
    gyro_y = read_raw_data(GYRO_YOUT_H)
    gyro_z = read_raw_data(GYRO_ZOUT_H)
    now_time=time()
    gyro_x=(acc_x-base[0])/131
    gyro_y=(acc_y-base[1])/131
    gyro_z=(acc_z-base[2])/131

    accel_angle_y=math.atan(-1*acc_x/math.sqrt(math.pow(acc_y, 2)+math.pow(acc_z,2)))*RAD_to_DEG
    accel_angle_x=math.atan(acc_y/math.sqrt(math.pow(acc_x,2)+math.pow(acc_z,2)))*RAD_to_DEG
    accel_angle_z=0

    dt=(now_time-SAVE[0])/1000
    gyro_angle_x=gyro_x*dt+SAVE[1]
    gyro_angle_y=gyro_y*dt+SAVE[2]
    gyro_angle_z=gyro_z*dt+SAVE[3]
 
    u_gyro_angle_x=gyro_x*dt+SAVE[4]
    u_gyro_angle_y=gyro_y*dt+SAVE[5]
    u_gyro_angle_z=gyro_z*dt+SAVE[6]

    alpha=0.98
    #alpha=0
    angle_x=alpha*gyro_angle_x+(1-alpha)*accel_angle_x
    angle_y=alpha*gyro_angle_y+(1-alpha)*accel_angle_y
    angle_z=gyro_angle_z
    save_last(now_time, angle_x, angle_y, angle_z, u_gyro_angle_x, u_gyro_angle_y, u_gyro_angle_z)
    print("x= {}, y= {}".format(angle_x+2.6, angle_y-2)) # for test
    #print("x= {}, y={}".format(angle_x+3.1, angle_y+4)) # for test
    #print("gyro_x = {}, gyro_y = {}, gyro_z= {}".format(acc_angle_x, a_angle_y, u_gyro_angle_z))
    #if math.trunc(angle_x+2.6)!=last_servo_x:
        #x_ang=angle_x+2.6
        #print("x_ang = ", x_ang)
    x_ang=((100/9)*(int(angle_x+2.6)))+1500
        #last_servo_x=math.trunc(angle_x+2.6)


    #if math.trunc(angle_y-1.3)!=last_servo_y:
     #   last_servo_y=math.trunc(angle_y-1.3)
        #print("y_ang = ", y_ang)
    y_ang=((100/9)*(int(angle_y-2)))+1500
        #y_ang=angle_y-2


def control_servo_x(pin):
    global x_ang, flag
    while True:
        #print("x_ang = ", x_ang)
        if flag==-1:
            break
       # angle=((100/9)*x_ang)+1500
        #print("angle = ", ang)
        pi.set_servo_pulsewidth(pin, x_ang)
        sleep(0.01)

def control_servo_y(pin):
    global y_ang, flag
    while True:
        if flag==-1:
            break
        #angle=((100/9)*y_ang)+1500
        #print("angle = ", ang)
        pi.set_servo_pulsewidth(pin, y_ang)
        sleep(0.01)


bus=smbus.SMBus(1)
Device_Address=0x68
MPU_Init()
pi=pigpio.pi()
base=calibrate_sensor()
x_ang, y_ang = 0, 0
x_pin, y_pin = 17,27 #BCM
flag=0
SAVE=[time(), 0, 0 ,0 ,0 ,0 ,0]
print("change_servo angle 0 0")
pi.set_servo_pulsewidth(x_pin, 1500)
pi.set_servo_pulsewidth(y_pin, 1500)

x_thread = Thread(target = control_servo_x, args = (x_pin,)).start()
y_thread = Thread(target = control_servo_y, args = (y_pin,)).start()
while True:
    try:
        cal_angle(base)
        sleep(0.01)
    except KeyboardInterrupt:
        flag=-1
        break
