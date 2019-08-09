#include <msp430.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ***************
// ****************
// SET LCD!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// RS: P1.0
// R/W: P1.1
// E: P1.2
// ***************
// ****************
#define CS1 P1OUT |= BIT0 // RS
#define CS0 P1OUT &= BIT0
#define SID1 P1OUT |= BIT1 // R/W
#define SID0 P1OUT &= ~BIT1
#define SCLK1 P1OUT |= BIT2 // E
#define SCLK0 P1OUT &= ~BIT2
// PSB connect to ground since we only use serial transition mode

// data=00001100, always remember it's "d7 d6 d5 d4 d3 d2 d1 d0"
// if you need to know how to set d7-d0, just check ST7920V30_eng.pdf

#define chip_select_1 CS1 // RS
#define chip_select_0 CS0
#define serial_data_input_1 SID1 // R/W
#define serial_data_input_0 SID0
#define serial_clock_1 SCLK1 // E
#define serial_clock_0 SCLK0

void millisecond_of_delay(unsigned int t) {
    while (t--) {
        // delay for 1ms
        __delay_cycles(10000);
    }
}

void send_byte(unsigned char eight_bits) {
    unsigned int i;

    for (i = 0; i < 8; i++) {
        // 1111 1000 & 1000 0000 = 1000 0000 = True
        // 1111 0000 & 1000 0000 = 1000 0000 = True
        // 1110 0000 & 1000 0000 = 1000 0000 = True
        //...
        // 0000 0000 & 1000 0000 = 0000 0000 = False
        // The main purpose for this is to send a series of binary number from
        // left to right
        if ((eight_bits << i) & 0x80) {
            serial_data_input_1;
        } else {
            serial_data_input_0;
        }
        // We use this to simulate clock:
        serial_clock_0;
        serial_clock_1;
    }
}

void write_command(unsigned char command) {
    chip_select_1;

    send_byte(0xf8);
    /*
    f8=1111 1000;
    send five 1 first, so LCD will papare for receiving data;
    then R/W = 0, RS = 0;
    when RS = 0, won't write d7-d0 to RAM
    */
    send_byte(command & 0xf0);        // send d7-d4
    send_byte((command << 4) & 0xf0); // send d3-d0
    /*
    f0 = 1111 0000

    if character = 1100 0011
    first send 1100 0000 (d7-d4 0000)
    then send 0011 0000 (d3-d0 0000)
    */

    millisecond_of_delay(1);
    chip_select_0; // when chip_select from 1 to 0, serial counter and data will
                   // be reset
}

void write_data(unsigned char character) {
    chip_select_1;

    send_byte(0xfa);
    /*
    fa=1111 1010;

    send five 1 first, so LCD will papare for receiving data;
    then R/W = 0, RS = 1;
    when RS = 1, write d7-d0 to RAM
    */
    send_byte(character & 0xf0);        // send d7-d4
    send_byte((character << 4) & 0xf0); // send d3-d0
    /*
    f0 = 1111 0000

    if character = 1100 0011
    first send 1100 0000 (d7-d4 0000)
    then send 0011 0000 (d3-d0 0000)
    */

    millisecond_of_delay(1);
    chip_select_0;
}

void print_string(unsigned int x, unsigned int y, unsigned char *string) {
    switch (y) {
    case 1:
        write_command(0x80 + x);
        break;
    case 2:
        write_command(0x90 + x);
        break;
    case 3:
        write_command(0x88 + x);
        break;
    case 4:
        write_command(0x98 + x);
        break;
    default:
        break;
    }

    while (*string > 0) {
        write_data(*string);
        string++;
        millisecond_of_delay(1);
    }
}

void print_unsigned_char(int x, int y, unsigned char data) {
    char text[20];
    sprintf(text, "%02x", data);
    print_string(x, y, text);
}

void print_number(int x, int y, long int number) {
    char text[20];
    sprintf(text, "%d", number);
    print_string(x, y, text);
}

void reverse_a_string_with_certain_length(char *str, int len) {
    int i = 0, j = len - 1, temp;
    while (i < j) {
        temp = str[i];
        str[i] = str[j];
        str[j] = temp;
        i++;
        j--;
    }
}

int int_to_string(int x, char str[], int d) {
    int i = 0;
    while (x) {
        str[i++] = (x % 10) + '0';
        x = x / 10;
    }

    // If number of digits required is more, then
    // add 0s at the beginning
    while (i < d)
        str[i++] = '0';

    reverse_a_string_with_certain_length(str, i);
    str[i] = '\0';
    return i;
}

void float_to_string(float n, char *res, int afterpoint) {
    // Extract integer part
    int ipart = (int)n;

    // Extract floating part
    float fpart = n - (float)ipart;

    // convert integer part to string
    int i = int_to_string(ipart, res, 0);

    // check for display option after point
    if (afterpoint != 0) {
        res[i] = '.'; // add dot

        // Get the value of fraction part upto given no.
        // of points after dot. The third parameter is needed
        // to handle cases like 233.007
        int power = 1;
        int count_num = 0;
        for (; count_num < afterpoint; count_num++) {
            power = power * 10;
        }
        fpart = fpart * power;

        int_to_string((int)fpart, res + i + 1, afterpoint);
    }
}

