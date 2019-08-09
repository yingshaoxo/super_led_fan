        led.on()

        if (number != 10): # != resend key
            if (number < 10):
                self.input_string += str(number)
            elif (number == 14 or number == 15): # confire button
                try:
                    self.state += 1
                    if (self.state == 0):
                        self.task_number_from_keypad = int(self.input_string)
                        self.input_string = ""
                    if (self.state == 1):
                        self.paramater_list[0] = int(self.input_string)
                        self.input_string = ""
                    if (self.state == 2):
                        self.paramater_list[1] = int(self.input_string)
                        self.input_string = ""
                    if (self.state == 3):
                        self.paramater_list[2] = int(self.input_string)
                        self.input_string = ""
                    if (self.state > 3):
                        return
                except Exception as e:
                    self.state = -1
                    self.input_string = ""
                    self.paramater_list = [254, 254, 254]
                    self.task_number_from_keypad = 0
            elif (number == 11 or number == 12 or number == 13): # cancle button
                self.state = -1
                self.input_string = ""
                self.paramater_list = [254, 254, 254]
                self.task_number_from_keypad = 0
        
        # send data according to different task
        if (self.task_number_from_keypad != 0):
            send_signal(self.task_number_from_keypad, data=[self.paramater_list[0], self.paramater_list[1], self.paramater_list[2]])

        print("key:", number, "task:", self.task_number_from_keypad, "p:", self.paramater_list)

        sleep_ms(150)
        led.off()
