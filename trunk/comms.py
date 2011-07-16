#!/usr/bin/python

# This library is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version. This library
# is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details. You should have received a copy
# of the GNU General Public License along with this library. If not, see
# <http://www.gnu.org/licenses/>.


import random
import socket
import struct
import urllib


class FrameSender(object):
  @staticmethod
  def PackFrame(frame):
    return struct.pack('B' * 8 * 12, *frame)
    
  def Send(self, packed_frame):
    pass

  def Close():
    pass

class SerialSender(FrameSender):
  """Sends a 8x8x4bpp RGB frame to rainbowduino over serial."""
  def __init__(self, serial_file_name='/dev/ttyUSB0'):
    self.serial = file(serial_file_name, 'w')
    self.last_frame = None

  def Close():
    self.serial.close()

  def Send(self, packed_frame):
    if self.last_frame == packed_frame:
      return
    self.last_frame = packed_frame
    self.serial.write(packed_frame)
    self.serial.flush()


class UdpSender(FrameSender):
  """Sends a 8x8x4bpp RGB frame to rainbowduino over UDP to a server."""
  def __init__(self, host, port):
    self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.host_port = (host, port)
    self.last_frame = ''
    
  def Close():
    self.s.close()

  def Send(self, packed_frame):
    print 'Sending...'
    if self.last_frame == packed_frame:
      return
    self.last_frame = packed_frame
    self.s.sendto(packed_frame, self.host_port)
    print 'Sent...'


class UdpBridge(object):
  """Receives a 8x8x4bpp RGB frame from UDP and sends to rainbowduino over serial."""
  def __init__(self, host, port, serial):
    self.serial_frame = SerialSender(serial)
    self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.s.bind((host, port))
    
  def Loop(self):
    while True:
      data, addr = self.s.recvfrom(8 * 12)
      self.serial_frame.Send(data)


class UrlPlainTextFetcher(object):
  def __init__(self, tag_lines_url):
    data = urllib.urlopen(tag_lines_url).readlines()
    self.lines = [x.replace('\n','').replace('\r','').strip() for x in data]
    random.shuffle(self.lines)

  def GetRandomLine(self):
    return random.choice(self.line)


class TwitterTrending(object):
  def __init__(self):
    twitter_json = urllib.urlopen('http://api.twitter.com/1/trends/current.json').read()
    twitter_data = json.loads(twitter_json)
    self.topics = [t['name'].encode('ascii', errors='replace') for t in 
                   twitter_data['trends'][twitter_data['trends'].keys()[0]]]

  def GetTopics(self):
    return '|'.join(self.topics)
