import gc
import time
import image
import sensor
import binascii
from pyb import UART
from pyb import Pin
from pyb import LED
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
led = LED(3)


####################################
####################################
####################################

# set paramaters for picture taking

####################################
####################################
####################################


"""
increase the accuracy:

1. auto change paramater: by putting a black cycle at the right-bottom corner, you change the paramater automatically to get the preset pixels of that black cycle
2. get multiple picture, then add or merge them together
"""
width = 90
height = 120
sub_image_number_in_one_axis = 16
black_color_representation = 9
white_color_representation = 10


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
sub_image_center_point_list = get_sub_image_center_points()
detected_point_list = []


def detect_all_sub_image(an_image):
    global sub_image_number_in_one_axis
    global sub_image_crop_paramater_list
    global detected_point_list

    detected_point_list = []
    for yi in range(sub_image_number_in_one_axis):
        for xi in range(sub_image_number_in_one_axis):
            crop_paramater = sub_image_crop_paramater_list[yi][xi]
            sub_image = an_image.copy(roi=crop_paramater)
            blobs = sub_image.find_blobs([(69, 100, -128, 127, -128, 127)])
            # blobs = sub_image.find_blobs([(185, 255)])  # 156,255
            true_or_false = white_color_representation
            for blob in blobs:
                if blob.pixels() > 5:
                    true_or_false = black_color_representation
            detected_point_list.append(true_or_false)


def print_out_detected_points(an_image):
    global sub_image_number_in_one_axis
    global sub_image_center_point_list
    global detected_point_list

    list_for_y_axis = []
    for yi in range(sub_image_number_in_one_axis):
        list_for_x_axis = []
        for xi in range(sub_image_number_in_one_axis):
            point = sub_image_center_point_list[yi][xi]
            if (detected_point_list[yi * 16 + xi] == black_color_representation):
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
    1. show two horizontal line at specific position. (each line take a row?)
    2. two lines move between center and top or bottom
    3. show two 16x16 picture, and the middle of the two picture have to be 4x4
    4. show two 16x16 picture, picture getting wider or narrower. (the totall change > than 2 point)

    5. record 3 pictures in 5 minites, and replay it with LCD
    6. send the 3 pictures to LED fans, one by one display at 120 degress of LED fans. the distance between each picture is 3x3 points
    7. change the LED color of task 6. (from red to green, then to orange) (from left to right, from right to left, from top to bottom, from bottom to top, from center to boundary)

8: send picture data
    9: white point in picture
    10: black point in picture
    > the last element of 257 array was used for point out the picture index, for example, 1,2,3

11: send keypad value

Every signal start by `0`, then `signal`, then follow by 257 data.
"""


def send_idle_state():
    send_int(0)


def send_signal(task_number, data=None, picture_index=1):
    send_idle_state()  # back_to_normal
    send_int(task_number)
    if (data != None):
        data_length = len(data)
    for index in range(256): # send 1-256 elements
        if ((data != None) and (index < data_length)):
            send_int(data[index])
            #print(data[index])
        else:
            send_idle_state()
    send_int(picture_index) # send 257


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

    pin4 = Pin('P6', Pin.OUT_PP, Pin.PULL_DOWN)
    pin5 = Pin('P7', Pin.OUT_PP, Pin.PULL_DOWN)
    pin6 = Pin('P8', Pin.OUT_PP, Pin.PULL_DOWN)
    pin7 = Pin('P9', Pin.OUT_PP, Pin.PULL_DOWN)

    state = 0

    task_number = 0
    input_start = 0
    input_string = ""

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
                self.millisecond_of_delay(300)
                if (self.input_of_row1()):
                    # self.handle_keypad_number(1)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(300)
                if (self.input_of_row1()):
                    self.handle_keypad_number(0)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(300)
                if (self.input_of_row1()):
                    self.handle_keypad_number(10)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row1()):
                self.millisecond_of_delay(300)
                if (self.input_of_row1()):
                    self.handle_keypad_number(14)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row2()):
            self.set_column1_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(300)
                if (self.input_of_row2()):
                    self.handle_keypad_number(7)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(300)
                if (self.input_of_row2()):
                    self.handle_keypad_number(8)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(300)
                if (self.input_of_row2()):
                    self.handle_keypad_number(9)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row2()):
                self.millisecond_of_delay(300)
                if (self.input_of_row2()):
                    self.handle_keypad_number(13)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row3()):
            self.set_column1_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(300)
                if (self.input_of_row3()):
                    self.handle_keypad_number(4)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(300)
                if (self.input_of_row3()):
                    self.handle_keypad_number(5)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(300)
                if (self.input_of_row3()):
                    self.handle_keypad_number(6)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row3()):
                self.millisecond_of_delay(300)
                if (self.input_of_row3()):
                    self.handle_keypad_number(12)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

        elif (not self.input_of_row4()):
            self.set_column1_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(300)
                if (self.input_of_row4()):
                    self.handle_keypad_number(1)
                    self.set_column1_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column1_to_0()

            self.set_column2_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(300)
                if (self.input_of_row4()):
                    self.handle_keypad_number(2)
                    self.set_column2_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column2_to_0()

            self.set_column3_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(300)
                if (self.input_of_row4()):
                    self.handle_keypad_number(3)
                    self.set_column3_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column3_to_0()

            self.set_column4_to_1()
            if (self.input_of_row4()):
                self.millisecond_of_delay(300)
                if (self.input_of_row4()):
                    self.handle_keypad_number(11)
                    self.set_column4_to_0()
                    return 0  # must return, otherwise, a weird thing will happen
            self.set_column4_to_0()

    def handle_keypad_number(self, number):
        """
        1	2	3	Return(or back)
        4	5	6	Menu
        7	8	9	Cancel
            0	.	Enter

        .: 10
        Return: 11
        Menu: 12
        Cancel: 13
        Enter: 14
        """
        led.on()

        print(number)

        #if (self.input_start == 0):
        #    if ((number >= 0) and (number < 10)):
        #        self.input_string += str(number)
        #        self.input_start = 1
        #elif (self.input_start == 1):
        #    if ((number >= 0) and (number < 10)):
        #        self.input_string += str(number)
        #    elif (number > 0):
        #        if (number == 13):
        #            self.input_string = ""
        #            self.input_start = 0
        #        elif (number == 14):
        #            self.target_number = int(self.input_string)
        #            print(self.target_number)
    
        #            self.input_string = ""
        #            self.input_start = 0

        # send keypad value to remote
        send_signal(11, data=[number, self.state])

        sleep_ms(150)
        led.off()

        self.state += 1
        if self.state > 255:
            self.state = 0


keypad = Keypad()

while(True):
    clock.tick()
    #img = sensor.snapshot().lens_corr(1.8)

    keypad.catch_keypad_input()

    if DEBUG == 1:
        detect_all_sub_image(img)
        img = print_out_detected_points(img)

        send_signal(8, data=detected_point_list)

    #print("FPS %f" % clock.fps())
    gc.mem_free()
