import cv2

def getDevices() -> list[int]:
	"""
	Returns a list of video device indexes for opencv. 
	Credit: Patrick Yeadon on StackOverflow - https://stackoverflow.com/questions/8044539/listing-available-devices-in-python-opencv
	"""
	index = 0
	arr = []
	while True:
		cap = cv2.VideoCapture(index)
		if not cap.read()[0]:
			break
		else:
			arr.append(index)
		cap.release()
		index += 1
	return arr
