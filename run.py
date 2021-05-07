import configparser
import cv2
import numpy as np
import time
from matplotlib import pyplot as plt

HORIZONTAL_MAX_DIFF = 20
KEY_ESCAPE = 27
COLOR_ORANGE = (0,128,255)
COLOR_MAGENTA = (255,0,255)
COLOR_GREEN = (0,255,0)
COLOR_RED = (0,0,255)
COLOR_BLUE = (255,0,0)

# Read local file `config.ini`
config = configparser.ConfigParser()      
config.read('config.ini')
URI = config.get('CONFIG','URL')
DIALS_COUNT = int(config.get('CONFIG', 'DIALS_COUNT'))
SAVE_IMAGE = bool(config.get('CONFIG', 'SAVE_IMAGE'))

cap = cv2.VideoCapture(URI)
fig, ax = plt.subplots(figsize=(6, 6))

def filter_circles(circles):
    # convert the (x, y) coordinates and radius of the circles to integers
    circles = np.round(circles[0, :]).astype("int")
    # sort by X-axis
    circles = sorted(circles, key=lambda x: x[0])

    # remove circles with Y-axis deviating too much from the rest
    valid_circles = []
    min_y = None
    for c in circles:
        y = c[1]
        if min_y == None:
            min_y = y
        if y < min_y:
            min_y = y

    for c in circles:
        x = c[0]
        y = c[1]
        r = c[2]
        if abs(y-min_y) < HORIZONTAL_MAX_DIFF:
            valid_circles.append((x, y, r))

    print("Found #%i circles:" % len(valid_circles))
    return valid_circles

def find_needle(image, cx, cy, radius):

    # https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

    size = radius * 0.8
    slices = 40
    factor = 360/slices
    center = tuple([cx, cy])

    needle_pt = None
    # find the longest dark line from the centre
    longest_dark = 0
    value = None

    for i in range(slices):
        # original angle:
        #     360
        # 180      0
        #     90
        angle = i*factor - 90
        # converted angle:
        #     0
        # 360      90
        #     180
        dark_length = 0
        x2 = cx + int(size*np.cos(angle*np.pi/180.0))
        y2 = cy + int(size*np.sin(angle*np.pi/180.0))

        #cv2.line(image, center, (x2, y2), 255, thickness=2)
        points_on_line = np.linspace(center, (x2, y2), radius) # 100 samples on the line
        for pt in points_on_line:
            point = np.int32(pt)
            px = point[0]
            py = point[1]
            b = image[:, :, 0][py, px]
            g = image[:, :, 1][py, px]
            r = image[:, :, 2][py, px]
            # Compute grayscale with naive equation
            gray = (b.astype(int) + g.astype(int) + r.astype(int))/3
            # debug: show points on the line
            #cv2.circle(image, tuple(point), 1, (255,i*10,0), -1)
            # if sufficiently dark
            if gray < 100:
                #cv2.circle(image, tuple(point), 1, (255, gray, 0), -1)
                dark_length += 1
            else:
                continue
        
        if dark_length > longest_dark:
            longest_dark = dark_length
            needle_pt = tuple(point)
            value = 10*i/slices # scale to 0-10

    return value, needle_pt

def process_values(values):
    reading = ''
    for i, (v) in enumerate(values):
        whole = int(np.floor(v))
        if i == len(values) - 1:
            reading = reading + str(whole)
            break
        decimals = v - whole
        if decimals < 0.5 and values[i+1] > 5:
            # decimal value low but the next value is high, so need to adjust the reading by -1
            whole = whole-1
        reading = reading + str(whole)

    return reading

def find_circles(capture):
    ret, frame = capture.read()

    if SAVE_IMAGE:
        filename = time.strftime("data/sample-%Y%m%d-%H%M.jpg")
        cv2.imwrite(filename, frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    output = frame.copy()

    # TODO: move values to config, or try to figure them out (increase values incrementally)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.1, minDist=60, minRadius=50, maxRadius=100)

    # TODO: move to config
    readout_conventions = ["CW", "CCW", "CW", "CCW", "CW"]

    if circles is None:
        return

    # find circles which are roughly on the same level
    circles = filter_circles(circles)

    # ignore results if an exact number of dials wasn't found
    if len(circles) != DIALS_COUNT:
        return

    values = []

    # loop over the (x, y) coordinates and radius of the circles
    minx = 0
    miny = 0
    radius = 0
    for i, ((x, y, r), convention) in enumerate(zip(circles, readout_conventions)):
        value, tip = find_needle(output, x, y, r)
        actual_value = read_value(value, convention)
        values.append(actual_value)
        print("#%i: (%i, %i) radius: %i - value: %f" % (i, x, y, r, actual_value))

        # draw needle and value
        cv2.line(output, (x, y), tip, COLOR_MAGENTA, thickness=2)
        cv2.putText(output, str(actual_value), (x - 20, y + r + 20), cv2.FONT_HERSHEY_PLAIN, 1, 255)

        # draw the circle in the output image, then draw a rectangle
        # corresponding to the center of the circle
        cv2.circle(output, (x, y), r, COLOR_GREEN, 4)
        cv2.rectangle(output, (x - 2, y - 2), (x + 2, y + 2), COLOR_ORANGE, -1)

        if i == 0:
            minx = x
            miny = y
            radius = r

    # TODO: compare to the previous reading? it should never be less than the previous one
    reading = process_values(values)
    print("Final reading: %s" % reading)
    cv2.putText(output, reading, (minx, miny + radius + 100), cv2.FONT_HERSHEY_PLAIN, 2, COLOR_BLUE)

    if SAVE_IMAGE:
        filename = time.strftime("data/sample-%Y%m%d-%H%M-out.jpg")
        cv2.imwrite(filename, output)

    cv2.imshow("output", output)

def read_value(value, convention):
    if convention == "CCW":
        result = 10. - value
    else:
        result = value
    if result == 10:
        result = 0
    return result

while True:

    find_circles(cap)
    time.sleep(2)

    if cv2.waitKey(1) & 0xFF == KEY_ESCAPE:
        break

cap.release()
cv2.destroyAllWindows()