void print_float(int x, int y, float number) {
    char text[20];
    if (number < 0) {
        number = -number;
        char text2[20];
        strcpy(text, "-");
        float_to_string(number, text2, 4);
        strcat(text, text2);
    } else {
        float_to_string(number, text, 4);
    }
    print_string(x, y, text);
}

void screen_clean() {
    write_command(0x01);
}

void force_screen_clean() {
    unsigned char i, j, k;

    write_command(0x34); //打开扩展指令集，绘图显示关
    write_command(0x36); //打开扩展指令集，绘图显示开

    for (i = 0; i < 2; i++) //分上下两屏写
    {
        for (j = 0; j < 32; j++) {
            write_command(0x80 + j); //写Y 坐标
            millisecond_of_delay(1);
            if (i == 0) //写X 坐标
            {
                write_command(0x80);
                millisecond_of_delay(1);
            } else //写下半屏
            {
                write_command(0x88);
                millisecond_of_delay(1);
            }

            for (k = 0; k < 16; k++) { //写一整行数据
                write_data(0x00);
                millisecond_of_delay(1);
            }
        }
    }

    write_command(0x30); //关闭扩展指令集
}

void draw_graph(const unsigned char *graphic) {
    force_screen_clean();
    write_command(0x34); //开启扩展指令集，并关闭画图显示。

    unsigned char x, y;
    for (y = 0; y < 64; y++) {
        if (y < 32) {
            for (x = 0; x < 8; x++)                      // Draws top half of the screen.
            {                                            // In extended instruction mode, vertical and horizontal coordinates must be specified before sending data in.
                write_command(0x80 | y);                 // Vertical coordinate of the screen is specified first. (0-31)
                write_command(0x80 | x);                 // Then horizontal coordinate of the screen is specified. (0-8)
                write_data(graphic[2 * x + 16 * y]);     // Data to the upper byte is sent to the coordinate.
                write_data(graphic[2 * x + 1 + 16 * y]); // Data to the lower byte is sent to the coordinate.
            }
        } else {
            for (x = 0; x < 8; x++)             // Draws bottom half of the screen.
            {                                   // Actions performed as same as the upper half screen.
                write_command(0x80 | (y - 32)); // Vertical coordinate must be scaled back to 0-31 as it is dealing with another half of the screen.
                write_command(0x88 | x);
                write_data(graphic[2 * x + 16 * y]);
                write_data(graphic[2 * x + 1 + 16 * y]);
            }
        }
    }

    write_command(0x36); //开显示
    write_command(0x30); //转回基本指令集
}

void initialize_LCD() {
    P1DIR = 0xFF;
    P1OUT = 0x00;

    millisecond_of_delay(1000); // delay for LCD to wake up

    write_command(0x30); // 30=0011 0000; use `basic instruction mode`, use
                         // `8-BIT interface`
    millisecond_of_delay(20);
    write_command(0x0c); // 0c=0000 1100; DISPLAY ON, cursor OFF, blink OFF
    millisecond_of_delay(20);
    write_command(0x01); // 0c=0000 0001; CLEAR

    millisecond_of_delay(200);
}

// ***************
// ****************
// SET Serial Communication!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
//
// TX(transmit): P3.4
// RX(receive): P3.5
//
// One thing you have to know: Tx connect to Rx, Rx connect to Tx  !!!!!!!!!
//
// VCC: 3.3V
//
// ***************
// ****************

void initialize_serial_communication() {
    /* for 115200 baud */
    volatile unsigned int i;
    WDTCTL = WDTPW + WDTHOLD; // Stop WDT
    P3SEL |= 0x30;            // P3.4 and P3.5 = USART0 TXD/RXD

    BCSCTL1 &= ~XT2OFF; // XT2on

    do {
        IFG1 &= ~OFIFG; // Clear OSCFault flag
        for (i = 0xFF; i > 0; i--)
            ;                 // Time for flag to set
    } while ((IFG1 & OFIFG)); // OSCFault flag still set?

    BCSCTL2 |= SELM_2 + SELS; // MCLK = SMCLK = XT2 (safe)
    ME1 |= UTXE0 + URXE0;     // Enable USART0 TXD/RXD
    UCTL0 |= CHAR;            // 8-bit character
    UTCTL0 |= SSEL1;          // UCLK = SMCLK
    UBR00 = 0x45;             // 8MHz 115200
    UBR10 = 0x00;             // 8MHz 115200
    UMCTL0 = 0x00;            // 8MHz 115200 modulation
    UCTL0 &= ~SWRST;          // Initialize USART state machine

    IE1 |= URXIE0; // Enable USART0 RX interrupt

    _BIS_SR(GIE); // just enable general interrupt
}

unsigned int STATE_YOU_WANT_TO_SEND = 0;
void send_state_to_serial(int state) {
    STATE_YOU_WANT_TO_SEND = state;
}

