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
import os
import png
import random
import struct
import sys
import time


class PngFontReader(object):
  """Reads a png and stores a list of rows containing R, G, B."""
  def __init__(self, filename):
    if not os.path.exists(filename):
      filename = os.path.join(os.path.dirname(sys.argv[0]),
                              os.path.basename(filename))
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
    if col_start >= len(self.font_8bpp[0]):
      col_start = 0
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
    if char_0_col_start > len(self.font_8bpp[0]):
      char_0_col_start = 0
    char_1_col_start = (ord(string[(start_pixel_column + 7) / 8]) - self.first_char) * 8 * 3
    if char_1_col_start > len(self.font_8bpp[0]):
      char_1_col_start = 0
    rgb8 = []
    for row in xrange(8):
      rgb8 += (self.font_8bpp[row][char_0_col_start + (8 - char_0_num_pixels) * 3 :
                                   char_0_col_start + 8 * 3] +
               self.font_8bpp[row][char_1_col_start :
                                   char_1_col_start + (8 - char_0_num_pixels) * 3])
    ret = self._RGB8To4BPP(rgb8)
    return ret


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
    for i in xrange(len(string)* 8):
      self.SendTickerElementAndWait(string, wait)
    self.ResetTicker()

  def ResetTicker(self):
    self.ticker = 0
    self.delta = 1
