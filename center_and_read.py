# Center and Read
# Author: Ramazan Vapurcu
# github.com/wmramazan

import numpy as np
import argparse
import cv2
import time

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--video", help = "path to the optional video file", default = "")
parser.add_argument("-f", "--freq", help = "frequency of reading frame", type = int, default = 20)
parser.add_argument("-p", "--center", help = "threshold for position of center", type = int, default = 30)
parser.add_argument("-r", "--ratio", help = "ratio of area for scaling matrix", type = int, default = 8)
parser.add_argument("-s", "--slope", help = "threshold for slope of color matrix", type = int, default = 0)
parser.add_argument("-a", "--area", help = "minimum contour area", type = int, default = 300)
args = parser.parse_args()

def detect_x_position(value):
    return int((value + args.slope - min_x) / range_x)

def detect_y_position(value):
    return int((value + args.slope - min_y) / range_y)

color_names = ('red', 'blue', 'yellow')
matrix = np.zeros((4, 4), dtype = int)

'''
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

frame_counter = 0

if args.video:
    camera = cv2.VideoCapture(args.video)
else:
    camera = cv2.VideoCapture(0)

camera_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
camera_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)

print "Frame: ", camera_width, "x", camera_height

frame_center = (camera_width / 2, camera_height / 2)
frame_area = camera_width * camera_height

while True:
    (grabbed, frame) = camera.read()

    if args.video and not grabbed:
        break

    # frame = imutils.resize(frame, width = 600)
    # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

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
        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (255, 255, 255))

        # TODO: If Markut's mode is LOITER, do not check position!!!

        if frame_counter % args.freq is 0:
            print "----------------"

            current_position = ((min_x + max_x) / 2, (min_y + max_y) / 2)

            difference = frame_center[0] - current_position[0]

            print "Point Counter: ", point_counter
            print "Current Position: ", current_position[0]

            if difference > 0:
                if difference < args.center:
                    print "Centered in x axis"
                else:
                    print "Right"
            else:
                difference *= -1
                if difference < args.center:
                    print "Centered in x axis"
                else:
                    print "Left"

            difference = frame_center[1] - current_position[1]

            if difference > 0:
                if difference < args.center:
                    print "Centered in y axis"
                else:
                    print "Down"
            else:
                difference *= -1
                if difference < args.center:
                    print "Centered in y axis"
                else:
                    print "Up"

            area = (max_x - min_x) * (max_y - min_y)
            print "Area: ", area

            try:
                ratio = int(frame_area / area)
                print "Ratio: ", ratio
            except ZeroDivisionError:
                ratio = frame_area

            if ratio < args.ratio - 5:
                print "Throttle Up"
            elif ratio > args.ratio + 5:
                print "Throttle Down"
            else:
                print "Good Scale"

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



                except IndexError:
                    print "Invalid Matrix"

    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF
    frame_counter += 1

    time.sleep(0.05)

    if key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()