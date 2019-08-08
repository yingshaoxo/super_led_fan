import gc
import time
import image
import sensor
import binascii
from pyb import UART
from pyb import Pin
from utime import sleep_ms


DEBUG = 10


sensor.reset()
# sensor.set_pixformat(sensor.GRAYSCALE)  # RGB565
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.B128X128)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)  # must be turned off for color tracking
sensor.set_auto_whitebal(False)  # must be turned off for color tracking
clock = time.clock()

####################################
####################################
####################################

# set paramaters for picture taking

####################################
####################################
####################################
width = 90
height = 120
sub_image_number_in_one_axis = 16


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
    global detected_point_list

    detected_point_list = []
    for yi in range(sub_image_number_in_one_axis):
        for xi in range(sub_image_number_in_one_axis):
            crop_paramater = sub_image_crop_paramater_list[yi][xi]
            sub_image = an_image.copy(roi=crop_paramater)
            blobs = sub_image.find_blobs([(69, 100, -128, 127, -128, 127)])
            # blobs = sub_image.find_blobs([(185, 255)])  # 156,255
            true_or_false = 11
            for blob in blobs:
                if blob.pixels() > 5:
                    true_or_false = 10
            detected_point_list.append(true_or_false)


sub_image_center_point_list = get_sub_image_center_points()

detected_point_list = []


def print_out_detected_points(an_image):
    global detected_point_list

    list_for_y_axis = []
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        for xi in range(sub_image_number_in_one_axis):
            point = sub_image_center_point_list[yi][xi]
            if (detected_point_list[yi * 16 + xi] == 11):
                an_image.draw_circle(
                    point[0], point[1], 3, color=(255, 0, 0), fill=True)  # center_x, center_y
            else:
                an_image.draw_circle(
                    point[0], point[1], 3, color=(0, 255, 0), fill=True)  # center_x, center_y
        list_for_y_axis.append(list_for_x_axis)

    return an_image


####################################
####################################
####################################

# configure serial communication

####################################
####################################
####################################

uart = UART(3, 115200, timeout=20)  # P4/P5 = TX/RX


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

####################################
####################################
####################################

# set keyboard

# from P0-P3 and from P6-P9

####################################
####################################
####################################


class Keypad():
    pin0 = Pin('P0', Pin.IN, Pin.PULL_DOWN)
    pin1 = Pin('P1', Pin.IN, Pin.PULL_DOWN)
    pin2 = Pin('P2', Pin.IN, Pin.PULL_DOWN)
    pin3 = Pin('P3', Pin.IN, Pin.PULL_DOWN)

    pin4 = Pin('P6', Pin.OUT_PP)
    pin5 = Pin('P7', Pin.OUT_PP)
    pin6 = Pin('P8', Pin.OUT_PP)
    pin7 = Pin('P9', Pin.OUT_PP)

    def set_column1_to_0(self):
        self.pin4.value(0)

    def set_column1_to_1(self):
        self.pin4.value(1)

    def set_column2_to_0(self):
        self.pin5.value(0)

    def set_column2_to_1(self):
        self.pin5.value(1)

    def set_column3_to_0(self):
        self.pin6.value(0)

    def set_column3_to_1(self):
        self.pin6.value(1)

    def set_column4_to_0(self):
        self.pin7.value(0)

    def set_column4_to_1(self):
        self.pin7.value(1)

    def input_of_row1(self):
        return self.pin0.value()

    def input_of_row2(self):
        return self.pin1.value()

    def input_of_row3(self):
        return self.pin2.value()

    def input_of_row4(self):
        return self.pin3.value()

    def millisecond_of_delay(self, t):
        sleep_ms(t)

    def catch_keypad_input(self):
        if (not self.input_of_row1()):
            self.set_column1_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(400)
                if (self.input_of_row1()):
                    # self.handle_keypad_number(1)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(400)
                if (self.input_of_row1()):
                    self.handle_keypad_number(0)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(400)
                if (self.input_of_row1()):
                    self.handle_keypad_number(10)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(400)
                if (self.input_of_row1()):
                    self.handle_keypad_number(-4)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row2()):
            self.set_column1_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(400)
                if (self.input_of_row2()):
                    self.handle_keypad_number(7)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(400)
                if (self.input_of_row2()):
                    self.handle_keypad_number(8)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(400)
                if (self.input_of_row2()):
                    self.handle_keypad_number(9)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(400)
                if (self.input_of_row2()):
                    self.handle_keypad_number(-3)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row3()):
            self.set_column1_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(400)
                if (self.input_of_row3()):
                    self.handle_keypad_number(4)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(400)
                if (self.input_of_row3()):
                    self.handle_keypad_number(5)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(400)
                if (self.input_of_row3()):
                    self.handle_keypad_number(6)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(400)
                if (self.input_of_row3()):
                    self.handle_keypad_number(-2)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row4()):
            self.set_column1_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(400)
                if (self.input_of_row4()):
                    self.handle_keypad_number(1)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(400)
                if (self.input_of_row4()):
                    self.handle_keypad_number(2)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(400)
                if (self.input_of_row4()):
                    self.handle_keypad_number(3)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(400)
                if (self.input_of_row4()):
                    self.handle_keypad_number(-1)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

    def handle_keypad_number(self, number):
        print(number)


keypad = Keypad()

while(True):
    clock.tick()

    keypad.catch_keypad_input()

    if DEBUG == 1:
        img = sensor.snapshot().lens_corr(1.8)
        detect_all_sub_image(img)
        img = print_out_detected_points(img)

        send_signal(8, data=detected_point_list)

    #print("FPS %f" % clock.fps())
    gc.mem_free()
