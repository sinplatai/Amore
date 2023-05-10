import time
import os
import cv2
import configparser
import threading
from pypylon import pylon
from threading import Thread
from datetime import datetime
from queue import Queue
import logging
import traceback
from imutils import paths, resize

print('[MODULE] basler module 1.4.5')

class SoftwareTriggerBalser():
	def __init__(self, alias, basic_cam_path, log_path, restart_txt_path = None):
		r'''
		*	alias: (str) Name of this instance
		*	basic cam path: (str) Directory path of basic cam ini file
		*	log path: (str) Directory path of output log text file
				- ex) 'log' \
				- low-level directory is created automatically like 'log/cam1'
		*	restart txt path: (str) Directory path of restart stack txt file
				- If restart stack reaches to user-defined value \
				- Main code reads txt file, and determines what to do.
		'''
		# setting paths and variables
		self.basic_cam_path = basic_cam_path
		self.log_path = os.path.join(log_path, alias)
		if restart_txt_path == None:
			self.restart_txt_path = os.path.join(self.log_path, 'restart.txt')
		else:
			self.restart_txt_path = restart_txt_path 	# if error -> write += 1
		self.name = alias
		
		# setting config parser
		self.config = configparser.ConfigParser()
		self.config.read(self.basic_cam_path, encoding='utf-8')
		self.user_values = self.config['SETTING']
		self.MODE = self.user_values['MODE']

		# setting logger
		self.logger = logging.getLogger()
		self.logger.setLevel(logging.INFO)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		os.makedirs(self.log_path, exist_ok=True)

		nowtime = datetime.now().strftime('%Y_%m_%d')
		file_handler = logging.FileHandler(f'{self.log_path}/log_{nowtime}.log')
		file_handler.setFormatter(formatter)
		self.logger.addHandler(file_handler)

		# cam restart txt - if error occurs write += 1
		self.init_restart_stack()

		# game data setting (camera capture trick)
		self.gamedata = self.config['GAME']['path']
		self.nextdir = os.listdir(self.gamedata)[0]
		self.gamequeue = Queue()
		self.game_grabber = False 	# game mode trigger switch
		self.game_streamer = False

		# connect camera
		self.connect_cam()

		# start capture thread
		Thread(target = self.Capture, daemon=True).start()
		
	def connect_cam(self):
		if self.MODE == 'war':
			while 1:
				try:
					info = pylon.DeviceInfo()
					info.SetSerialNumber(self.user_values['serial'])
					self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice(info))
					self.camera.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(),
												pylon.RegistrationMode_ReplaceAll,
												pylon.Cleanup_Delete)

					self.iep = ImageEventPrinter(self.basic_cam_path)
					self.camera.RegisterImageEventHandler(self.iep, 
													pylon.RegistrationMode_Append, 
													pylon.Cleanup_Delete)
					self.camera.MaxNumBuffer = int(self.user_values['maxNumBuffer'])
					self.camera.Open()
					self.logger.info(f'[INFO] {self.user_values["serial"]} basler device connected')

					# Set user-defined values
					# self.camera.Width.SetValue(int(self.user_values['width']))
					# self.camera.Height.SetValue(int(self.user_values['height']))
					
					# self.camera.CenterX.SetValue(eval(self.user_values['centerX']))
					# self.camera.CenterY.SetValue(eval(self.user_values['centerY']))

					# if not eval(self.user_values['centerX']):
					# 	self.camera.OffsetX.SetValue(int(self.user_values['offsetX']))

					# if not eval(self.user_values['centerY']):
					# 	self.camera.OffsetY.SetValue(int(self.user_values['offsetY']))

					# self.camera.GevSCPSPacketSize.SetValue(int(self.user_values['packetSize']))
					# self.camera.GevSCPD.SetValue(int(self.user_values['interPacketDelay']))
					# self.camera.ExposureTimeRaw.SetValue(int(self.user_values['ExposureTimeRaw']))  # must be multiple of 52

					# self.init_restart_stack()
					break

				except Exception as e:
					time.sleep(1)
					self.camera.Close()
					self.logger.error(f'{traceback.format_exc()}')
					print(f'[ERROR] Can not connect camera {self.user_values["serial"]}. try reconnect...')
					# self.plus_restart_stack()
					
		else: # mode == 'game'
			self.iep = ImageEventPrinter(self.basic_cam_path)

	def stream_mode(self, on=True):
		if self.MODE == 'war':
			self.camera.Close()
			self.connect_cam()

		if on == 'True' or on == True:
			if self.MODE == 'war':
				self.camera.TriggerMode.SetValue('Off')

				if not self.camera.IsGrabbing():
					self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
				print('[CAMERA] Steam war mode started / grab: On')

			else: # game mode
				self.game_streamer = True
				Thread(target = self.game_stream, daemon=True).start()

		else:
			if self.MODE == 'war':
				self.camera.TriggerMode.SetValue('On')
				self.camera.StopGrabbing()
				print('[CAMERA] Steam war mode stopped / grab: Off')
			else:
				self.game_streamer = False
				print('[CAMERA] Steam game mode stopped / grab: Off')

	def game_stream(self):
		self.iterpath = sorted(list(paths.list_images(
			os.path.join(self.gamedata, self.nextdir)
			)))

		while self.game_streamer:
			for path in self.iterpath:
				print(path)
				time.sleep(0.05)
				image = cv2.imread(path)
				image = cv2.resize(
					image,
					(int(self.user_values['width']), int(self.user_values['height']))
				)
				self.iep.Qimage.put(image)

	def trigger_on(self):
		# initialze cam
		self.initialize_cam()

		# add cycle
		self.config.read(self.basic_cam_path, encoding='utf-8')
		with open(self.basic_cam_path, 'w') as f:
			cycle = self.config.get('CAPTURE', 'cycle')
			# when cycle reachs to '99', initialize the value to '00'
			if cycle == '99':
				cycle = '00'

			# make next cycle value (+1)
			self.config['CAPTURE']['cycle'] = str(int(cycle) + 1).zfill(2)
			self.config.write(f)
		
		self.iep.read_config()

		if self.MODE == 'war':
			# loop until getting grab status successfully
			while 1:
				try:
					if self.camera.IsGrabbing():
						break

					self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
					self.init_restart_stack()
					break
				except Exception as e:
					self.logger.error(f'{traceback.format_exc()}')
					self.plus_restart_stack()
					self.connect_cam()
			
			# loop for the user-defined counts
			while self.camera.IsGrabbing() and not self.iep.trigger_end:
				if self.camera.WaitForFrameTriggerReady(300, pylon.TimeoutHandling_ThrowException):
					self.camera.ExecuteSoftwareTrigger()

			# stop grabbing after reaching the maximum trigger counts
			self.camera.StopGrabbing()
		
		else: # if mode is 'game'
			self.game_grabber = True
			if self.gamequeue.empty():
				for pack in os.listdir(self.gamedata):
					self.gamequeue.put(pack)
			self.nextdir = self.gamequeue.get()
			return

	def trigger_off(self):
		if self.MODE == 'war':
			self.camera.StopGrabbing()
		else:
			self.game_grabber = False

	def Capture(self):
		while 1:
			if self.MODE == 'war':
				try:
					while self.camera.IsGrabbing():
						self.camera.RetrieveResult(300, pylon.TimeoutHandling_Return)
						break
				except Exception as e:
					self.logger.error(f'{traceback.format_exc()}')
					print(traceback.format_exc())
					self.plus_restart_stack()

			else: # mode == 'game'
				time.sleep(0.1) # if delete, image won't change...
				self.iterpath = sorted(list(paths.list_images(
						os.path.join(self.gamedata, self.nextdir)
						)))

				stime = time.time()
				while self.game_grabber:

					for idx, path in enumerate(self.iterpath):
						if idx == int(self.user_values['maxTriggerCounts']):
							self.iep.trigger_end = True
							print('game cam elapsed:', time.time() - stime)
							break
						image = cv2.imread(path)
						image = cv2.resize(
							image,
							(int(self.user_values['width']), int(self.user_values['height']))
						)
						self.iep.Qimage.put(image)
						self.game_grabber = False

	def plus_restart_stack(self):
		with open(self.restart_txt_path, 'r') as f:
			restart_stack = f.read()
			self.restart_stack = int(restart_stack)
			self.restart_stack += 1
		with open(self.restart_txt_path, 'w') as f:
			f.write(str(self.restart_stack))

	def init_restart_stack(self):
		with open(self.restart_txt_path, 'w') as f:
			f.write("0")
		self.restart_stack = 0

	def initialize_cam(self):
		# stop grabbing
		if self.MODE == 'war':
			if self.camera.IsGrabbing():
				self.camera.StopGrabbing()
		
		# restore image limit
		self.iep.image_limit = int(self.user_values['maxTriggerCounts']) 
				
		# clear imae event handler
		self.iep.Qimage.queue.clear()
		self.iep.trigger_end = False
		self.iep.read_config()
		self.init_restart_stack()


