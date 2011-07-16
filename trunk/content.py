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
import png
import random
import renderer
import struct
import time


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
    pattern = Pattern(frame_sender)
    while True:
      for p in [pattern.red,
                pattern.green,
                pattern.blue,
                pattern.rg, pattern.rb, pattern.gb]:
        pattern.frame_sender.Send(comms.FrameSender.PackFrame(p))
        time.sleep(0.2)


class Clock(object):
  def __init__(self, char_renderer):
    self.char_renderer = char_renderer

  def SendTime(self):
    string = datetime.datetime.now().strftime(' %H:%M ')
    self.char_renderer.SendFullStringAndWait(string, 0.1)

  @staticmethod
  def Renderer(frame_sender):
    font_reader = renderer.PngFontReader('8x8font_green.png')
    char_frame = renderer.CharFrame(font_reader.rgb8, 32)
    char_renderer = renderer.CharRenderer(char_frame, frame_sender)
    clock = Clock(char_renderer)
    while True:
      clock.SendTime()


class Combined(object):
  @staticmethod
  def Renderer(frame_sender):
    png_font_reader = renderer.PngFontReader('8x8fontINV.png')
    char_frame = renderer.CharFrame(png_font_reader.rgb8, 0)
    char_renderer_0 = renderer.CharRenderer(char_frame, frame_sender)
    tag_lines = comms.UrlPlainTextFetcher('http://www.textfiles.com/humor/TAGLINES/taglines.txt')

    png_font_reader = renderer.PngFontReader('8x8font_green.png')
    char_frame = renderer.CharFrame(png_font_reader.rgb8, 32)
    char_renderer = renderer.CharRenderer(char_frame, frame_sender)
    clock = Clock(char_renderer, True)

    cycle = 0
    # Number of cycles required to cycle hh:mi back and forth.
    CLOCK_CYCLES = 2
    twitter_toggle = False
    while True:
      if cycle < CLOCK_CYCLES:
        cycle += 1
        clock.SendTime()
      else:
        twitter_toggle = not twitter_toggle
        if twitter_toggle:
          twitter_trending = comms.TwitterTrending()
          text = twitter_trending.GetTopics()
        else:
          text = tag_lines.GetRandomLine()
        char_renderer_0.SendFullStringAndWait(text, 0.1)
        cycle = 0


def main():
  #frame_sender = comms.SerialSender()
  frame_sender = comms.UdpSender('localhost', 9000)
  #Randomness(frame_sender)
  #Pattern.Renderer(frame_sender)
  #Clock.Renderer(frame_sender)
  #Combined.Renderer(frame_sender)

if __name__ == '__main__':
  main()
