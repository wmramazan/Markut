# Markut - Task 1
# Author: Ramazan Vapurcu
# github.com/wmramazan

import socket
import exceptions
import time
import dronekit
import argparse
import math
import serial
import cv2
import numpy as np

TARGET_LATITUDE = -35.361354
TARGET_LONGITUDE = 149.165218

parser = argparse.ArgumentParser(description = "Fly Stay Alive")
parser.add_argument("--connect", help = "connection string of Markut", default = "/dev/ttyUSB0")
parser.add_argument("--altitude", help = "target altitude", type = int, default = 10)
parser.add_argument("--speed", help = "air speed", type = int, default = 3)
parser.add_argument("--freq", help = "frequency of reading frame", type = int, default = 20)
parser.add_argument("--slope", help = "threshold for slope of color matrix", type = int, default = 0)
parser.add_argument("--area", help = "minimum contour area", type = int, default = 0)
args = parser.parse_args()

print "-> Markut - Fly Stay Alive"
print "-> Waiting your command: "

def get_distance_metres(aLocation1, aLocation2):
    dlat = aLocation2.lat - aLocation1.lat
    dlong = aLocation2.lon - aLocation1.lon
    return math.sqrt((dlat * dlat) + (dlong * dlong)) * 1.113195e5

try:
    markut = dronekit.connect(args.connect, wait_ready=True, heartbeat_timeout=15)

except socket.error:
    print 'No server exists!'

except exceptions.OSError as e:
    print 'No serial exists!'

except dronekit.APIException:
    print 'Timeout!'

except:
    print 'Some other error!'

# Pre-arm checks
while not markut.is_armable:
    print "Waiting for Markut to initialize.."
    time.sleep(1)

print "Arming Motors"
markut.mode = dronekit.VehicleMode("GUIDED")
markut.armed = True

while not markut.mode.name == "GUIDED" and not markut.armed:
    print "Getting ready to take off.."
    time.sleep(1)

print "Taking off!"
markut.simple_takeoff(args.altitude)

while True:
    markut_current_altitude = markut.location.global_relative_frame.alt
    print " Altitude: ", markut_current_altitude
    if markut_current_altitude >= args.altitude * 0.95:
        print "Reached target altitude."
        break
    time.sleep(1)

markut.airspeed = args.speed

target_location = dronekit.LocationGlobal(TARGET_LATITUDE, TARGET_LONGITUDE, args.altitude)
target_distance = get_distance_metres(markut.location.global_relative_frame, target_location)
markut.simple_goto(target_location)

while markut.mode.name == "GUIDED":
    remaining_distance = get_distance_metres(markut.location.global_relative_frame, target_location)
    print "Distance to target: ", remaining_distance
    if remaining_distance <= target_distance * 0.01:
        print "Reached target"
        break;
    time.sleep(2)

markut.mode = dronekit.VehicleMode("LOITER")
while not markut.mode.name == "LOITER":
    print "GUIDED -> LOITER"
    time.sleep(1)

sd = serial.Serial('/dev/ttyS0', 9600, timeout=1)
if not sd.isOpen():
    sd.open()

time.sleep(1)

def detect_x_position(value):
    return int((value + args.slope - min_x) / range_x)

def detect_y_position(value):
    return int((value + args.slope - min_y) / range_y)

matrix = np.zeros((4, 4), dtype = int)

# Boundaries (HSV)
boundaries = [
    ([168, 150, 150], [171, 200, 200]), # red
    ([100, 10, 150], [115, 140, 200]), # blue
    ([22, 110, 180], [26, 220, 240]) # yellow
]

'''
# Test Boundaries (BGR)
boundaries = [
    ([0, 0, 100], [50, 56, 255]), # red
    ([50, 0, 0], [100, 255, 10]), # blue
    ([0, 120, 0], [70, 190, 255]) # yellow
]
'''

frame_counter = 0

camera = cv2.VideoCapture(0)

camera_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
camera_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)

print "Frame: ", camera_width, "x", camera_height

frame_center = (camera_width / 2, camera_height / 2)
frame_area = camera_width * camera_height

time.sleep(10)

while frame_counter < 4:
    (grabbed, frame) = camera.read()

    # frame = imutils.resize(frame, width = 600)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    point_counter = 0
    color_counts = [0] * 3
    center_x = [None] * 16
    center_y = [None] * 16

    for index, (lower, upper) in enumerate(boundaries):
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)

        mask = cv2.inRange(frame, lower, upper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]

        for (cnt) in contours:

            if cv2.contourArea(cnt) < args.area:
                continue

            color_counts[index] += 1
            M = cv2.moments(cnt)
            try:
                center_x[point_counter] = int(M["m10"] / M["m00"])
                center_y[point_counter] = int(M["m01"] / M["m00"])
                point_counter += 1
            except ZeroDivisionError:
                pass
            except IndexError:
                pass

    if point_counter > 0:
        min_x = min(x for x in center_x if x is not None)
        max_x = max(center_x)
        min_y = min(y for y in center_y if y is not None)
        max_y = max(center_y)
        #cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (255, 255, 255))

        if frame_counter % args.freq is 0:

            if point_counter is 16:
                range_x = int((max_x - min_x) / 3)
                range_y = int((max_y - min_y) / 3)

                index = 0
                end = color_counts[0]

                try:
                    while index < end:
                        # print "index: ", '%2d' % (index), " ", detect_y_position(center_y[index]), detect_x_position(center_x[index])
                        matrix[detect_y_position(center_y[index])][detect_x_position(center_x[index])] = 0
                        index += 1

                    end += color_counts[1]
                    while index < end:
                        # print "index: ", '%2d' % (index), " ", detect_y_position(center_y[index]), detect_x_position(center_x[index])
                        matrix[detect_y_position(center_y[index])][detect_x_position(center_x[index])] = 1
                        index += 1

                    end += color_counts[2]
                    while index < end:
                        # print "index: ", '%2d' % (index), " ", detect_y_position(center_y[index]), detect_x_position(center_x[index])
                        matrix[detect_y_position(center_y[index])][detect_x_position(center_x[index])] = 2
                        index += 1

                    print matrix

                    matrix_string = ""
                    i = 0
                    while i < 4:
                        j = 0
                        while j < 4:
                            matrix_string += str(matrix[i][j])
                            j += 1
                        i += 1

                    print matrix_string
                    sd.write(matrix_string)

                except IndexError:
                    print "Invalid Matrix"
            else:
                print "Couldn't find the color matrix"
                print "Point Counter: ", point_counter

    time.sleep(10)
    frame_counter += 1

camera.release()

markut.mode = dronekit.VehicleMode("RTL")
while not markut.mode.name == "RTL":
    print "Returning to home"
    time.sleep(1)

markut.close()