# Contains a Configuration Event Handler that prints a message for each event method call.
class ConfigurationEventPrinter(pylon.ConfigurationEventHandler):
	def OnAttach(self, camera):
		print("OnAttach event")

	def OnAttached(self, camera):
		print("OnAttached event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnOpen(self, camera):
		print("OnOpen event for device ", camera.GetDeviceInfo().GetModelName())

	def OnOpened(self, camera):
		print("OnOpened event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnGrabStart(self, camera):
		print("OnGrabStart event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnGrabStarted(self, camera):
		print("OnGrabStarted event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnGrabStop(self, camera):
		print("OnGrabStop event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnGrabStopped(self, camera):
		print("OnGrabStopped event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnClose(self, camera):
		print("OnClose event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnClosed(self, camera):
		print("OnClosed event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnDestroy(self, camera):
		print("OnDestroy event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnDestroyed(self, camera):
		print("OnDestroyed event")

	def OnDetach(self, camera):
		print("OnDetach event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnDetached(self, camera):
		print("OnDetached event for device ",
			  camera.GetDeviceInfo().GetModelName())

	def OnGrabError(self, camera, errorMessage):
		print("OnGrabError event for device ",
			  camera.GetDeviceInfo().GetModelName())
		print("Error Message: ", errorMessage)

	def OnCameraDeviceRemoved(self, camera):
		print("OnCameraDeviceRemoved event for device ",
			  camera.GetDeviceInfo().GetModelName())

class ImageEventPrinter(pylon.ImageEventHandler):
	def __init__(self, basic_cam_config):
		super().__init__()
		self.Qimage = Queue()
		self.basic_cam_config_path = basic_cam_config
		self.trigger_end = True
		self.read_config()

	def read_config(self):
		self.config = configparser.ConfigParser()
		self.config.read(self.basic_cam_config_path, encoding='utf-8')
		
		# Setting variable
		self.image_limit = int(self.config['SETTING']['maxTriggerCounts'])
		
		# Capture variable
		self.capture_mode = self.config['CAPTURE']['check']
		self.capture_path = self.config['CAPTURE']['path']
		self.cycle = self.config['CAPTURE']['cycle']

	def OnImagesSkipped(self, camera, countOfSkippedImages):
		print("OnImagesSkipped event for device ",
						 camera.GetDeviceInfo().GetModelName())
		print(countOfSkippedImages, " images have been skipped.")
		print('-skip-------------------------------------------')

	def OnImageGrabbed(self, camera, grabResult):
		# Stop when reaches max trigger counts
		if self.image_limit == 0:
			if camera.TriggerMode() == 'Off':
				self.image_limit += 5000
			else:
				print('[INFO] End of trigger')
				self.trigger_end = True
				self.image_limit -= 1
				return

		elif self.image_limit < 0:
			return

		# Image grabbed successfully?
		if grabResult.GrabSucceeded():
			try:
				converter = pylon.ImageFormatConverter()
				converter.OutputPixelFormat = pylon.PixelType_BGR8packed
				converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
				img = converter.Convert(grabResult)
				img = img.GetArray()

				self.Qimage.put(img)
				self.image_limit -= 1

			except Exception as e:
				print(traceback.format_exc())
		else:
			print(f"Error: {grabResult.GetErrorCode(), grabResult.GetErrorDescription()}")


if __name__ == '__main__':
	cam = SoftwareTriggerBalser('cam1', 'config/basic_cam_config.INI', 'log')
	Thread(target=cam.stream_mode, daemon=True, args=(True,)).start()

	basic_cam_config = configparser.ConfigParser()
	basic_cam_config.read(cam.basic_cam_path, encoding='utf-8')
	imgcount = 0

	while 1:
		time.sleep(0.05)

		# standby image
		if cam.iep.trigger_end:
			image = cv2.imread('stanby.jpg')

		# 1 - get image
		# Strongly recommand using 'while' when checking Qimage.empty()
		# It can shorten your Cycle time almost twice as before
		while not cam.iep.Qimage.empty():
			image = cam.iep.Qimage.get()
			imgcount += 1
			print('get image:', imgcount)
			# show image
			image = resize(image, width=600)
			cv2.imshow('output', image)
			key = cv2.waitKey(1)
		
		# 2 - image postprocessing (show, resize and etc)
		# show image
		image = resize(image, width=600)
		cv2.imshow('output', image)
		key = cv2.waitKey(5) & 0xff

		if key == ord('q'):
			break
		
		# 3 - trigger on3
		# It must be executed with daemon thread
		# elif key == ord('1'):
		# 	Thread(target = cam.trigger_on, daemon=True).start()
		# 	imgcount = 0
		
		# elif key == ord('2'):
		# 	cam.stream_mode(True)

		# elif key == ord('3'):
		# 	cam.stream_mode(False)

		print('qsize:', cam.iep.Qimage.qsize())
