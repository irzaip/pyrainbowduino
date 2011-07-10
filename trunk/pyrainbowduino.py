#!/usr/bin/python

# This library is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version. This library
# is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details. You should have received a copy
# of the GNU General Public License along with this library. If not, see
# <http://www.gnu.org/licenses/>.


import datetime
import png
import random
import struct
import time
import urllib


class PngFontReader(object):
  """Reads a png and stores a list of rows containing R, G, B."""
  def __init__(self, filename):
    self.png = png.Reader(filename=filename)
    self.rgb8 = [row for row in self.png.asRGB8()[2]]


class CharFrame(object):
  """Used to obtain 4BPP frames from an image strip."""
  def __init__(self, font_8bpp, first_char):
    self.font_8bpp = font_8bpp
    self.first_char = first_char

  def _RGB8To4BPP(self, rgb8):
    ret = []
    for i in xrange(len(rgb8) - 1, 0, -6):
      # Packs 2 RGB8 pixels in 3 bytes
      ret += [(rgb8[i - 2] >> 4) |
              ((rgb8[i - 1] >> 4) << 4),
              (rgb8[i] >> 4) |
              ((rgb8[i - 5] >> 4) << 4),
              (rgb8[i - 4] >> 4) |
              ((rgb8[i - 3] >> 4) << 4)]
    return ret

  def ForChar(self, char):
    """Returns an 8x8x4bpp frame for the given char."""
    col_start = (ord(char) - self.first_char) * 8 * 3
    rgb8 = []
    for row in xrange(8):
      rgb8 += self.font_8bpp[row][col_start : col_start + 8 * 3]
    ret = self._RGB8To4BPP(rgb8)
    return ret

  def ForString(self, string, start_pixel_column):
    """Returns an 8x8x4bpp frame for the given string, starting at start_pixel_column."""
    char_0 = start_pixel_column / 8
    char_0_num_pixels = 8 - (start_pixel_column % 8)
    char_0_col_start = (ord(string[char_0]) - self.first_char) * 8 * 3
    char_1_col_start = (ord(string[(start_pixel_column + 7) / 8]) - self.first_char) * 8 * 3
    rgb8 = []
    for row in xrange(8):
      rgb8 += (self.font_8bpp[row][char_0_col_start + (8 - char_0_num_pixels) * 3 :
                                   char_0_col_start + 8 * 3] +
               self.font_8bpp[row][char_1_col_start :
                                   char_1_col_start + (8 - char_0_num_pixels) * 3])
    ret = self._RGB8To4BPP(rgb8)
    return ret


class FrameSender(object):
  """Sends a 8x8x4bpp RGB frame to rainbowduino over serial."""
  def __init__(self):
    self.serial = file('/dev/ttyUSB0', 'w')
    self.last_frame = None

  def Close():
    self.serial.close()

  def Send(self, frame):
    if self.last_frame == frame:
      return
    self.last_frame = frame
    d = struct.pack('B' * 8 * 12, *frame)
    self.serial.write(d)
    self.serial.flush()


def Randomness():
  """Some randomness to check things blink."""
  frame = []
  frame += [0xf0,0x07, 0x07, 0x00, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0x0f,0x07, 0x70, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0x00,0xf0, 0x77, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0] * (96 - len(frame))
  sender = FrameSender()
  sender.Send(frame)
  frame = [0, 0xf0, 0x0f, 0x77, 0x70, 0x07]
  frame = (frame * 20)[:96]
  while True:
    random.shuffle(frame)
    sender.Send(frame)
    time.sleep(0.2)


class Pattern(object):
  def __init__(self):
    self.sender = FrameSender()
    self.red = [x for x in [0x07, 0xf0, 0x00] * 32]
    self.green = [x for x in [0x70, 0x00, 0x0f] * 32]
    self.blue = [x for x in [0x00, 0x07, 0xf0] * 32]
    self.rg = [x for x in [0x77, 0x00, 0x00] * 32]
    self.rb = [x for x in [0x07, 0x07, 0x00] * 32]
    self.gb = [x for x in [0x70, 0x07, 0x00] * 32]

  @staticmethod
  def Renderer():
    pattern = Pattern()
    while True:
      for p in [pattern.red,
                pattern.green,
                pattern.blue,
                pattern.rg, pattern.rb, pattern.gb]:
        pattern.sender.Send(p)
        time.sleep(0.2)


class CharRenderer(object):
  def __init__(self, char_frame):
    self.char_frame = char_frame
    self.ticker = 0
    self.delta = 1
    self.sender = FrameSender()

  def SendCharAndWait(self, char, wait):
    self.sender.Send(self.char_frame.ForChar(str(char)))
    time.sleep(wait)

  def SendTickerStringAndWait(self, string, wait):
    self.ticker += self.delta
    if self.ticker >= (len(string) - 1) * 8:
      self.delta *= -1
      self.ticker = (len(string) - 1) * 8
    elif self.ticker <= 0:
      self.delta *= -1
      self.ticker = 0
    self.sender.Send(self.char_frame.ForString(string, self.ticker))
    time.sleep(wait)

  def ResetTicker(self):
    self.ticker = 0
    self.delta = 1


class Clock(object):
  def __init__(self, char_renderer, ticker):
    self.char_renderer = char_renderer
    self.ticker = ticker

  def _SendTimeDiscrete(self):
    now = datetime.datetime.now()
    self.char_renderer.SendCharAndWait(now.hour / 10, 0.8)
    self.char_renderer.SendCharAndWait(now.hour % 10, 0.8)
    self.char_renderer.SendCharAndWait(':', 0.2)
    self.char_renderer.SendCharAndWait(now.minute / 10, 0.8)
    self.char_renderer.SendCharAndWait(now.minute % 10, 0.8)
    self.char_renderer.SendCharAndWait('*', 0.8)

  def _SendTimeTicker(self):
    string = datetime.datetime.now().strftime(' %H:%M ')
    self.char_renderer.SendTickerStringAndWait(string, 0.1)

  def SendTime(self):
    if self.ticker:
      self._SendTimeTicker()
    else:
      self._SendTimeDiscrete()

  @staticmethod
  def Renderer():
    clock = Clock(CharRenderer(CharFrame(PngFontReader('8x8font_green.png').rgb8, 32)),
                  True)
    while True:
      clock.SendTime()


class TagLiner(object):
  def __init__(self, char_renderer, tag_lines_url):
    self.char_renderer = char_renderer
    data = urllib.urlopen(tag_lines_url).readlines()
    self.tag_lines = [x.replace('\n','').replace('\r','').strip() for x in data]
    random.shuffle(self.tag_lines)

  def SendRandomTagLine(self):
    random_tag_line = random.choice(self.tag_lines)
    for i in xrange(len(random_tag_line) * 8):
      self.char_renderer.SendTickerStringAndWait(random_tag_line, 0.1)
    self.char_renderer.ResetTicker()

  @staticmethod
  def Renderer():
    tag_liner = TagLiner(CharRenderer(CharFrame(PngFontReader('8x8fontINV.png').rgb8, 0)),
                         'http://www.textfiles.com/humor/TAGLINES/taglines.txt')
    while True:
      tag_liner.SendRandomTagLine()


def main():
  #Randomness()
  #Pattern.Renderer()
  Clock.Renderer()
  #TagLiner.Renderer()

if __name__ == '__main__':
  main()
