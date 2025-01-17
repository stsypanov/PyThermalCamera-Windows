import cv2, time
import numpy as np

from enums.ColormapEnum import Colormap
from keybinds import *

class Controller:
    def __init__(self):
        pass
    
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

    def run(self):
        # Initialize video
        cap = cv2.VideoCapture(1)

        """
        MAJOR CHANGE: Do NOT convert to RGB. For some reason, this breaks the frame temperature data on TS001.
        Originally, it was apparently the opposite: https://stackoverflow.com/questions/63108721/opencv-setting-videocap-property-to-cap-prop-convert-rgb-generates-weird-boolean
        """
        #cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        
        # Initialize the settings
        width = 256 # Sensor width
        height = 192 # Sensor height
        scale = 3 # Scale multiplier
        newWidth = width*scale 
        newHeight = height*scale
        alpha = 1.0 # Contrast control (1.0-3.0)
        colormap = 0
        font=cv2.FONT_HERSHEY_SIMPLEX
        dispFullscreen = False
        cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow('Thermal', newWidth,newHeight)
        rad = 0 #blur radius
        threshold = 2
        hud = True
        recording = False
        elapsed = "00:00:00"
        snaptime = "None"

        def rec():
            now = time.strftime("%Y%m%d--%H%M%S")
            #do NOT use mp4 here, it is flakey!
            videoOut = cv2.VideoWriter(now+'output.avi', cv2.VideoWriter_fourcc(*'XVID'),25, (newWidth,newHeight))
            return(videoOut)

        def snapshot(heatmap):
            #I would put colons in here, but it Win throws a fit if you try and open them!
            now = time.strftime("%Y%m%d-%H%M%S") 
            snaptime = time.strftime("%H:%M:%S")
            cv2.imwrite("TC001"+now+".png", heatmap)
            return snaptime

        while(cap.isOpened()):
            # Capture frame-by-frame
            ret, frame = cap.read()
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
                mcol,mrow = divmod(posmax,width)
                himax = int(thdata[mcol][mrow][0])
                lomax=lomax*256
                maxtemp = himax+lomax
                maxtemp = (maxtemp/64)-273.15
                maxtemp = round(maxtemp,2)

                
                # Find the lowest temperature in the frame
                lomin = int(thdata[...,1].min())
                posmin = int(thdata[...,1].argmin())
                
                # Since argmax returns a linear index, convert back to row and col
                lcol,lrow = divmod(posmin,width)
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
                bgr = cv2.convertScaleAbs(imdata, alpha=alpha)#Contrast
                # Bicubic interpolate, upscale and blur
                bgr = cv2.resize(bgr,(newWidth,newHeight),interpolation=cv2.INTER_CUBIC)#Scale up!
                if rad>0:
                    bgr = cv2.blur(bgr,(rad,rad))

                # Apply colormap
                heatmap = bgr
                cmapText = ""
                match Colormap(colormap):
                    case Colormap.JET:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_JET)
                        cmapText = 'Jet'
                    case Colormap.HOT:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_HOT)
                        cmapText = 'Hot'
                    case Colormap.MAGMA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_MAGMA)
                        cmapText = 'Magma'
                    case Colormap.INFERNO:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_INFERNO)
                        cmapText = 'Inferno'
                    case Colormap.PLASMA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PLASMA)
                        cmapText = 'Plasma'
                    case Colormap.BONE:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_BONE)
                        cmapText = 'Bone'
                    case Colormap.SPRING:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_SPRING)
                        cmapText = 'Spring'
                    case Colormap.AUTUMN:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_AUTUMN)
                        cmapText = 'Autumn'
                    case Colormap.VIRIDIS:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_VIRIDIS)
                        cmapText = 'Viridis'
                    case Colormap.PARULA:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PARULA)
                        cmapText = 'Parula'
                    case Colormap.INV_RAINBOW:
                        heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_RAINBOW)
                        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
                        cmapText = 'Inv Rainbow'
                    case _:
                        heatmap = bgr
                        cmapText = 'None'

                # Draw crosshairs
                cv2.line(heatmap,(int(newWidth/2),int(newHeight/2)+20),\
                (int(newWidth/2),int(newHeight/2)-20),(255,255,255),2) #vline
                cv2.line(heatmap,(int(newWidth/2)+20,int(newHeight/2)),\
                (int(newWidth/2)-20,int(newHeight/2)),(255,255,255),2) #hline

                cv2.line(heatmap,(int(newWidth/2),int(newHeight/2)+20),\
                (int(newWidth/2),int(newHeight/2)-20),(0,0,0),1) #vline
                cv2.line(heatmap,(int(newWidth/2)+20,int(newHeight/2)),\
                (int(newWidth/2)-20,int(newHeight/2)),(0,0,0),1) #hline
                
                # Show temp
                cv2.putText(heatmap,str(temp)+' C', (int(newWidth/2)+10, int(newHeight/2)-10),\
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(heatmap,str(temp)+' C', (int(newWidth/2)+10, int(newHeight/2)-10),\
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

                if hud==True:
                    # Display black box for our data
                    cv2.rectangle(heatmap, (0, 0),(160, 120), (0,0,0), -1)
                    
                    # Put text in the box
                    cv2.putText(heatmap,'Avg Temp: '+str(avgtemp)+' C', (10, 14),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Label Threshold: '+str(threshold)+' C', (10, 28),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Colormap: '+cmapText, (10, 42),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Blur: '+str(rad)+' ', (10, 56),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Scaling: '+str(scale)+' ', (10, 70),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Contrast: '+str(alpha)+' ', (10, 84),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    cv2.putText(heatmap,'Snapshot: '+snaptime+' ', (10, 98),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)

                    if recording == False:
                        cv2.putText(heatmap,'Recording: '+elapsed, (10, 112),\
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4,(200, 200, 200), 1, cv2.LINE_AA)
                    if recording == True:
                        cv2.putText(heatmap,'Recording: '+elapsed, (10, 112),\
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4,(40, 40, 255), 1, cv2.LINE_AA)
                
                #Yeah, this looks like we can probably do this next bit more efficiently!
                # Display floating max temp
                if maxtemp > avgtemp+threshold:
                    cv2.circle(heatmap, (mrow*scale, mcol*scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (mrow*scale, mcol*scale), 5, (0,0,255), -1)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*scale)+10, (mcol*scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*scale)+10, (mcol*scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

                # Display floating min temp
                if mintemp < avgtemp-threshold:
                    cv2.circle(heatmap, (lrow*scale, lcol*scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (lrow*scale, lcol*scale), 5, (255,0,0), -1)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*scale)+10, (lcol*scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*scale)+10, (lcol*scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)

                # Display image
                cv2.imshow('Thermal',heatmap)

                if recording == True:
                    elapsed = (time.time() - start)
                    elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed)) 
                    videoOut.write(heatmap)
                
                keyPress = cv2.waitKey(1)
                if keyPress == ord(KEY_INCREASE_BLUR): # Increase blur radius
                    rad += 1
                if keyPress == ord(KEY_DECREASE_BLUR): # Decrease blur radius
                    rad -= 1
                    if rad <= 0:
                        rad = 0

                if keyPress == ord(KEY_INCREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Increase threshold
                    threshold += 1
                if keyPress == ord(KEY_DECREASE_FLOATING_HIGH_LOW_TEMP_LABEL_THRESHOLD): # Decrease threashold
                    threshold -= 1
                    if threshold <= 0:
                        threshold = 0

                if keyPress == ord(KEY_INCREASE_SCALE): # Increase scale
                    scale += 1
                    if scale >=5:
                        scale = 5
                    newWidth = width*scale
                    newHeight = height*scale
                    if dispFullscreen == False:
                        cv2.resizeWindow('Thermal', newWidth,newHeight)
                if keyPress == ord(KEY_DECREASE_SCALE): # Decrease scale
                    scale -= 1
                    if scale <= 1:
                        scale = 1
                    newWidth = width*scale
                    newHeight = height*scale
                    if dispFullscreen == False:
                        cv2.resizeWindow('Thermal', newWidth,newHeight)

                if keyPress == ord(KEY_FULLSCREEN): # Enable fullscreen
                    dispFullscreen = True
                    cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                if keyPress == ord(KEY_WINDOWED): # Disable fullscreen
                    dispFullscreen = False
                    cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_AUTOSIZE,cv2.WINDOW_GUI_NORMAL)
                    cv2.resizeWindow('Thermal', newWidth,newHeight)

                if keyPress == ord(KEY_INCREASE_CONTRAST): # Increase contrast
                    alpha += 0.1
                    alpha = round(alpha,1) #fix round error
                    if alpha >= 3.0:
                        alpha=3.0
                if keyPress == ord(KEY_DECREASE_CONTRAST): # Decrease contrast
                    alpha -= 0.1
                    alpha = round(alpha,1)#fix round error
                    if alpha<=0:
                        alpha = 0.0


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