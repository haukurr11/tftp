#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket
import struct


def read(host,port,filename):
  clientsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  clientsocket.settimeout(5)
  pack_format = '!H' + str(len(filename)) + 'sB5sB'
  sendpacket = struct.pack(pack_format.encode(), 1, filename.encode(), 0, b'octet', 0)
  clientsocket.sendto(sendpacket, (host, port))
  totaldatalen = 0
  countblock = 1
  while True:
      retries = 0
      while retries < 3:
          try:
            data, remotesocket = clientsocket.recvfrom(512)
            opcode = struct.unpack('!H', data[0:2])[0]
            retries= 0
            break
          except:
            clientsocket.sendto(sendpacket, (host, port))
            opcode = 'Timeout'
            retries += 1
      if opcode == 3:
        blockno = struct.unpack('!H',data[2:4])[0]
        if blockno != countblock:
            clientsocket.sendto(errBlockNo, remotesocket)
            print('Receive wrong block. Session closed.')
            break
        countblock += 1
        payload = data[4:]
        totaldatalen += len(payload)
        sendpacket = struct.pack(b'!2H', 4, blockno)
        clientsocket.sendto(sendpacket, remotesocket)
        if len(payload) < 512:
            print('\rget %s :%s bytes. finish.' %(filename, totaldatalen))
            break
      elif opcode == 5:
        errString = data[4:-1]
        print('Received error code %s : %s' %(str(errCode), bytes.decode(errString)))
        break
      elif opcode == 'Timeout':
        print('Timeout. Session closed.')
        break
      else:
        print('Unknown error. Session closed.')
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
