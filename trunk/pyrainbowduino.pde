//#include "Rainbow.h"
//#include <avr/pgmspace.h>
//#include <math.h>

/*
 --------------------------------------------------------------------------------
 PyRainbowduino.pde
 July 2011
 Based on Rainbowduino_CMD_v2.pde
 Connected to a host via Serial which sets the bitmap for the rainbowduino.
 See also pyrainbodwuino.py for some examples.
 --------------------------------------------------------------------------------
 Rainbowduino_CMD_v2.pde
 November 2009
 Based on RainbowCMD.pde from Seeedstudio and MeggyJr_Plasma.pde 0.3
 Modified to support a new command, SetPixel by david tames http://kino-eye.com
 --------------------------------------------------------------------------------
 Copyright (c) 2009 David Tames.  All right reserved.
 Copyright (c) 2009 Seedstudio.  All right reserved.
 Copyright (c) 2009 Ben Combee.  All right reserved.
 Copyright (c) 2009 Ken Corey.  All right reserved.
 Copyright (c) 2008 Windell H. Oskay.  All right reserved.
 This library is free software: you can redistribute it and/or modify it under the
 terms of the GNU General Public License as published by the Free Software Foundation,
 either version 3 of the License, or (at your option) any later version. This library
 is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
 even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
 See the GNU General Public License for more details. You should have received a copy
 of the GNU General Public License along with this library. If not, see 
 <http://www.gnu.org/licenses/>.
  --------------------------------------------------------------------------------
 */

#define SCREEN_WIDTH 8
#define SCREEN_HEIGHT 8
#define BPP 12
#define MAX_LEVEL (1 << 4)
#define TCNT2_VALUE 0xE5

static unsigned char g_bitmap_serial_buffer[SCREEN_WIDTH * SCREEN_HEIGHT * BPP / 8] = {0x0f, 0x0f};
static bool g_has_new_bitmap = false;
static unsigned char g_bitmap[SCREEN_WIDTH * SCREEN_HEIGHT * BPP / 8] = {0x0f, 0x0f};
static unsigned char g_row = 0;
static unsigned char g_level = 0;

void setup() {
  _init();
  Serial.begin(9600);
}

void loop() {
  read_bitmap_from_serial();
}

void read_bitmap_from_serial() {
  const int kAvailable = Serial.available();
  if (kAvailable >= sizeof(g_bitmap_serial_buffer)) {
    g_has_new_bitmap = false;
    for (unsigned int i = 0; i < sizeof(g_bitmap); ++i) {
      g_bitmap_serial_buffer[i] = Serial.read();
    }
    g_has_new_bitmap = true;
  }
}

ISR(TIMER2_OVF_vect)  {
  TCNT2 = TCNT2_VALUE;
  if (g_has_new_bitmap) {
    memcpy(g_bitmap, g_bitmap_serial_buffer, sizeof(g_bitmap));
    g_has_new_bitmap = false;
  }
  draw_row();
  if (++g_row >= SCREEN_HEIGHT) {
    g_row = 0;
    if (++g_level >= MAX_LEVEL) {
      g_level = 0;
    }
  }
}

void init_timer2(void)  {
  TCCR2A |= (1 << WGM21) | (1 << WGM20);   
  TCCR2B |= (1 << CS22);   // by clk/64
  TCCR2B &= ~((1 << CS21) | (1 << CS20));   // by clk/64
  TCCR2B &= ~((1 << WGM21) | (1 << WGM20));   // Use normal mode
  ASSR |= (0 << AS2);       // Use internal clock - external clock not used in Arduino
  TIMSK2 |= (1 << TOIE2) | (0 << OCIE2B);   //Timer2 Overflow Interrupt Enable
  TCNT2 = TCNT2_VALUE;
  sei();   
}

void _init(void)  {
  DDRD = 0xff;
  DDRC = 0xff;
  DDRB = 0xff;
  PORTD = 0;
  PORTB = 0;
  init_timer2();  // initial the timer for scanning the LED matrix
}

void close_all_lines() {
  PORTD &=~0xf8;
  PORTB &=~0x07;
}

void open_line() {
  PORTB = (PINB & ~0x07) | 0x04 >> g_row;
  PORTD = (PIND & ~0xF8) | (g_row < 3 ? 0 : (0x80 >> (g_row - 3)));
}

void draw_row()  {
  PORTC |= 0x08;  // disable oe
  close_all_lines();
  open_line();
  PORTC |= 0x04;  // le hight
  blit_row();
  PORTC &= ~0x04;  // le low
  PORTC &= ~0x08;  // enable oe
}

void blit_row() {
  // We are using 12 bits per pixel.
  // This is the memory layout in terms of
  // - bits, 
  // - color components
  // - bytes
  // - pixels
  // --------------------------------------
  // |0..3|4..7|8..11|12..15|16..19|20..23|
  // |R   |G   |B    |R     |G     |B     |
  // |   B0    |    B1      |     B2      |
  // |       P0      |           P1       |
  // --------------------------------------
  // It means that ByteX contains:
  // B0=RG, B1=BR, B2=RG, B3=BR, B4=RG, B5=BR,...
  // The simplest way is to just traverse the byte array
  // and use the mask to extract the color component for
  // that byte.
  static const int kWidthInBytes = SCREEN_WIDTH * BPP / 8;
  static const unsigned char kMasks[3][kWidthInBytes] = {
    // Green
    {0xF0, 0x00, 0x0F, 
     0xF0, 0x00, 0x0F,
     0xF0, 0x00, 0x0F,
     0xF0, 0x00, 0x0F},
    // Red
    {0x0F, 0xF0, 0x00, 
     0x0F, 0xF0, 0x00, 
     0x0F, 0xF0, 0x00, 
     0x0F, 0xF0, 0x00},
    // Blue
    {0x00, 0x0F, 0xF0,
     0x00, 0x0F, 0xF0,
     0x00, 0x0F, 0xF0,
     0x00, 0x0F, 0xF0},              
  };
  const int kByteStart = g_row * kWidthInBytes;
  for (unsigned int color = 0; color < 3; ++color) {
    for (unsigned int b = 0; b < 12; ++b) {
      const unsigned char kMask = kMasks[color][b];
      if (!kMask) continue;
      unsigned char color_level = 
        (g_bitmap[kByteStart + b] & kMask);
      if (kMask == 0xF0)
        color_level >>= 4;
      if (color_level > g_level) {
        PORTC |= 0x01;
      } else {
        PORTC &= ~0x01;
      }
      // Toggle clock.
      PORTC &= ~0x02;
      PORTC |= 0x02;
    }
  }
}

