#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket
import struct


def read(host,port,filename):
  clientsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  clientsocket.settimeout(5)
  pack_format = '!H%dsB5sB' % len(filename)
  sendpacket = struct.pack(pack_format, 1, filename, 0, b'octet', 0)
  clientsocket.sendto(sendpacket, (host, port))
  while True:
      try:
        receivedpacket, remotesocket = clientsocket.recvfrom(512)
        opcode = struct.unpack('!H', receivedpacket[0:2])[0]
      except:
        clientsocket.sendto(sendpacket, (host, port))
        continue
      if opcode == 3: #DATA PACKET
        block = struct.unpack('!H',receivedpacket[2:4])[0]
        data = receivedpacket[4:]
        sendpacket = struct.pack(b'!2H', 4, block) #ACK PACKET
        clientsocket.sendto(sendpacket, remotesocket)
        if len(receivedpacket) < 512:
            print "DONE!"
            break
      elif opcode == 5: #ERROR PACKET
        errCode = struct.unpack('!H',receivedpacket[2:4])[0]
        errString = receivedpacket[4:-1]
        print "ERROR(" + errCode + ") : " + errString
        break


def write(host,port,filename):
  if not os.path.isfile(filename):
     print "file not found"
     return
  s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  s.connect((host, port))
  print "WRITE: Connected to " + host + " on port " + str(port)

def main():
  if len(sys.argv) != 4 and len(sys.argv) != 5:
    print "The program takes 4 arguments:\
           servername, command and port(optional)"
    return
  host = sys.argv[1]
  command = sys.argv[2]
  filename = sys.argv[3]
  if len(sys.argv)>4:
    try:
      port = int(sys.argv[4])
    except ValueError:
      print "the port has to be an integer number"
      return
  else:
    port = 69
  if command == "lesa":
    read(host,port,filename)
  elif command == "skrifa":
    write(host,port,filename)
  else:
    print "the program only supports \
           the commands lesa and skrifa"

if __name__ == "__main__":
   main()
