import cv2, time
import numpy as np

from enums.ColormapEnum import Colormap
from keybinds import *

class ThermalCameraController:
    def __init__(self, deviceIndex: int = 0, width: int = 256, height: int = 192, scale: int = 3, contrast: float = 1.0, colormap: Colormap = Colormap.NONE, blurRadius: int = 0, threshold: int = 2, isHudVisible: bool = True):
        self._deviceIndex = deviceIndex
        self._width = width
        self._height = height
        self._scale = scale
        self._contrast = contrast
        self._colormap = colormap
        self._blurRadius = blurRadius
        self._threshold = threshold
        self._isHudVisible = isHudVisible
        
        self._scaledWidth = self._width * self._scale
        self._scaledHeight = self._height * self._scale
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._isRecording = False
        self._isFullscreen = False
        self._elapsed = "00:00:00"
        self._snaptime = "None"
        self._colormapText = "None"
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

    def _drawGUI(self, heatmap):
        
        return heatmap

    def _drawHUD(self, heatmap):
        
        # Display black box for our data
        cv2.rectangle(heatmap, (0, 0),(160, 120), (0,0,0), -1)
        
        # Put text in the box
        cv2.putText(heatmap,'Avg Temp: '+str(self._avgtemp)+' C', (10, 14),\
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
            cv2.putText(heatmap,'Recording: '+self._isRecording, (10, 112),\
            self._font, 0.4,(200, 200, 200), 1, cv2.LINE_AA)
        else:
            cv2.putText(heatmap,'Recording: '+self._elapsed, (10, 112),\
            self._font, 0.4,(40, 40, 255), 1, cv2.LINE_AA)
            
        return heatmap

    def run(self):
        # Initialize video
        self._cap = cv2.VideoCapture(self._deviceIndex)

        """
        MAJOR CHANGE: Do NOT convert to RGB. For some reason, this breaks the frame temperature data on TS001.
        Originally, it was apparently the opposite: https://stackoverflow.com/questions/63108721/opencv-setting-videocap-property-to-cap-prop-convert-rgb-generates-weird-boolean
        """
        #cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        
        # Initialize the GUI
        cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow('Thermal', self._scaledWidth, self._scaledHeight)

        def rec():
            now = time.strftime("%Y%m%d--%H%M%S")
            #do NOT use mp4 here, it is flakey!
            videoOut = cv2.VideoWriter(now+'output.avi', cv2.VideoWriter_fourcc(*'XVID'),25, (self._scaledWidth,self._scaledHeight))
            return(videoOut)

        def snapshot(heatmap):
            #I would put colons in here, but it Win throws a fit if you try and open them!
            now = time.strftime("%Y%m%d-%H%M%S") 
            self._snaptime = time.strftime("%H:%M:%S")
            cv2.imwrite("TC001"+now+".png", heatmap)
            return self._snaptime

        while(self._cap.isOpened()):
            # Capture frame-by-frame
            ret, frame = self._cap.read()
            if ret == True:
                imdata,thdata = np.array_split(frame, 2)
                # Now parse the data from the bottom frame and convert to temp!
                # https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
                # Huge props to LeoDJ for figuring out how the data is stored and how to compute temp from it.
                # Grab data from the center pixel...
                hi = int(thdata[96][128][0])
                lo = int(thdata[96][128][1])
                lo = lo*256
                rawtemp = hi+lo
                temp = (rawtemp/64)-273.15
                temp = round(temp,2)

                # Find the max temperature in the frame
                lomax = int(thdata[...,1].max())
                posmax = int(thdata[...,1].argmax())
                # Since argmax returns a linear index, convert back to row and col
                mcol,mrow = divmod(posmax,self._width)
                himax = int(thdata[mcol][mrow][0])
                lomax=lomax*256
                maxtemp = himax+lomax
                maxtemp = (maxtemp/64)-273.15
                maxtemp = round(maxtemp,2)

                
                # Find the lowest temperature in the frame
                lomin = int(thdata[...,1].min())
                posmin = int(thdata[...,1].argmin())
                
                # Since argmax returns a linear index, convert back to row and col
                lcol,lrow = divmod(posmin, self._width)
                himin = int(thdata[lcol][lrow][0])
                lomin=lomin*256
                mintemp = int(himin+lomin)
                mintemp = (mintemp/64)-273.15
                mintemp = round(mintemp,2)

                # Find the average temperature in the frame
                loavg = int(thdata[...,1].mean())
                hiavg = int(thdata[...,0].mean())
                loavg=loavg*256
                avgtemp = loavg+hiavg
                avgtemp = (avgtemp/64)-273.15
                avgtemp = round(avgtemp,2)
                
                # Contrast
                bgr = cv2.convertScaleAbs(imdata, alpha=self._contrast)#Contrast
                # Bicubic interpolate, upscale and blur
                bgr = cv2.resize(bgr,(self._scaledWidth,self._scaledHeight),interpolation=cv2.INTER_CUBIC)#Scale up!
                if self._blurRadius>0:
                    bgr = cv2.blur(bgr,(self._blurRadius,self._blurRadius))

                # Apply colormap
                heatmap = bgr
                match Colormap(self._colormap):
                    case Colormap.JET:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_JET)
                        self._colormapText = 'Jet'
                    case Colormap.HOT:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_HOT)
                        self._colormapText = 'Hot'
                    case Colormap.MAGMA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_MAGMA)
                        self._colormapText = 'Magma'
                    case Colormap.INFERNO:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_INFERNO)
                        self._colormapText = 'Inferno'
                    case Colormap.PLASMA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PLASMA)
                        self._colormapText = 'Plasma'
                    case Colormap.BONE:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_BONE)
                        self._colormapText = 'Bone'
                    case Colormap.SPRING:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_SPRING)
                        self._colormapText = 'Spring'
                    case Colormap.AUTUMN:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_AUTUMN)
                        self._colormapText = 'Autumn'
                    case Colormap.VIRIDIS:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_VIRIDIS)
                        self._colormapText = 'Viridis'
                    case Colormap.PARULA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PARULA)
                        self._colormapText = 'Parula'
                    case Colormap.INV_RAINBOW:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_RAINBOW)
                        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
                        self._colormapText = 'Inv Rainbow'
                    case _:
                        heatmap = bgr
                        self._colormapText = 'None'

                # Draw crosshairs
                heatmap = self._drawCrosshairs(heatmap)
                
                # Draw temp
                heatmap = self._drawTemp(heatmap, temp=temp)

                # Draw HUD
                if self._isHudVisible==True:
                    heatmap = self._drawGUI(heatmap=heatmap)
                
                #Yeah, this looks like we can probably do this next bit more efficiently!
                # Display floating max temp
                if maxtemp > avgtemp+self._threshold:
                    cv2.circle(heatmap, (mrow*self._scale, mcol*self._scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (mrow*self._scale, mcol*self._scale), 5, (0,0,255), -1)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*self._scale)+10, (mcol*self._scale)+5),\
                    self._font, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*self._scale)+10, (mcol*self._scale)+5),\
                    self._font, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

                # Display floating min temp
                if mintemp < avgtemp-self._threshold:
                    cv2.circle(heatmap, (lrow*self._scale, lcol*self._scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (lrow*self._scale, lcol*self._scale), 5, (255,0,0), -1)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*self._scale)+10, (lcol*self._scale)+5),\
                    self._font, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*self._scale)+10, (lcol*self._scale)+5),\
                    self._font, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

                # Display image
                cv2.imshow('Thermal', heatmap)

                if self._isRecording == True:
                    self._elapsed = (time.time() - start)
                    self._elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed)) 
                    videoOut.write(heatmap)
                
                keyPress = cv2.waitKey(1)
                if keyPress == ord(KEY_INCREASE_BLUR): # Increase blur radius
                    self._blurRadius += 1
                if keyPress == ord(KEY_DECREASE_BLUR): # Decrease blur radius
                    self._blurRadius -= 1
                    if self._blurRadius <= 0:
                        self._blurRadius = 0

                if keyPress == ord(KEY_INCREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Increase threshold
                    self._threshold += 1
                if keyPress == ord(KEY_DECREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Decrease threashold
                    self._threshold -= 1
                    if self._threshold <= 0:
                        self._threshold = 0

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

                if keyPress == ord(KEY_FULLSCREEN): # Enable fullscreen
                    self._isFullscreen = True
                    cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                if keyPress == ord(KEY_WINDOWED): # Disable fullscreen
                    self._isFullscreen = False
                    cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_AUTOSIZE,cv2.WINDOW_GUI_NORMAL)
                    cv2.resizeWindow('Thermal', self._scaledWidth,self._scaledHeight)

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


                if keyPress == ord(KEY_TOGGLE_HUD): # Toggle HUD
                    if hud==True:
                        hud=False
                    elif hud==False:
                        hud=True

                if keyPress == ord(KEY_CYCLE_THROUGH_COLORMAPS): # Cycle through color maps
                    colormap += 1
                    if colormap == 11:
                        colormap = 0

                if keyPress == ord(KEY_RECORD) and recording == False: # Start reording
                    videoOut = rec()
                    recording = True
                    start = time.time()
                    
                if keyPress == ord(KEY_STOP): # Stop reording
                    recording = False
                    elapsed = "00:00:00"

                if keyPress == ord(KEY_SNAPSHOT): # Take a snapshot
                    snaptime = snapshot(heatmap)

                if keyPress == ord(KEY_QUIT):
                    break
                    capture.release()
                    cv2.destroyAllWindows()