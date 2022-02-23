#!/usr/bin/env python3

"""
Display HAT Mini Weather Display

Don't forget to enter your location below.

Run with:
  python3 weather.py

  Pushbuttons
  ===========
  A: backlight up.
  B: backlight down.
  X: °C or °F. 
  Y: wind direction in degrees or cardinals. 

Runs on Raspberry Pi Buster with pygame 2.1.0, SDL 2.0.9 & Python 3.7.3

Not working at all? Try upgrading pygame:
  sudo python3 -m pip install pygame --upgrade

libsdl2_ttf-2.0.so.0 error? Try: 
  sudo apt-get install python3-sdl2

CPV, Elektor, 22/02/2022
"""

import os
import sys
import signal
import pygame
import time
import math
import httplib2
import json
from urllib.request import urlopen
import socket

from displayhatmini import DisplayHATMini

# Enter your location here, then try it in a browser before using it for real.
location = "Pluneret"
lookup_url = "https://free-api.heweather.net/s6/weather/now?location=" + location + "&key=2d63e6d9a95c4e8f8d3f65d0b5bcdf7f&lang=e"

my_font = 'piboto'
my_font_size = 50
temperature_units = "C"
wind_degrees = False

black = (0,0,0)
white = (255,255,255)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
darkred = (175,0,0)
darkgreen = (0,175,0)
darkblue = (0,0,175)

if pygame.vernum < (2, 0, 0):
    print("Need PyGame >= 2.0.0:\n    python3 -m pip install pygame --upgrade")
    sys.exit(1)

# Plumbing to convert Display HAT Mini button presses into pygame events
def button_callback(pin):
    global brightness
    global temperature_units
    global wind_degrees
    global deciseconds

    # Only handle presses
    if not display_hat.read_button(pin):
        return

    if pin == display_hat.BUTTON_A:
        brightness += 0.1
        brightness = min(1, brightness)

    if pin == display_hat.BUTTON_B:
        brightness -= 0.1
        brightness = max(0, brightness)

    if pin == display_hat.BUTTON_X:
        if temperature_units=="C": temperature_units = "F" 
        else: temperature_units = "C"
        deciseconds = 999 # Force display update.

    if pin == display_hat.BUTTON_Y:
        wind_degrees = not wind_degrees
        deciseconds = 999 # Force display update.

def print_value(x,y,msg,color,align="left"):
    w = font.size(msg)[0]
    h = font.size(msg)[1]
    img = font.render(msg,True,color)
    if align=="right": x = 320 - w - x
    screen.blit(img,(x,y))

def weather_show_icon(icon):
    # Load the icon that corresponds to the weather.
    icon_file = "icons/" + icon + ".bmp"
    icon = pygame.image.load(icon_file)
    # Put it on the screen.
    screen.fill(white) # white background
    screen.blit(icon,(0,0)) # Our icons are 240x240 pixels.

def weather_show(weather):
    print(weather)
    # Extract all the available data, even if we don't use it all.
    cloud = weather["cloud"]
    cond_code = weather["cond_code"]
    cond_txt = weather["cond_txt"]
    fl = weather["fl"] # Feel? Celsius?
    humidity = weather["hum"] # Percentage
    precipitation = weather["pcpn"]
    pressure = weather["pres"] # mbar
    temperature = weather["tmp"] # Celsius
    visibility = weather["vis"]
    wind_dir_degree = weather["wind_deg"] # Direction in degrees
    wind_dir = weather["wind_dir"] # Direction as 'N', 'SE', etc.
    wind_force = weather["wind_sc"] # Force?
    wind_speed = weather["wind_spd"]
    # Show weather icon.
    weather_show_icon(cond_code)
    # Add some text to it.
    x = 7
    y = 0
    t = int(temperature)
    tf = round(1.8*t + 32) # Convert to Fahrenheit in case we need it.
    if t<-20: t = -20
    if t>40: t = 40
    t = round(((t+20)/60)*255)
    if temperature_units=="F": temperature = str(tf)
    temperature += "°" + temperature_units
    print_value(x,y,temperature,(t,0,255-t),"right")
    y += 56
    print_value(x,y,pressure,darkgreen,"right")
    y += 56
    print_value(x,y,humidity+"%",darkblue,"right")
    y += 56
    if wind_degrees==True: wind = wind_dir_degree + "°"
    else: wind = wind_dir
    wind += " " + wind_force
    print_value(x,y,wind,darkred,"right")

def weather_get(url):
    print(url)
    try:
        # Request the weather information.
        soup = urlopen(url)
        markup = soup.read()
        soup.close()
    except:
        # Couldn't fetch data, return error.
        print("weather_get: fetch error")
        display_hat.set_led(0.2, 0.0, 0.0) # RGB LED
        return "error"
        
    # Access the part of the JSON object that we care about.
    feed_json = json.loads(markup)
    if feed_json["HeWeather6"][0]["status"] == "ok":
        # Weather info is OK, so display it.
        weather_show(feed_json["HeWeather6"][0]["now"])
        display_hat.set_led(0.0, 0.0, 0.0) # RGB LED off. The LED is annoying, only use it when it is really needed.
    else:
        # Do something to show that weather info is invalid.
        screen.fill(red)
        display_hat.set_led(0.1, 0.1, 0.0) # RGB LED
    return "ok"

def _exit(sig, frame):
    global running
    running = False
    print("\nBye!\n")

def update_display():
    display_hat.st7789.set_window()
    # Grab the pygame screen as a bytes object
    pixelbytes = pygame.transform.rotate(screen, 180).convert(16, 0).get_buffer()
    # Lazy (slow) byteswap:
    pixelbytes = bytearray(pixelbytes)
    pixelbytes[0::2], pixelbytes[1::2] = pixelbytes[1::2], pixelbytes[0::2]
    # Bypass the ST7789 PIL image RGB888->RGB565 conversion
    for i in range(0, len(pixelbytes), 4096):
        display_hat.st7789.data(pixelbytes[i:i + 4096])



print("Display HAT Mini Weather Demo")

brightness = 1.0
display_hat = DisplayHATMini(buffer=None, backlight_pwm=True)
display_hat.on_button_pressed(button_callback) # Set button handler
display_hat.set_led(0.0, 0.0, 0.0) # RGB LED

os.putenv('SDL_VIDEODRIVER', 'dummy')
pygame.init() # cpv - required for fonts (and probably other stuff as well)
#pygame.display.init()  # Need to init for .convert() to work
screen = pygame.Surface((display_hat.WIDTH, display_hat.HEIGHT))

font = pygame.font.SysFont(my_font,my_font_size,bold=True)

weather_show_icon("1012")
deciseconds = 999 # Ensure display update the first time.

running = True
while running:
    display_hat.set_backlight(brightness)
    update_display()
    
    time.sleep(0.1)
    deciseconds += 1
    if deciseconds>=100:
       # Run every 10 or so seconds.
       weather_get(lookup_url) # Update weather forecast.
       deciseconds = 0

# No matter how we quit, it always ends with a segmentation fault?
pygame.display.quit()
pygame.quit()
#sys.exit(0)
quit()
