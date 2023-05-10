# import modules

from threading import Thread
import configparser
import os
import glob
import shutil
import traceback
import time
from datetime import datetime
import tkinter as tk
import cv2
import numpy as np
import imutils
from imutils import paths
from PIL import Image, ImageTk

from lib.camera import SoftwareTriggerBalser
from lib.amore import compare_similarity

class MainFrame(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

        # full screen mode f11
        self.master.attributes('-fullscreen', True)
        self.master.bind("<F11>", lambda event: self.master.attributes('-fullscreen', not self.master.attributes('-fullscreen')))
        self.master.bind("<Escape>", lambda event: self.master.attributes('-fullscreen', False))
        self.master.title("SINPLAT AI VISION PROGRAM")

        # setting config
        # model_config = configparser.ConfigParser()
        # model_config.read('lib/config/cam1_odc_config.INI', encoding='utf-8')

        # self.model_path = str(model_config['NONE']['model_path'])
        # self.label_path = str(model_config['NONE']['label_path'])

        # variables
        self.cam1_img = None
        self.cam_output = None

        self.capture_mode = False
        self.output_save_mode = False

        self.start_mode = False
        self.result_mode = False
        self.reset_mode = False

        self.is_ok = False
        self.inspection_mode = False
        self.cam1_label_list = []
        self.ProcessCheck = False
        # self.InsArea = [900,0,750,300]  #아모레퍼시픽 분홍색 용기(상단부)
        self.InsArea = [900,1770,750,250]  #아모레퍼시픽 분홍색 용기(하단부)
        # self.InsArea = [800, 800, 800, 800]  #디폴트
        self.Exchange = True
        self.realtime_view_mode = False
        self.TargetImageName = "standard.jpg"
        self.min_confidence = 98.5
        # self.total_ins_result = True

        # self.model_name = '0_DEFAULT'
        self.selected_model = 0
        self.total_cnt = self.ok1_cnt = self.ng1_cnt = 0

        #inspection Limit Time
        self.inspection_time = time.time()
        self.inspection_timelimit = 10

        # img sources
        self.bg_img = ImageTk.PhotoImage(file = 'imgs/bg.png')
        self.ok_img = ImageTk.PhotoImage(file = 'imgs/ok.png')
        self.ng_img = ImageTk.PhotoImage(file = 'imgs/ng.png')
        self.start_btn = ImageTk.PhotoImage(file='imgs/start.png')
        self.result_btn = ImageTk.PhotoImage(file='imgs/result.png')
        self.reset_btn = ImageTk.PhotoImage(file='imgs/reset.png')
        self.on_img = ImageTk.PhotoImage(file='imgs/on.png')

        self.create_widgets()

    def create_widgets(self):
        self.grid(row = 0, column = 0)
        self.main_canvas = tk.Canvas(self, width = 1920, height = 1080)

        self.background_image = self.main_canvas.create_image(0, 0, image = self.bg_img, anchor = 'nw')

        self.cam_image = self.main_canvas.create_image(265, 165, image = '', anchor = 'nw', state = 'normal') 
        self.backup_image = self.main_canvas.create_image(265, 165, image = '', anchor = 'nw', state = 'normal')

        self.start_btn_image = self.main_canvas.create_image(1509, 248, image = self.start_btn, anchor = 'center', state = 'hidden')
        self.result_btn_image = self.main_canvas.create_image(1639, 248, image=self.result_btn, anchor='center', state = 'hidden')
        self.reset_btn_image = self.main_canvas.create_image(1769, 248, image=self.reset_btn, anchor='center', state = 'hidden')

        self.capture_on_btn_image = self.main_canvas.create_image(1517, 467, image=self.on_img, anchor='center', state = 'hidden')
        self.save_on_btn_image = self.main_canvas.create_image(1772, 467, image=self.on_img, anchor='center', state = 'hidden')

        self.ok_canvas_image = self.main_canvas.create_image(1517, 915, image = self.ok_img, anchor = 'center', state = 'hidden')
        self.ng_canvas_image = self.main_canvas.create_image(1779, 915, image = self.ng_img, anchor = 'center', state = 'hidden')

        self.total1_canvas_cnt = self.main_canvas.create_text(1490, 675, text=self.total_cnt, font=(None, 20, 'bold'), fill='white', anchor='center')
        self.ok1_canvas_cnt = self.main_canvas.create_text(1640, 675, text=self.ok1_cnt, font=(None, 20, 'bold'), fill='white', anchor='center')
        self.ng1_canvas_cnt = self.main_canvas.create_text(1790, 675, text=self.ng1_cnt, font=(None, 20, 'bold'), fill='white', anchor='center')

        self.X_index_entry = tk.Entry (self, font=("gothic", 18, 'bold'), width=12, justify='center')
        self.X_index_showEntry = self.main_canvas.create_window(850, 49, anchor='center', window=self.X_index_entry)
        self.X_index_entry.insert(0, str(self.InsArea[0]))
        self.X_index_entry.bind("<KeyRelease>", self.SettingIndex_Bind)

        self.Y_index_entry = tk.Entry (self, font=("gothic", 18, 'bold'), width=12, justify='center')
        self.Y_index_showEntry = self.main_canvas.create_window(1041, 49, anchor='center', window=self.Y_index_entry)
        self.Y_index_entry.insert(0, str(self.InsArea[1]))
        self.Y_index_entry.bind("<KeyRelease>", self.SettingIndex_Bind)

        self.W_index_entry = tk.Entry (self, font=("gothic", 18, 'bold'), width=12, justify='center')
        self.W_index_showEntry = self.main_canvas.create_window(1239, 49, anchor='center', window=self.W_index_entry)
        self.W_index_entry.insert(0, str(self.InsArea[2]))
        self.W_index_entry.bind("<KeyRelease>", self.SettingIndex_Bind)

        self.H_index_entry = tk.Entry (self, font=("gothic", 18, 'bold'), width=12, justify='center')
        self.H_index_showEntry = self.main_canvas.create_window(1434, 49, anchor='center', window=self.H_index_entry)
        self.H_index_entry.insert(0, str(self.InsArea[3]))
        self.H_index_entry.bind("<KeyRelease>", self.SettingIndex_Bind)

        # self.model_name_txt = self.main_canvas.create_text(1420, 35, text=self.model_name, font=(None, 18, 'bold'), fill='white', anchor='nw')

        self.main_canvas.bind('<Button-1>', self.main_btn)
        self.main_canvas.pack()

    def SettingIndex_Bind(self, event):
        self.X_index = self.X_index_entry.get()
        self.Y_index = self.Y_index_entry.get()
        self.W_index = self.W_index_entry.get()
        self.H_index = self.H_index_entry.get()

        if self.X_index == '':
            self.X_index = 0
            self.X_index_entry.insert(0, '0')
        if self.Y_index == '':
            self.Y_index = 0
            self.Y_index_entry.insert(0, '0')
        if self.W_index == '':
            self.W_index = 0
            self.W_index_entry.insert(0, '0')
        if self.H_index == '':
            self.H_index = 0
            self.H_index_entry.insert(0, '0')

        try:
            self.X_index = int(self.X_index)
        except:
            self.X_index = 0
            self.X_index_entry.delete(0, 'end')
            self.X_index_entry.insert(0, "0")
        try:
            self.Y_index = int(self.Y_index)
        except:
            self.Y_index = 0
            self.Y_index_entry.delete(0, 'end')
            self.Y_index_entry.insert(0, "0")
        try:
            self.W_index = int(self.W_index)
        except:
            self.W_index = 0
            self.W_index_entry.delete(0, 'end')
            self.W_index_entry.insert(0, "0")
        try:
            self.H_index = int(self.H_index)
        except:
            self.H_index = 0
            self.H_index_entry.delete(0, 'end')
            self.H_index_entry.insert(0, "0")

        self.InsArea = [self.X_index, self.Y_index, self.W_index, self.H_index]
        print(f'Setup Index - {self.InsArea}')
        self.Exchange = True

    def btn_off(self):
        self.main_canvas.itemconfig(self.reset_btn_image, state = 'hidden')

    def main_btn(self, event):
        self.x = event.x
        self.y = event.y
        print('main_canvas:', self.x, self.y)

        #sinplat btn
        # if 1650 < self.x < 1650+170 and 25 < self.y < 25+45:
        #     self.selected_model += 1

        #     if self.selected_model == 1:
        #         self.model_name = '1_IOPE'
        #         self.main_canvas.itemconfig(self.model_name_txt, text = self.model_name)
        #         print('model 1 selected')
        #     if self.selected_model == 2:
        #         self.model_name = '2_SULHWA'
        #         self.main_canvas.itemconfig(self.model_name_txt, text = self.model_name)
        #         print('model 2 selected')
        #     if self.selected_model == 3:
        #         self.model_name = '3_HANYUL'
        #         self.main_canvas.itemconfig(self.model_name_txt, text = self.model_name)
        #         print('model 3 selected')
        #     if self.selected_model > 3:
        #         self.selected_model = 0
        #         self.model_name = '0_DEFAULT'
        #         self.main_canvas.itemconfig(self.model_name_txt, text = self.model_name)
        #         print('model 4 selected')

        #start btn
        if 1480 < self.x < 1480+55 and 225 < self.y < 225+55:
            self.start_mode = not self.start_mode #True, False
            self.cam1_label_list = []
            # self.total_ins_result = True

            if self.start_mode:
                self.inspection_time = time.time()
                self.result_mode = False
                self.reset_mode = False
                #inspection start
                self.cam1_label_list = []
                self.cam_output = None
                                
                self.inspection_mode = True 
                self.is_ok = False

                self.main_canvas.itemconfig(self.ok_canvas_image, state = 'hidden')
                self.main_canvas.itemconfig(self.ng_canvas_image, state = 'hidden')

                self.main_canvas.itemconfig(self.start_btn_image, state = 'normal')			
                self.main_canvas.itemconfig(self.result_btn_image, state = 'hidden')
                self.main_canvas.itemconfig(self.reset_btn_image, state = 'hidden')

        #result btn
        if 1615 < self.x < 1615+55 and 225 < self.y < 225+55:
            self.result_mode = not self.result_mode

            if self.result_mode:
                self.start_mode = False
                self.reset_mode = False

                self.main_canvas.itemconfig(self.start_btn_image, state = 'hidden')			
                self.main_canvas.itemconfig(self.result_btn_image, state = 'normal')
                self.main_canvas.itemconfig(self.reset_btn_image, state = 'hidden')

                # update count for cam1
                
                if 'OK' in self.cam1_label_list: # OK
                    self.ok1_cnt = self.ok1_cnt +1
                    self.main_canvas.itemconfig(self.ok_canvas_image, state = 'normal')	
                    self.main_canvas.itemconfig(self.ng_canvas_image, state = 'hidden')
                    self.main_canvas.itemconfig(self.ok1_canvas_cnt, text = self.ok1_cnt)
                else: # NG
                    self.ng1_cnt = self.ng1_cnt +1
                    self.main_canvas.itemconfig(self.ng_canvas_image, state = 'normal')
                    self.main_canvas.itemconfig(self.ok_canvas_image, state = 'hidden')
                    self.main_canvas.itemconfig(self.ng1_canvas_cnt, text = self.ng1_cnt)    

                self.total_cnt = self.total_cnt +1
                self.main_canvas.itemconfig(self.total1_canvas_cnt, text = self.total_cnt)

                self.inspection_mode = False
                self.cam1_label_list = []
                # self.cam_output = None
                # CTH.iep.Qimage.queue.clear()

        #reset btn
        if 1745 < self.x < 1745+55 and 225 < self.y < 225+55:
            self.reset_mode = not self.reset_mode

            self.main_canvas.itemconfig(self.reset_btn_image, state = 'normal')
            root.after(200, self.btn_off)			

            if self.reset_mode:
                self.ProcessCheck = False
                self.start_mode = False
                self.result_mode = False

                self.inspection_mode = False
                self.cam1_label_list = []
                self.cam_output = None
                CTH.iep.Qimage.queue.clear()
    
                self.main_canvas.itemconfig(self.ok_canvas_image, state = 'hidden')
                self.main_canvas.itemconfig(self.ng_canvas_image, state = 'hidden')

                self.main_canvas.itemconfig(self.start_btn_image, state = 'hidden')			
                self.main_canvas.itemconfig(self.result_btn_image, state = 'hidden')

        # capture mode
        if 1440 < self.x < 1440+155 and 440 < self.y < 440+55: 
            self.capture_mode = not self.capture_mode #True, False
            state = 'hidden' if not self.capture_mode else 'normal'
            self.main_canvas.itemconfig(self.capture_on_btn_image, state = state)
            print('[INFO] capture_mode: ', self.capture_mode)
            self.Exchange = True

        # output save mode
        if 1690 < self.x < 1690+155 and 440 < self.y < 440+55: 
            self.output_save_mode = not self.output_save_mode #True, False
            state = 'hidden' if not self.output_save_mode else 'normal'
            self.main_canvas.itemconfig(self.save_on_btn_image, state = state)
            print('[INFO] output_save_mode: ', self.output_save_mode)

        # realtime view mode
        if 1591 < self.x < 1873 and 27 < self.y < 75:
            self.realtime_view_mode = not self.realtime_view_mode
            print('[INFO] realtime_view_mode: ', self.realtime_view_mode)
            
    def convert_img(self, img):
        img = cv2.resize(img, (958, 840), cv2.INTER_NEAREST)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(image = img)
        return img

    def img_to_contrast(self, img): 
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB) 
        l, a, b = cv2.split(lab) 
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(2, 2)) 
        cl = clahe.apply(l) 
        limg = cv2.merge((cl, a, b)) 
        final_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR) 
        return final_img

    def save_ins_capture(self, img, save_path, save_num=500):
        img_name=''.join([str("%.8f"%time.time()).replace('.', '_'), '.jpg'])
        os.makedirs(save_path, exist_ok=True)
        cv2.imwrite(os.path.join(save_path, img_name), img)
        self.rm_ins_capture(path=save_path, num=save_num)
        return

    def rm_ins_capture(self, is_folder=False, path=None, num=500):
        flist = sorted(glob.glob(f'{path}/*'), key=os.path.getctime, reverse=True)
        # print('\n\n\nnow file count ', path, len(flist))

        if len(flist) > num:
            for n in range(num, len(flist)):
                if is_folder:
                    shutil.rmtree(flist[n], ignore_errors= True)
                    # print(f'Removed old folders: {flist[n]}')
                else:
                    os.remove(flist[n])
                    # print(f'Removed old files: {flist[n]}')

    def myloop(self):
        # show cam1 image   
        while 1:
            try:
                time.sleep(0.01)
                # print('1.' , threading.active_count())
                # print('2.' , CTH.iep.Qimage.qsize())			
                
                # clearing queue
                if CTH.iep.Qimage.qsize() > 1:
                    CTH.iep.Qimage.queue.clear()

                if not CTH.iep.Qimage.empty():
                    self.cam1_img = CTH.iep.Qimage.get()

                    if self.capture_mode:
                        save_path=f'database/cam1_capture'
                        # self.save_ins_capture(self, self.cam1_img, save_path)
                        # Thread(target=self.save_ins_capture, args=[self.cam1_img.copy(), save_path],daemon=True).start()
                        self.save_ins_capture(self.cam1_img[self.InsArea[1]:self.InsArea[1]+self.InsArea[3], self.InsArea[0]:self.InsArea[0]+self.InsArea[2]].copy(), save_path) 
                        cv2.imwrite('standard.jpg', self.cam1_img[self.InsArea[1]:self.InsArea[1]+self.InsArea[3], self.InsArea[0]:self.InsArea[0]+self.InsArea[2]].copy())


                    if (self.inspection_mode and self.is_ok==False) or self.realtime_view_mode:
                        self.ProcessCheck = True
                        startTime = time.time()

                        result = 'NG'
                        self.cam1_label_list.append(result)
                        # cv2.imwrite('tmp/ins_img.jpg', self.cam1_img)
                        # print(f"imwrite Time: {time.time()-startTime:.3f} sec")
                        # input_img = cv2.imread('tmp/ins_img.jpg')
                        # print(f"imread1 Time: {time.time()-startTime:.3f} sec")
                        # target_img = cv2.imread('standard.jpg')
                        # print(f"imread2 Time: {time.time()-startTime:.3f} sec")
                        similarity, ins_area = amore.measure_similarity(self.cam1_img.copy(), self.InsArea.copy(), self.Exchange)
                        # print(f"Inspection Process Time: {time.time()-startTime:.3f} sec")
                        self.Exchange = False
                        cv2.rectangle(self.cam1_img, (ins_area[0], ins_area[1]), (ins_area[0]+ins_area[2], ins_area[1]+ins_area[3]), (255,255,255), 15)
                        text = f'[RESULT] {similarity[0][0]*100:.5f}%'
                        print(text, self.is_ok)

                        if similarity[0][0]*100 > self.min_confidence:
                            result = 'OK'
                            self.cam1_label_list.append(result)
                        
                            cv2.rectangle(self.cam1_img, (0, 0), (self.cam1_img.shape[1], self.cam1_img.shape[0]), (0,255,0), 15)
                            cv2.putText(self.cam1_img, text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 8)

                            self.cam_output = self.cam1_img.copy()
                            self.is_ok = True
                        
                        else:
                            cv2.rectangle(self.cam1_img, (0, 0), (self.cam1_img.shape[1], self.cam1_img.shape[0]), (0,0,255), 15)
                            cv2.putText(self.cam1_img, text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 8)

                            self.cam_output = self.cam1_img.copy()
                        # print(f"Rectengle Time: {time.time()-startTime:.3f} sec")

                        if self.output_save_mode:
                            save_path=f'database/cam1_result'
                            self.save_ins_capture(self.cam_output.copy(), save_path) 
                        
                        print(f"Inspection Time: {time.time()-startTime:.3f} sec")
                        if ((time.time()-self.inspection_time > self.inspection_timelimit) or 'OK' in self.cam1_label_list) and not self.realtime_view_mode:
                            self.result_mode = False
                            self.start_mode = False
                            self.reset_mode = False

                            self.main_canvas.itemconfig(self.start_btn_image, state = 'hidden')			
                            self.main_canvas.itemconfig(self.result_btn_image, state = 'normal')
                            self.main_canvas.itemconfig(self.reset_btn_image, state = 'hidden')

                            if 'OK' in self.cam1_label_list: # OK
                                self.ok1_cnt = self.ok1_cnt +1
                                self.main_canvas.itemconfig(self.ok_canvas_image, state = 'normal')	
                                self.main_canvas.itemconfig(self.ng_canvas_image, state = 'hidden')
                                self.main_canvas.itemconfig(self.ok1_canvas_cnt, text = self.ok1_cnt)
                            else: # NG
                                self.ng1_cnt = self.ng1_cnt +1
                                self.main_canvas.itemconfig(self.ng_canvas_image, state = 'normal')
                                self.main_canvas.itemconfig(self.ok_canvas_image, state = 'hidden')
                                self.main_canvas.itemconfig(self.ng1_canvas_cnt, text = self.ng1_cnt)    

                            self.total_cnt = self.total_cnt +1
                            self.main_canvas.itemconfig(self.total1_canvas_cnt, text = self.total_cnt)

                            self.inspection_mode = False
                            self.cam1_label_list = []
                            print(f"Inspection Result OK Check Complete")
                            # print(f"Result Process Time: {time.time()-startTime:.3f} sec")
                        
                    else:
                        cv2.rectangle(self.cam1_img, (self.InsArea[0], self.InsArea[1]), (self.InsArea[0]+self.InsArea[2], self.InsArea[1]+self.InsArea[3]), (255,255,255), 15)
                        CTH.iep.Qimage.queue.clear()

                    # tk 용 이미지로 변환
                    if self.cam_output is not None:
                        self.result_img = self.convert_img(self.cam_output)
                    else:
                        self.result_img = self.convert_img(self.cam1_img)

                    if self.ProcessCheck == True:
                        # tk 내 이미지 띄우기
                        self.main_canvas.itemconfig(self.cam_image, image = self.result_img)
                        self.result_img_bu = self.result_img
                        self.main_canvas.itemconfig(self.backup_image, image = self.result_img_bu)                    
                    else:
                        # tk 내 이미지 띄우기
                        self.main_canvas.itemconfig(self.cam_image, image = self.result_img)
                        self.result_img_bu = self.result_img
                        self.main_canvas.itemconfig(self.backup_image, image = self.result_img_bu)                    

                    # self.cam1_img = CTH.iep.Qimage.get()
            except:
                print(traceback.format_exc())

# inspection thread
CTH = SoftwareTriggerBalser('cam1', 'lib/config/basic_cam_config.INI', 'log')
Thread(target=CTH.stream_mode, daemon=True).start()

amore = compare_similarity('lib/config/cam1_amore_config.INI')

root = tk.Tk()
main_frame = MainFrame(master=root)
Thread(target=main_frame.myloop, daemon=True).start()

root.update()
root.mainloop()