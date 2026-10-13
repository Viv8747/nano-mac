import serial
import serial.tools.list_ports
import numpy as np
import cv2
import tkinter as tk
from tkinter import messagebox
import time
import sys

DELAY_SECONDS = 0.75 
BRIGHTNESS_BOOST = 2.0  

def find_nanovna_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # NanoVNA uses STMicroelectronics Virtual COM port ID: VID=0483, PID=5740
        if port.vid == 0x0483 and port.pid == 0x5740:
            return port.device
        # Fallback for generic Windows labeling
        if "USB Serial Device" in port.description or "STMicroelectronics" in port.description or "ChibiOS" in port.description:
            return port.device
    return None

# --- Setup and Auto-Detect ---
root = tk.Tk()
root.withdraw() # Hide the main window to just use the popup/screen check

vna_port = find_nanovna_port()
if not vna_port:
    messagebox.showerror("Connection Error", "NanoVNA not found!\n\nPlease ensure it is plugged in, turned on, and that no other software is using the COM port.")
    sys.exit()

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.destroy() 

window_name = 'NanoVNA Projector Feed'
scale_factor = 2
vna_width, vna_height = 480 * scale_factor, 320 * scale_factor

start_x = int((screen_width - vna_width) / 2)
start_y = int((screen_height - vna_height) / 2)

cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# Connect to the auto-detected port
vna = serial.Serial(vna_port, timeout=3) 
print(f"NanoVNA found on {vna_port}. Starting feed... Press 'q' to quit.")

while True:
    vna.reset_input_buffer()
    vna.reset_output_buffer()
    
    vna.write(b'capture\r')
    vna.read_until(b'\n')
    image_data = vna.read(307200)
    vna.read_until(b'>')
    
    if len(image_data) == 307200:
        img_16 = np.frombuffer(image_data, dtype=np.uint16).reshape((320, 480))
        
        r = ((img_16 >> 11) & 0x1F) << 3
        g = ((img_16 >> 5) & 0x3F) << 2
        b = (img_16 & 0x1F) << 3
        img_bgr = np.dstack((b, g, r)).astype(np.uint8)
        
        img_boosted = cv2.convertScaleAbs(img_bgr, alpha=BRIGHTNESS_BOOST, beta=0)
        img_scaled = cv2.resize(img_boosted, (vna_width, vna_height), interpolation=cv2.INTER_NEAREST)
        
        canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
        canvas[start_y:start_y+vna_height, start_x:start_x+vna_width] = img_scaled
        
        cv2.imshow(window_name, canvas)
        
    quit_pressed = False
    start_time = time.time()
    while time.time() - start_time < DELAY_SECONDS:
        if cv2.waitKey(10) & 0xFF == ord('q'):
            quit_pressed = True
            break
            
    if quit_pressed:
        break

vna.close()
cv2.destroyAllWindows()