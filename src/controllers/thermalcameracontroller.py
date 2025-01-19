import cv2, time, os
import numpy as np

from enums.ColormapEnum import Colormap
from controllers.guiController import GuiController
from constants.keybinds import *

class ThermalCameraController:
    def __init__(self, deviceIndex: int = 0, width: int = 256, height: int = 192, fps: int = 25, deviceName: str = "TC001", mediaOutputPath: str = f"{os.getcwd()}/output"):
        # Parameters init
        self._deviceIndex: int = deviceIndex
        self._deviceName: str = deviceName
        self._width: int = width
        self._height: int = height
        self._fps: int = fps

        # Calculated values init
        self._rawTemp = 0
        self._temp = 0
        self._mcol: int = 0
        self._mrow: int = 0
        self._lcol: int = 0
        self._lrow: int = 0
        self._maxTemp = 0
        self._minTemp = 0
        self._avgTemp = 0
        
        # Media/recording init
        self._isRecording = False
        self._mediaOutputPath: str = mediaOutputPath
        
        if not os.path.exists(self._mediaOutputPath):
            os.makedirs(self._mediaOutputPath)
        
        # GUI Init
        self._guiController = GuiController(
            windowTitle="Thermal",
            width=self._width,
            height=self._height
        )
        
        # OpenCV init
        self._cap = None
        self._videoOut = None
    
    @staticmethod
    def printBindings():
        """
        Print key bindings for the program.
        """
        print('Key Bindings:\n')
        print(f'{KEY_INCREASE_BLUR} {KEY_DECREASE_BLUR}: Increase/Decrease Blur')
        print(f'{KEY_INCREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD} {KEY_DECREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD}: Floating High and Low Temp Label Threshold')
        print(f'{KEY_INCREASE_SCALE} {KEY_DECREASE_SCALE}: Change Interpolated scale Note: This will not change the window size on the Pi')
        print(f'{KEY_INCREASE_CONTRAST} {KEY_DECREASE_CONTRAST}: Contrast')
        print(f'{KEY_FULLSCREEN} {KEY_WINDOWED}: Fullscreen Windowed (note going back to windowed does not seem to work on the Pi!)')
        print(f'{KEY_RECORD} {KEY_STOP}: Record and Stop')
        print(f'{KEY_SNAPSHOT} : Snapshot')
        print(f'{KEY_CYCLE_THROUGH_COLORMAPS} : Cycle through ColorMaps')
        print(f'{KEY_TOGGLE_HUD} : Toggle HUD')
 
    @staticmethod
    def printCredits():
        """
        Print credits/author(s) for the program.
        """
        print('Original Author: Les Wright 21 June 2023')
        print('https://youtube.com/leslaboratory')
        print('Fork Author: Riley Meyerkorth 17 January 2025')
        print('A Python program to read, parse and display thermal data from the Topdon TC001 and TS001 Thermal cameras!\n')

    def _drawGUI(self, imdata):
        """
        Draws the GUI elements on the thermal image.
        """
        # Apply affects
        img = self._guiController.applyEffects(imdata=imdata)

        # Apply colormap
        img = self._guiController.applyColormap(img)

        # Draw crosshairs
        img = self._guiController.drawCrosshairs(img)
        
        # Draw temp
        img = self._guiController.drawTemp(img, temp=self._temp)

        # Draw HUD
        if self._guiController.isHudVisible == True:
            img = self._guiController.drawHUD(img, self._avgTemp, self._isRecording)
        
        # Display floating max temp
        if self._maxTemp > self._avgTemp + self._guiController.threshold:
            img = self._guiController.drawMaxTemp(img, self._mrow, self._mcol, self._maxTemp)

        # Display floating min temp
        if self._minTemp < self._avgTemp - self._guiController.threshold:
            img = self._guiController.drawMinTemp(img, self._lrow, self._lcol, self._minTemp)
            
        # Update recording stats
        if self._isRecording == True:
            self._guiController.updateRecordingStats()

        return img
    
    def _checkForKeyPress(self, keyPress: int, img):
        """
        Checks and acts on key presses.
        """
        ### BLUR RADIUS
        if keyPress == ord(KEY_INCREASE_BLUR): # Increase blur radius
            self._guiController.blurRadius += 1
        if keyPress == ord(KEY_DECREASE_BLUR): # Decrease blur radius
            self._guiController.blurRadius -= 1
            if self._guiController.blurRadius <= 0:
                self._guiController.blurRadius = 0

        ### THRESHOLD CONTROL
        if keyPress == ord(KEY_INCREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Increase threshold
            self._guiController.threshold += 1
        if keyPress == ord(KEY_DECREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Decrease threashold
            self._guiController.threshold -= 1
            if self._guiController.threshold <= 0:
                self._guiController.threshold = 0

        ### SCALE CONTROLS
        if keyPress == ord(KEY_INCREASE_SCALE): # Increase scale
            self._guiController.scale += 1
            if self._guiController.scale >=5:
                self._guiController.scale = 5
            self._guiController.scaledWidth = self._width*self._guiController.scale
            self._guiController.scaledHeight = self._height*self._guiController.scale
            if self._guiController.isFullscreen == False:
                cv2.resizeWindow(self._guiController.windowTitle, self._guiController.scaledWidth, self._guiController.scaledHeight)
        if keyPress == ord(KEY_DECREASE_SCALE): # Decrease scale
            self._guiController.scale -= 1
            if self._guiController.scale <= 1:
                self._guiController.scale = 1
            self._guiController.scaledWidth = self._width*self._guiController.scale
            self._guiController.scaledHeight = self._height*self._guiController.scale
            if self._guiController.isFullscreen == False:
                cv2.resizeWindow(self._guiController.windowTitle, self._guiController.scaledWidth,self._guiController.scaledHeight)

        ### FULLSCREEN CONTROLS
        if keyPress == ord(KEY_FULLSCREEN): # Enable fullscreen
            self._guiController.isFullscreen = True
            cv2.namedWindow(self._guiController.windowTitle, cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(self._guiController.windowTitle, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        if keyPress == ord(KEY_WINDOWED): # Disable fullscreen
            self._guiController.isFullscreen = False
            cv2.namedWindow(self._guiController.windowTitle, cv2.WINDOW_GUI_NORMAL)
            cv2.setWindowProperty(self._guiController.windowTitle, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_GUI_NORMAL)
            cv2.resizeWindow(self._guiController.windowTitle, self._guiController.scaledWidth, self._guiController.scaledHeight)

        ### CONTRAST CONTROLS
        if keyPress == ord(KEY_INCREASE_CONTRAST): # Increase contrast
            self._guiController.contrast += 0.1
            self._guiController.contrast = round(self._guiController.contrast,1) #fix round error
            if self._guiController.contrast >= 3.0:
                self._guiController.contrast=3.0
        if keyPress == ord(KEY_DECREASE_CONTRAST): # Decrease contrast
            self._guiController.contrast -= 0.1
            self._guiController.contrast = round(self._guiController.contrast,1)#fix round error
            if self._guiController.contrast<=0:
                self._guiController.contrast = 0.0

        ### HUD CONTROLS
        if keyPress == ord(KEY_TOGGLE_HUD): # Toggle HUD
            if self._guiController.isHudVisible==True:
                self._guiController.isHudVisible=False
            elif self._guiController.isHudVisible==False:
                self._guiController.isHudVisible=True

        ### COLOR MAPS
        if keyPress == ord(KEY_CYCLE_THROUGH_COLORMAPS): # Cycle through color maps
            if self._guiController.colormap.value+1 > Colormap.INV_RAINBOW.value:
                self._guiController.colormap = Colormap.NONE
            else:
                self._guiController.colormap = Colormap(self._guiController.colormap.value + 1)
        
        ### RECORDING/MEDIA CONTROLS
        if keyPress == ord(KEY_RECORD) and self._isRecording == False: # Start reording
            self._videoOut = self._record()
            self._isRecording = True
            self._guiController.recordingStartTime = time.time()
            
        if keyPress == ord(KEY_STOP): # Stop reording
            self._isRecording = False
            self._guiController.elapsed = "00:00:00"

        if keyPress == ord(KEY_SNAPSHOT): # Take a snapshot
            self._guiController.snaptime = self._snapshot(img)

    def _record(self):
        """
        STart recording video to file.
        """
        currentTimeStr = time.strftime("%Y%m%d--%H%M%S")
        #do NOT use mp4 here, it is flakey!
        self._videoOut = cv2.VideoWriter(
            f"{self._mediaOutputPath}/{currentTimeStr}-output.avi",
            cv2.VideoWriter_fourcc(*'XVID'),
            self._fps,
            (self._guiController.scaledWidth, self._guiController.scaledHeight))
        return self._videoOut
    
    def _snapshot(self, img):
        """
        Takes a snapshot of the current frame.
        """
        #I would put colons in here, but it Win throws a fit if you try and open them!
        currentTimeStr = time.strftime("%Y%m%d-%H%M%S") 
        self._guiController.snaptime = time.strftime("%H:%M:%S")
        cv2.imwrite(f"{self._mediaOutputPath}/{self._deviceName}-{currentTimeStr}.png", img)
        return self._guiController.snaptime

    def normalizeTemperature(self, rawTemp: float, d: int = 64, c: float = 273.15) -> float:
        """
        Normalizes/converts the raw temperature data using the formula found by LeoDJ.
        Link: https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
        """
        return (rawTemp/d) - c

    def calculateTemperature(self, thdata):
        """
        Calculates the (normalized) temperature of the frame.
        """
        raw = self.calculateRawTemperature(thdata)
        return round(self.normalizeTemperature(raw), 2)

    def calculateRawTemperature(self, thdata):
        """
        Calculates the raw temperature of the frame.
        """
        hi = int(thdata[96][128][0])
        lo = int(thdata[96][128][1])
        lo = lo*256
        return hi+lo

    def calculateAverageTemperature(self, thdata):
        """
        Calculates the average temperature of the frame.
        """
        loavg = int(thdata[...,1].mean())
        hiavg = int(thdata[...,0].mean())
        loavg=loavg*256
        return round(self.normalizeTemperature(loavg+hiavg), 2)

    def calculateMinimumTemperature(self, thdata):
        """
        Calculates the minimum temperature of the frame.
        """
        # Find the min temperature in the frame
        lomin = int(thdata[...,1].min())
        posmin = int(thdata[...,1].argmin())
        
        # Since argmax returns a linear index, convert back to row and col
        self._lcol, self._lrow = divmod(posmin, self._width)
        himin = int(thdata[self._lcol][self._lrow][0])
        lomin=lomin*256
        
        return round(self.normalizeTemperature(himin+lomin), 2)

    def calculateMaximumTemperature(self, thdata):
        """
        Calculates the maximum temperature of the frame.
        """
        # Find the max temperature in the frame
        lomax = int(thdata[...,1].max())
        posmax = int(thdata[...,1].argmax())

        # Since argmax returns a linear index, convert back to row and col
        self._mcol, self._mrow = divmod(posmax, self._width)
        himax = int(thdata[self._mcol][self._mrow][0])
        lomax=lomax*256
        
        return round(self.normalizeTemperature(himax+lomax), 2)

    def run(self):
        """
        Runs the main runtime loop for the program.
        """
        # Initialize video
        self._cap = cv2.VideoCapture(self._deviceIndex)

        """
        MAJOR CHANGE: Do NOT convert to RGB. For some reason, this breaks the frame temperature data on TS001.
        Originally, it was the opposite: https://stackoverflow.com/questions/63108721/opencv-setting-videocap-property-to-cap-prop-convert-rgb-generates-weird-boolean
        """
        #cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)

        # Start main runtime loop
        while(self._cap.isOpened()):
            ret, frame = self._cap.read()
            if ret == True:
                # Split frame into two parts: image data and thermal data
                imdata, thdata = np.array_split(frame, 2)
                
                # Now parse the data from the bottom frame and convert to temp!
                # Grab data from the center pixel...
                self._rawTemp = self.calculateRawTemperature(thdata)
                self._temp = self.calculateTemperature(thdata)

                # Calculate minimum temperature
                self._minTemp = self.calculateMinimumTemperature(thdata)
                
                # Calculate maximum temperature
                self._maxTemp = self.calculateMaximumTemperature(thdata)

                # Find the average temperature in the frame
                self._avgTemp = self.calculateAverageTemperature(thdata)
                
                # Draw GUI elements
                heatmap = self._drawGUI(imdata=imdata)

                # Check for recording
                if self._isRecording == True:
                    self._videoOut.write(heatmap)
                    
                # Check for quit and other inputs
                keyPress = cv2.waitKey(1)
                if keyPress == ord(KEY_QUIT):
                    # Check for recording and close out
                    if self._isRecording == True:
                        self._videoOut.release()
                    return

                self._checkForKeyPress(keyPress=keyPress, img=heatmap)
                
                # Display image
                cv2.imshow(self._guiController.windowTitle, heatmap)