unsigned int STATE_FROM_SERIAL = 0;
unsigned int TASK_NUMBER = 0;

unsigned int data_arraving = 0;
unsigned int data_index = 0;

//unsigned int an_image[256] = {
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
//};
unsigned int an_image[257];
unsigned int image_index = 0;
unsigned int an_image_received = 0;

#pragma vector = USART0RX_VECTOR
__interrupt void usart0_rx(void) {
    while (!(IFG1 & UTXIFG0)) {
        // USART0 TX buffer ready?
    }
    STATE_FROM_SERIAL = (int)RXBUF0;                // receive state
    //TXBUF0 = (unsigned char)STATE_YOU_WANT_TO_SEND; // send state

    //if (STATE_FROM_SERIAL != 0 || data_arraving == 1) {
    //    if (data_arraving == 0) {
    //        TASK_NUMBER = STATE_FROM_SERIAL;
    //        if (TASK_NUMBER == 8) {
    //            data_arraving = 1;
    //            an_image_received = 0;
    //        }
    //    } else {
    //        if (data_index > 257) {
    //            data_arraving = 0;
    //            data_index = 0;
    //            an_image_received = 1;
    //        }
    //        if (STATE_FROM_SERIAL == 9) {
    //            an_image[data_index] = 0;
    //        } else {
    //            an_image[data_index] = 1;
    //        }
    //        data_index += 1;
    //    }
    //} else {
    //    TASK_NUMBER = 0;
    //}

    if (STATE_FROM_SERIAL != 0 || data_arraving == 1) {
        if (data_arraving == 0) {
            TASK_NUMBER = STATE_FROM_SERIAL;
            if (TASK_NUMBER == 8) {
                an_image_received = 0;
            }
            data_arraving = 1;
        } else {
            if (TASK_NUMBER == 8) {
                if (data_index < 256) {
                    if (STATE_FROM_SERIAL == 9) {
                        an_image[data_index] = 1;
                    } else {
                        an_image[data_index] = 0;
                    }
                } else { // data_index == 256, actually the 257 element
                    image_index = STATE_FROM_SERIAL;
                }
            }

            data_index += 1;

            if (data_index > 256) {
                data_arraving = 0;
                data_index = 0;
                if (TASK_NUMBER == 8) {
                    an_image_received = 1;
                }
            }
        }
    } else {
        TASK_NUMBER = 0;
    }
}

void draw_picture_from_serial() {
    // convert 16x16 points to 8x16
    unsigned char new_data[128];
    int new_data_index = 0;

    unsigned char y, x;
    for (y = 0; y < 16; y++) {
        for (x = 0; x < 16; x++) {
            if (x % 2 != 0) { // only work for odd index, for example, 1,3,5,7
                int first, second;
                first = an_image[(y * 16) + x];
                second = an_image[((y * 16) + x) - 1];
                if ((first == 0) && (second == 1)) {
                    new_data[new_data_index] = 0x0f;
                } else if ((first == 1) && (second == 0)) {
                    new_data[new_data_index] = 0xf0;
                } else if ((first == 1) && (second == 1)) {
                    new_data[new_data_index] = 0xff;
                } else if ((first == 0) && (second == 0)) {
                    new_data[new_data_index] = 0x00;
                }
                new_data_index++;
            }
        }
    }

    // start drawing
    force_screen_clean();
    write_command(0x34); //开启扩展指令集，并关闭画图显示。
    write_command(0x36); //开显示

    unsigned char i, ii, iii;
    for (i = 0; i < 16; i++) {
        if (i < 8) {
            for (ii = 0; ii < 4; ii++) {
                write_command(0x80 + ii + 4 * i);
                write_command(0x80);
                for (iii = 0; iii < 8; iii++) {
                    write_data(new_data[i * 8 + iii]);
                }
                for (iii = 0; iii < 8; iii++) {
                    write_data(0x00);
                }
            }
        } else {
            for (ii = 0; ii < 4; ii++) {
                write_command(0x80 + ii + 4 * i - 32);
                write_command(0x88);
                for (iii = 0; iii < 8; iii++) {
                    write_data(new_data[i * 8 + iii]);
                }
                for (iii = 0; iii < 8; iii++) {
                    write_data(0x00);
                }
            }
        }
    }

    write_command(0x30); //转回基本指令集
}

int main(void) {
    WDTCTL = WDTPW | WDTHOLD; // stop watchdog timer

    initialize_LCD();
    initialize_serial_communication();

    int i = 0;
    while (1) {
        //print_number(0, 1, TASK_NUMBER);
        //print_number(0, 2, an_image_received);
        //print_number(0, 3, image_index);
        //print_number(0, 4, STATE_FROM_SERIAL);
        ////print_number(0, 4, i);
        //millisecond_of_delay(500);
        //screen_clean();

        //i++;
        //if (i > 50) {
        //    i = 0;
        //}

        if (an_image_received == 1) {
            draw_picture_from_serial();

            //millisecond_of_delay(100);
            an_image_received = 0;
        }
    }

    return 0;
}