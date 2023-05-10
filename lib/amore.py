import os
import cv2
import imutils
import numpy as np
from keras.applications.vgg16 import VGG16, preprocess_input
from keras.preprocessing import image as kimage
from skimage import io
from sklearn.metrics.pairwise import cosine_similarity
from imutils.paths import list_images
import configparser
import time

class compare_similarity():
    def __init__(self, config_path=None):
        # load VGG model
        self.vgg_model = VGG16(weights='imagenet', include_top=False, pooling='avg')   
        self.features1 = None
        self.features2 = None     

        # set setval config
        self.setvalue_path = config_path

        # self.compare_img_dir = '01_test_image/06_long_color_glass_1ok' 
        # 아이오페
        # self.ins_area = [1150, 320, 300, 150] # x, y, w, h 
        # 한율
        # ins_area = [1170, 660, 250, 130] # x, y, w, h 
        # 설화수
        # self.ins_area = [1150, 590, 180, 380] # x, y, w, h 
        # self.conf = 98

    def load_image(self,img, target_size=(224, 224)):
        # img = io.imread(img_path)
        img = cv2.resize(img, target_size)
        img = kimage.img_to_array(img)
        img = np.expand_dims(img, axis=0)
        img = preprocess_input(img)
        return img

    def extract_features(self,img_path, model):
        img = self.load_image(img_path)
        features = model.predict(img)
        features = features.flatten()
        return features

    def measure_similarity(self, ori_img, ins_area, exchange):
        sessionTime = time.time()
        # setvalue_config = configparser.ConfigParser()
        # setvalue_config.read(self.setvalue_path, encoding='utf-8')        
        # standard_img_path = str(setvalue_config['NONE']['standard_img'])
        # # ins_area = eval(setvalue_config['NONE']['ins_area'])
        # conf = int(setvalue_config['NONE']['conf'])
        # print(f'config load time: {time.time()-sessionTime}')

        img_1 = cv2.imread("standard.jpg")  #master_img[ins_area[1]:ins_area[1]+ins_area[3], ins_area[0]:ins_area[0]+ins_area[2]].copy()#self.ins_image_path(standard_img_path, ins_area)
        img_2 = ori_img[ins_area[1]:ins_area[1]+ins_area[3], ins_area[0]:ins_area[0]+ins_area[2]].copy()#self.ins_image_path(img2_path, ins_area)
        # print(f'ins_image_path time: {time.time()-sessionTime}')

        if self.features1 is None or exchange == True:
            self.features1 = self.extract_features(img_1, self.vgg_model)
            print(f'extract_features1 time: {time.time()-sessionTime}')            
        else:
            pass
        # self.features1 = self.extract_features(img_path1, self.vgg_model)
        self.features2 = self.extract_features(img_2, self.vgg_model)
        # print(f'extract_features2 time: {time.time()-sessionTime}')
        similarity = cosine_similarity([self.features1], [self.features2])
        # print(f'cosine_similarity time: {time.time()-sessionTime}')
        return similarity, ins_area

    def ins_image_path(self, img_path, ins_area):
        os.makedirs('tmp', exist_ok=True)
        filename = img_path.split(os.sep)[-1]
        image = cv2.imread(img_path)
        ins_img = image.copy()[ins_area[1]:ins_area[1]+ins_area[3], ins_area[0]:ins_area[0]+ins_area[2]]
        ins_img = cv2.imwrite(f'tmp/crop_{filename}', ins_img)
        return_path = f'tmp/crop_{filename}'
        # print()
        # print(return_path)
        return return_path

#########################################################################################

if __name__ == '__main__':
    
    # hyper-parameters
    amore = compare_similarity('config/cam1_amore_config.INI')
    compare_img_dir = 'gamedata' 
   
    for num, image_path in enumerate(sorted(list(list_images(compare_img_dir)))):
        filename = image_path.split(os.sep)[-1]
        image = cv2.imread(image_path)
        # Calculate the similarity
        similarity, ins_area, conf = amore.measure_similarity(f"{compare_img_dir}/{filename}")
        
        text = f'[RESULT] {num+1:03d}. {filename}: {similarity[0][0]*100:.5f}%'
        print(text)

        cv2.putText(image, text, (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 5)
        image = imutils.resize(image, width=1024)
        cv2.imshow("cv_img", image)
        
        if similarity[0][0]*100 > conf:
            key = cv2.waitKey(0)
            os.makedirs('answer', exist_ok=True)
            cv2.imwrite(f'answer/{num:03d}_answer.jpg', image)
        else:
            key = cv2.waitKey(1)
        if key == 'q':
            break