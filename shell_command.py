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
import content
import optparse
import renderer
import subprocess
import shlex


def GetCmdOutput(command):
  p = subprocess.Popen(command, stdout=subprocess.PIPE)
  stdout = p.communicate()[0]
  return stdout


def ExecuteCommand(command, begin, end):
  data = GetCmdOutput(shlex.split(command))
  data = data.split('\n')
  if not begin:
    begin = 0
  if not end:
    end = len(data)
  data = ''.join(data[begin:end])
  frame_sender = comms.UdpSender()
  font_name = '8x8fontINV.png'
  char_start = 0
  if len(data) < 6:
    font_name = '8x8font_green.png'
    char_start = 32
  png_font_reader = renderer.PngFontReader(font_name)
  char_frame = renderer.CharFrame(png_font_reader.rgb8, char_start)
  char_renderer = renderer.CharRenderer(char_frame, frame_sender)
  char_renderer.SendFullStringAndWait(data, 0.1)
  char_renderer.SendCharAndWait(' ', 0.1)


def main():
  parser = optparse.OptionParser()
  parser.add_option('-c', '--cmd', dest='cmd',
                    help='cmd to execute')
  parser.add_option('-b', '--begin', dest='begin',
                    type=int,
                    help='beginning line to send')  
  parser.add_option('-e', '--end', dest='end',
                    type=int,
                    help='end line to send')
  options, _ = parser.parse_args()
  ExecuteCommand(options.cmd, options.begin, options.end)

if __name__ == '__main__':
  main()
