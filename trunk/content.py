#!/usr/bin/python

# This library is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version. This library
# is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details. You should have received a copy
# of the GNU General Public License along with this library. If not, see
# <http://www.gnu.org/licenses/>.


import comms
import datetime
import json
import png
import random
import struct
import time


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


def Randomness(frame_sender):
  """Some randomness to check things blink."""
  frame = []
  frame += [0xf0,0x07, 0x07, 0x00, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0x0f,0x07, 0x70, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0x00,0xf0, 0x77, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
  frame += [0] * (96 - len(frame))
  frame = [0, 0xf0, 0x0f, 0x77, 0x70, 0x07]
  frame = (frame * 20)[:96]
  while True:
    random.shuffle(frame)
    frame_sender.Send(comms.FrameSender.PackFrame(frame))
    time.sleep(0.2)


class Pattern(object):
  def __init__(self, frame_sender):
    self.frame_sender = frame_sender
    self.red = [x for x in [0x07, 0xf0, 0x00] * 32]
    self.green = [x for x in [0x70, 0x00, 0x0f] * 32]
    self.blue = [x for x in [0x00, 0x07, 0xf0] * 32]
    self.rg = [x for x in [0x77, 0x00, 0x00] * 32]
    self.rb = [x for x in [0x07, 0x07, 0x00] * 32]
    self.gb = [x for x in [0x70, 0x07, 0x00] * 32]

  @staticmethod
  def Renderer(frame_sender):
    pattern = Pattern()
    while True:
      for p in [pattern.red,
                pattern.green,
                pattern.blue,
                pattern.rg, pattern.rb, pattern.gb]:
        pattern.frame_sender.Send(comms.FrameSender.PackFrame(p))
        time.sleep(0.2)


class CharRenderer(object):
  def __init__(self, char_frame, frame_sender):
    self.char_frame = char_frame
    self.ticker = 0
    self.delta = 1
    self.frame_sender = frame_sender

  def SendCharAndWait(self, char, wait):
    frame = self.char_frame.ForChar(str(char))
    self.frame_sender.Send(comms.FrameSender.PackFrame(frame))
    time.sleep(wait)

  def SendTickerElementAndWait(self, string, wait):
    self.ticker += self.delta
    if self.ticker >= (len(string) - 1) * 8:
      self.delta *= -1
      self.ticker = (len(string) - 1) * 8
    elif self.ticker <= 0:
      self.delta *= -1
      self.ticker = 0
    frame = self.char_frame.ForString(string, self.ticker)
    self.frame_sender.Send(comms.FrameSender.PackFrame(frame))
    time.sleep(wait)
    
  def SendFullStringAndWait(self, string, wait):
    for i in xrange(len(string) * 8):
      self.SendTickerElementAndWait(string, wait)
    self.ResetTicker()

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
    self.char_renderer.SendFullStringAndWait(string, 0.1)

  def SendTime(self):
    if self.ticker:
      self._SendTimeTicker()
    else:
      self._SendTimeDiscrete()

  @staticmethod
  def Renderer(frame_sender):
    font_reader = PngFontReader('8x8font_green.png')
    char_frame = CharFrame(font_reader.rgb8, 32)
    char_renderer = CharRenderer(char_frame, frame_sender)
    clock = Clock(char_renderer, True)
    while True:
      clock.SendTime()


class Combined(object):
  @staticmethod
  def Renderer(frame_sender):
    png_font_reader = PngFontReader('8x8fontINV.png')
    char_frame = CharFrame(png_font_reader.rgb8, 0)
    char_renderer_0 = CharRenderer(char_frame, frame_sender)
    tag_liner = comms.UrlPlainTextFetcher('http://www.textfiles.com/humor/TAGLINES/taglines.txt')

    png_font_reader = PngFontReader('8x8font_green.png')
    char_frame = CharFrame(png_font_reader.rgb8, 32)
    char_renderer = CharRenderer(char_frame, frame_sender)
    clock = Clock(char_renderer, True)

    cycle = 0
    # Number of cycles required to cycle hh:mi back and forth.
    CLOCK_CYCLES = 6 * 8 * 2
    twitter_toggle = False
    while True:
      if cycle < CLOCK_CYCLES:
        cycle += 1
        clock.SendTime()
      else:
        twitter_toggle = not twitter_toggle
        if twitter_toggle:
          twitter_trending = TwitterTrending()
          text = twitter_trending.GetTopics()
        else:
          text = tag_liner.GetRandomLine()
        ticker.SendStringAndWait(text, 0.1)
        cycle = 0


def main():
  frame_sender = comms.UdpSender('localhost', 9000)
  #Randomness()
  #Pattern.Renderer()
  #Clock.Renderer()
  #TagLiner.Renderer()
  Combined.Renderer(frame_sender)

if __name__ == '__main__':
  main()
