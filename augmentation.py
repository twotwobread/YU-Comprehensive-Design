import random
import numpy as np
import os
import cv2
import glob
from PIL import Image
import PIL.ImageOps    

#다음 변수를 수정하여 새로 만들 이미지 갯수를 정합니다.
num_augmented_images = 2

file_path = 'C:/why_ws/yoloV5/'
name = 'test.jpg'

file_names = os.listdir(file_path)
total_origin_image_num = len(file_names)
augment_cnt = 1

for i in range(1, num_augmented_images):
    #change_picture_index = random.randrange(1, total_origin_image_num-1)
    #file_name = file_names[change_picture_index]
    
    #origin_image_path = 'custom_data\Wonbin_faces\\' + file_name
    #print(origin_image_path)
    image = Image.open(file_path + name)
    random_augment = random.randrange(1,4)
    for j in range(3):
        if(j == 0):
            #이미지 좌우 반전
            inverted_image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            inverted_image.save(file_path + 'inverted_' + str(augment_cnt) + name)
        elif(j == 1):
            #이미지 기울이기
            rotated_image = image.rotate(random.randrange(-20, 20))
            rotated_image.save(file_path + 'rotated_' + str(augment_cnt) + name)
            
        elif(j == 2):
            #노이즈 추가하기
            #img = cv2.imread(origin_image_path)
            img = cv2.imread(file_path + name)
            row,col,ch= img.shape
            mean = 0
            var = 0.1
            sigma = var**0.5
            gauss = np.random.normal(mean,sigma,(row,col,ch))
            gauss = gauss.reshape(row,col,ch)
            noisy_array = img + gauss
            noisy_image = Image.fromarray(np.uint8(noisy_array)).convert('RGB')
            noisy_image.save(file_path + 'noiseAdded_' + str(augment_cnt) + name)
        
        augment_cnt += 1
