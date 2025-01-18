import cv2, time
import numpy as np

from enums.ColormapEnum import Colormap
from keybinds import *

class ThermalCameraController:
    def __init__(self, deviceIndex: int = 0, width: int = 256, height: int = 192, scale: int = 3, contrast: float = 1.0, colormap: Colormap = Colormap.NONE, blurRadius: int = 0, threshold: int = 2, isHudVisible: bool = True):
        # Parameters init
        self._deviceIndex: int = deviceIndex
        self._width: int = width
        self._height: int = height
        self._scale: int = scale
        self._contrast: float = contrast
        self._colormap: Colormap = colormap
        self._blurRadius: float = blurRadius
        self._threshold: int = threshold
        self._isHudVisible: bool = isHudVisible

        # Calculated values init
        self._scaledWidth: int = self._width * self._scale
        self._scaledHeight: int = self._height * self._scale
        self._rawTemp = 0
        self._temp = 0
        self._mcol: int = 0
        self._mrow: int = 0
        self._lcol: int = 0
        self._lrow: int = 0
        self._maxTemp = 0
        self._minTemp = 0
        self._avgTemp = 0

        # Other init
        self._windowTitle = "Thermal"
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._isRecording = False
        self._isFullscreen = False
        self._elapsed = "00:00:00"
        self._snaptime = "None"
        self._colormapText = "None"
        self._videoOut = None
        self._start = None
        self._cap = None
    
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
        # Apply affects
        heatmap = self._applyEffects(imdata=imdata)

        # Apply colormap
        heatmap = self._applyColormap(heatmap=heatmap)

        # Draw crosshairs
        heatmap = self._drawCrosshairs(heatmap)
        
        # Draw temp
        heatmap = self._drawTemp(heatmap, temp=self._temp)

        # Draw HUD
        if self._isHudVisible == True:
            heatmap = self._drawHUD(heatmap=heatmap)
        
        # Display floating max temp
        if self._maxTemp > self._avgTemp + self._threshold:
            heatmap = self._drawMaxTemp(heatmap)

        # Display floating min temp
        if self._minTemp < self._avgTemp - self._threshold:
            heatmap = self._drawMinTemp(heatmap)

        return heatmap

    def _drawTemp(self, heatmap, temp):
        cv2.putText(heatmap,str(temp)+' C', (int(self._scaledWidth/2)+10, int(self._scaledHeight/2)-10),\
        self._font, 0.45,(0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(heatmap,str(temp)+' C', (int(self._scaledWidth/2)+10, int(self._scaledHeight/2)-10),\
        self._font, 0.45,(0, 255, 255), 1, cv2.LINE_AA)
        
        return heatmap

    def _drawCrosshairs(self, heatmap):
        cv2.line(heatmap,(int(self._scaledWidth/2),int(self._scaledHeight/2)+20),\
        (int(self._scaledWidth/2),int(self._scaledHeight/2)-20),(255,255,255),2) #vline
        cv2.line(heatmap,(int(self._scaledWidth/2)+20,int(self._scaledHeight/2)),\
        (int(self._scaledWidth/2)-20,int(self._scaledHeight/2)),(255,255,255),2) #hline

        cv2.line(heatmap,(int(self._scaledWidth/2),int(self._scaledHeight/2)+20),\
        (int(self._scaledWidth/2),int(self._scaledHeight/2)-20),(0,0,0),1) #vline
        cv2.line(heatmap,(int(self._scaledWidth/2)+20,int(self._scaledHeight/2)),\
        (int(self._scaledWidth/2)-20,int(self._scaledHeight/2)),(0,0,0),1) #hline
        
        return heatmap

    def _drawHUD(self, heatmap):
        
        # Display black box for our data
        cv2.rectangle(heatmap, (0, 0),(160, 120), (0,0,0), -1)
        
        # Put text in the box
        cv2.putText(heatmap,'Avg Temp: '+str(self._avgTemp)+' C', (10, 14),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Label Threshold: '+str(self._threshold)+' C', (10, 28),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Colormap: '+self._colormapText, (10, 42),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Blur: '+str(self._blurRadius)+' ', (10, 56),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Scaling: '+str(self._scale)+' ', (10, 70),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Contrast: '+str(self._contrast)+' ', (10, 84),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(heatmap,'Snapshot: '+self._snaptime+' ', (10, 98),\
        self._font, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

        if self._isRecording == False:
            cv2.putText(heatmap,'Recording: '+str(self._isRecording), (10, 112),\
            self._font, 0.4,(200, 200, 200), 1, cv2.LINE_AA)
        else:
            cv2.putText(heatmap,'Recording: '+self._elapsed, (10, 112),\
            self._font, 0.4,(40, 40, 255), 1, cv2.LINE_AA)
            
        return heatmap
    
    def _drawMaxTemp(self, heatmap):
        cv2.circle(heatmap, (self._mrow*self._scale, self._mcol*self._scale), 5, (0,0,0), 2)
        cv2.circle(heatmap, (self._mrow*self._scale, self._mcol*self._scale), 5, (0,0,255), -1)
        cv2.putText(heatmap,str(self._maxTemp)+' C', ((self._mrow*self._scale)+10, (self._mcol*self._scale)+5),\
        self._font, 0.45,(0,0,0), 2, cv2.LINE_AA)
        cv2.putText(heatmap,str(self._maxTemp)+' C', ((self._mrow*self._scale)+10, (self._mcol*self._scale)+5),\
        self._font, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

        return heatmap
    
    def _drawMinTemp(self, heatmap):
        cv2.circle(heatmap, (self._lrow*self._scale, self._lcol*self._scale), 5, (0,0,0), 2)
        cv2.circle(heatmap, (self._lrow*self._scale, self._lcol*self._scale), 5, (255,0,0), -1)
        cv2.putText(heatmap,str(self._minTemp)+' C', ((self._lrow*self._scale)+10, (self._lcol*self._scale)+5),\
        self._font, 0.45,(0,0,0), 2, cv2.LINE_AA)
        cv2.putText(heatmap,str(self._minTemp)+' C', ((self._lrow*self._scale)+10, (self._lcol*self._scale)+5),\
        self._font, 0.45,(0, 255, 255), 1, cv2.LINE_AA)
    
    def _checkForKeyPress(self, keyPress: int, heatmap):
        ### BLUR RADIUS
        if keyPress == ord(KEY_INCREASE_BLUR): # Increase blur radius
            self._blurRadius += 1
        if keyPress == ord(KEY_DECREASE_BLUR): # Decrease blur radius
            self._blurRadius -= 1
            if self._blurRadius <= 0:
                self._blurRadius = 0

        ### THRESHOLD CONTROL
        if keyPress == ord(KEY_INCREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Increase threshold
            self._threshold += 1
        if keyPress == ord(KEY_DECREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Decrease threashold
            self._threshold -= 1
            if self._threshold <= 0:
                self._threshold = 0

        ### SCALE CONTROLS
        if keyPress == ord(KEY_INCREASE_SCALE): # Increase scale
            self._scale += 1
            if self._scale >=5:
                self._scale = 5
            self._scaledWidth = self._width*self._scale
            self._scaledHeight = self._height*self._scale
            if self._isFullscreen == False:
                cv2.resizeWindow('Thermal', self._scaledWidth,self._scaledHeight)
        if keyPress == ord(KEY_DECREASE_SCALE): # Decrease scale
            self._scale -= 1
            if self._scale <= 1:
                self._scale = 1
            self._scaledWidth = self._width*self._scale
            self._scaledHeight = self._height*self._scale
            if self._isFullscreen == False:
                cv2.resizeWindow('Thermal', self._scaledWidth,self._scaledHeight)

        ### FULLSCREEN CONTROLS
        if keyPress == ord(KEY_FULLSCREEN): # Enable fullscreen
            self._isFullscreen = True
            cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
        if keyPress == ord(KEY_WINDOWED): # Disable fullscreen
            self._isFullscreen = False
            cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
            cv2.setWindowProperty('Thermal',cv2.WND_PROP_AUTOSIZE,cv2.WINDOW_GUI_NORMAL)
            cv2.resizeWindow('Thermal', self._scaledWidth,self._scaledHeight)

        ### CONTRAST CONTROLS
        if keyPress == ord(KEY_INCREASE_CONTRAST): # Increase contrast
            self._contrast += 0.1
            self._contrast = round(self._contrast,1) #fix round error
            if self._contrast >= 3.0:
                self._contrast=3.0
        if keyPress == ord(KEY_DECREASE_CONTRAST): # Decrease contrast
            self._contrast -= 0.1
            self._contrast = round(self._contrast,1)#fix round error
            if self._contrast<=0:
                self._contrast = 0.0

        ### HUD CONTROLS
        if keyPress == ord(KEY_TOGGLE_HUD): # Toggle HUD
            if self._isHudVisible==True:
                self._isHudVisible=False
            elif self._isHudVisible==False:
                self._isHudVisible=True

        ### COLOR MAPS
        if keyPress == ord(KEY_CYCLE_THROUGH_COLORMAPS): # Cycle through color maps
            if self._colormap.value+1 > Colormap.INV_RAINBOW.value:
                self._colormap = Colormap.NONE
            else:
                self._colormap = Colormap(self._colormap.value + 1)
        
        ### RECORDING/MEDIA CONTROLS
        if keyPress == ord(KEY_RECORD) and self._isRecording == False: # Start reording
            self._videoOut = self._record()
            self._isRecording = True
            self._start = time.time()
            
        if keyPress == ord(KEY_STOP): # Stop reording
            self._isRecording = False
            self._elapsed = "00:00:00"

        if keyPress == ord(KEY_SNAPSHOT): # Take a snapshot
            self._snaptime = self._snapshot(heatmap)

    def _applyColormap(self, heatmap):
        match Colormap(self._colormap):
            case Colormap.JET:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
                self._colormapText = 'Jet'
            case Colormap.HOT:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_HOT)
                self._colormapText = 'Hot'
            case Colormap.MAGMA:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_MAGMA)
                self._colormapText = 'Magma'
            case Colormap.INFERNO:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_INFERNO)
                self._colormapText = 'Inferno'
            case Colormap.PLASMA:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_PLASMA)
                self._colormapText = 'Plasma'
            case Colormap.BONE:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_BONE)
                self._colormapText = 'Bone'
            case Colormap.SPRING:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_SPRING)
                self._colormapText = 'Spring'
            case Colormap.AUTUMN:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_AUTUMN)
                self._colormapText = 'Autumn'
            case Colormap.VIRIDIS:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_VIRIDIS)
                self._colormapText = 'Viridis'
            case Colormap.PARULA:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_PARULA)
                self._colormapText = 'Parula'
            case Colormap.INV_RAINBOW:
                heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_RAINBOW)
                heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
                self._colormapText = 'Inv Rainbow'
            case _:
                self._colormapText = 'None'

        return heatmap

    def _applyEffects(self, imdata):
        # Contrast
        heatmap = cv2.convertScaleAbs(imdata, alpha=self._contrast)
        # Bicubic interpolate, upscale and blur
        heatmap = cv2.resize(heatmap,(self._scaledWidth,self._scaledHeight),interpolation=cv2.INTER_CUBIC)#Scale up!
        if self._blurRadius>0:
            heatmap = cv2.blur(heatmap,(self._blurRadius,self._blurRadius))

        return heatmap

    def _record(self):
        now = time.strftime("%Y%m%d--%H%M%S")
        #do NOT use mp4 here, it is flakey!
        self._videoOut = cv2.VideoWriter(now+'output.avi', cv2.VideoWriter_fourcc(*'XVID'),25, (self._scaledWidth,self._scaledHeight))
        return self._videoOut
    
    def _snapshot(self, heatmap):
        #I would put colons in here, but it Win throws a fit if you try and open them!
        now = time.strftime("%Y%m%d-%H%M%S") 
        self._snaptime = time.strftime("%H:%M:%S")
        cv2.imwrite("TC001"+now+".png", heatmap)
        return self._snaptime

    def _convertTemperature(self, rawTemp: float, d: int = 64, c: float = 273.15) -> float:
        return (rawTemp/d) - c

    def run(self):
        # Initialize video
        self._cap = cv2.VideoCapture(self._deviceIndex)

        """
        MAJOR CHANGE: Do NOT convert to RGB. For some reason, this breaks the frame temperature data on TS001.
        Originally, it was apparently the opposite: https://stackoverflow.com/questions/63108721/opencv-setting-videocap-property-to-cap-prop-convert-rgb-generates-weird-boolean
        """
        #cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        
        # Initialize the GUI
        cv2.namedWindow(self._windowTitle,cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow(self._windowTitle, self._scaledWidth, self._scaledHeight)

        while(self._cap.isOpened()):
            # Capture frame-by-frame
            ret, frame = self._cap.read()
            if ret == True:
                imdata, thdata = np.array_split(frame, 2)
                # Now parse the data from the bottom frame and convert to temp!
                # https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
                # Huge props to LeoDJ for figuring out how the data is stored and how to compute temp from it.
                # Grab data from the center pixel...
                hi = int(thdata[96][128][0])
                lo = int(thdata[96][128][1])
                lo = lo*256
                self._rawTemp = hi+lo
                self._temp = round(self._convertTemperature(self._rawTemp), 2)

                # Find the max temperature in the frame
                lomax = int(thdata[...,1].max())
                posmax = int(thdata[...,1].argmax())

                # Since argmax returns a linear index, convert back to row and col
                self._mcol, self._mrow = divmod(posmax, self._width)
                himax = int(thdata[self._mcol][self._mrow][0])
                lomax=lomax*256
                self._maxTemp = round(self._convertTemperature(himax+lomax), 2)

                
                # Find the min temperature in the frame
                lomin = int(thdata[...,1].min())
                posmin = int(thdata[...,1].argmin())
                
                # Since argmax returns a linear index, convert back to row and col
                self._lcol, self._lrow = divmod(posmin, self._width)
                himin = int(thdata[self._lcol][self._lrow][0])
                lomin=lomin*256
                self._minTemp = round(self._convertTemperature(himin+lomin), 2)

                # Find the average temperature in the frame
                loavg = int(thdata[...,1].mean())
                hiavg = int(thdata[...,0].mean())
                loavg=loavg*256
                self._avgTemp = round(self._convertTemperature(loavg+hiavg), 2)
                
                # Draw GUI elements
                heatmap = self._drawGUI(imdata=imdata)

                # Display image
                cv2.imshow(self._windowTitle, heatmap)

                # Check for recording
                if self._isRecording == True:
                    self._elapsed = (time.time() - self._start)
                    self._elapsed = time.strftime("%H:%M:%S", time.gmtime(self._elapsed)) 
                    self._videoOut.write(heatmap)
                
                # Check for inputs
                keyPress = cv2.waitKey(1)
                self._checkForKeyPress(keyPress=keyPress, heatmap=heatmap)

                # Check for quit
                if keyPress == ord(KEY_QUIT):
                    return