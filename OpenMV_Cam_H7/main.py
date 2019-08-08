from pyb import UART
import binascii
import sensor
import image
import time
import gc

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.B128X128)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)  # must be turned off for color tracking
sensor.set_auto_whitebal(False)  # must be turned off for color tracking
clock = time.clock()

# set paramaters for picture taking
width = 90
height = 120
sub_image_number_in_one_axis = 16

# configure serial communication
uart = UART(3, 115200, timeout=20)  # P4/P5 = TX/RX


def get_sub_image_paramaters():
    list_for_y_axis = []
    y_value = 0
    y_interval = height//sub_image_number_in_one_axis
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        x_value = 0
        x_interval = width//sub_image_number_in_one_axis
        for xi in range(sub_image_number_in_one_axis):
            region_of_interest = (x_value, y_value, x_interval, y_interval)
            x_value += x_interval
            list_for_x_axis.append(region_of_interest)
        y_value += y_interval
        list_for_y_axis.append(list_for_x_axis)

    return list_for_y_axis


def get_sub_image_center_points():
    list_for_y_axis = []
    y_value = 0
    y_interval = height//sub_image_number_in_one_axis
    half_y_interval = y_interval//2
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        x_value = 0
        x_interval = width//sub_image_number_in_one_axis
        half_x_interval = x_interval//2
        for xi in range(sub_image_number_in_one_axis):
            region_of_interest = (x_value + half_x_interval,
                                  y_value + half_y_interval)
            x_value += x_interval
            list_for_x_axis.append(region_of_interest)
        y_value += y_interval
        list_for_y_axis.append(list_for_x_axis)

    return list_for_y_axis


sub_image_crop_paramater_list = get_sub_image_paramaters()


def detect_all_sub_image(an_image):
    one_dimensional_list = []
    list_for_y_axis = []
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        for xi in range(sub_image_number_in_one_axis):
            crop_paramater = sub_image_crop_paramater_list[yi][xi]
            sub_image = an_image.copy(roi=crop_paramater)
            blobs = sub_image.find_blobs([(69, 100, -128, 127, -128, 127)])
            true_or_false = 11
            for blob in blobs:
                if blob.pixels() > 1:
                    true_or_false = 10
            list_for_x_axis.append(true_or_false)
            one_dimensional_list.append(true_or_false)
        list_for_y_axis.append(list_for_x_axis)
    return list_for_y_axis, one_dimensional_list


sub_image_center_point_list = get_sub_image_center_points()


def print_out_detected_points(an_image, detected_point_list):
    list_for_y_axis = []
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        for xi in range(sub_image_number_in_one_axis):
            point = sub_image_center_point_list[yi][xi]
            if (detected_point_list[yi][xi] == 11):
                an_image.draw_circle(
                    point[0], point[1], 3, color=(255, 0, 0), fill=True)  # center_x, center_y
            else:
                an_image.draw_circle(
                    point[0], point[1], 3, color=(0, 255, 0), fill=True)  # center_x, center_y
        list_for_y_axis.append(list_for_x_axis)
    return an_image


def int_to_byte(integer):
    hex_string = '{:02x}'.format(integer)
    a_byte = binascii.unhexlify(hex_string)
    return a_byte


def byte_to_int(a_byte):
    if (a_byte == None):
        return 0

    hex_string = binascii.hexlify(a_byte)
    integer = int(hex_string, 16)
    return integer


# P4/P5 = TX/RX
def send_int(integer):
    uart.write(int_to_byte(integer))


def receive_int():
    a_byte = uart.read(1)
    return byte_to_int(a_byte)

"""
0: idle
1-7: different tasks
8: sned data
9: succesefully receive signal

10: black point in picture
11: white point in picture

Every signal start by `0`, then `signal`, then follow by 256 data.
"""

def send_idle_state():
    send_int(0)

receive_success_reply = 0
def send_signal(number, data=None):
    global receive_success_reply
    if receive_success_reply == 0:
        send_idle_state()
        send_int(number)
        for index in range(256):
            if (data != None):
                send_int(data[index])
                print(data[index])
            else:
                send_idle_state()
        return True
    return False

def continue_sending():
    global receive_success_reply
    receive_success_reply = 0

def stop_sending():
    global receive_success_reply
    receive_success_reply = 1

def receive_signal():
    number = receive_int()
    if number == 9:
        stop_sending()


while(True):
    clock.tick()
    img = sensor.snapshot().lens_corr(1.8)

    detected_point_list, data = detect_all_sub_image(img)
    img = print_out_detected_points(img, detected_point_list)

    send_signal(8, data=data)

    print("FPS %f" % clock.fps())
    gc.mem_free()
