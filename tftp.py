#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket
from struct import pack,unpack

PACKET_SIZE = 516
MAX_RETRIES = 5

class TooManyRetriesException(Exception):
  pass

class ErrorPacketException(Exception):
  pass

class IllegalOperationReceived(Exception):
  pass

class UnknownRequest(Exception):
  pass

def udp_socket():
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.settimeout(10)
  return sock

def req_header(rtype,filename,mode="octet"):
  if rtype == "RRQ":
    statuscode = 1
  elif rtype == "WRQ":
    statuscode = 2
  else:
    raise UnknownRequest("UNKNOWN REQUEST TYPE: " + rtype)
  header_pattern = "!H%dsB5sB" % len(filename)
  return pack(header_pattern,statuscode,filename,0,mode,0)

def get_opcode(p):
  return unpack("!H", p[0:2])[0]

def datapacket_split(p):
  return unpack("!2H", p[0:4]) + (p[4:],)

def errorpacket_split(p):
  return unpack("!2H",p[0:4]) + (p[4:-1],)

def ackpacket(block):
  return pack("!2H", 4, block)

def errorpacket(errno,errmsg):
  error_pattern = "!2H%dsB" % len(errmsg)
  return pack(error_pattern, 5, errno, errmsg, 0)

def read(host,port,filename):
  sock = udp_socket()
  opacket = req_header("RRQ",filename)
  sock.sendto(opacket, (host,port) )
  try:
    received_file = open(filename,"wb+")
  except Exception:
    sock.sendto(errorpacket(2,"Access violation"), (host,port) )
    raise
  retries = 0
  while True:
    try:
      if retries >= MAX_RETRIES:
        raise TooManyRetriesException(
            "Failed after %d retries" % retries)
      rpacket, rsock = sock.recvfrom(PACKET_SIZE)
      retries = 0
    except socket.timeout:
      retries += 1
      sock.sendto(opacket, (host,port))
      continue
    opcode = get_opcode(rpacket)
    if opcode == 5: #ERROR PACKET
      errorcode,errmsg = errorpacket_split(rpacket)[1:]
      raise ErrorPacketException( 
                ("ERROR(%d): " % errorcode) + errmsg)
    elif opcode == 3: #DATA PACKET
      block,data = datapacket_split(rpacket)[1:]
      sock.sendto( ackpacket(block), rsock)
      try:
        received_file.write(data)
        print "packet %d received, size: %d bytes" \
              % (block,len(data))
      except IOError as e:
        sock.sendto(
            errorpacket(3,
                   "Disk full or allocation exceeded"),rsock)
        received_file.close()
        raise
      if len(rpacket) < PACKET_SIZE:
          received_file.close()
          print "SUCCESS: the file " \
                + filename + " has been received"
          return
    else:
        sock.sendto(
            errorpacket(4,"Illegal TFTP Operation",rsock))
        received_file.close()
        raise IllegalOperationReceived("Unexpected Opcode")

def main():
  if len(sys.argv) != 4 and len(sys.argv) != 5:
    print "The program takes 4 arguments:" \
          +" servername, command and port(optional)"
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
    print "the program only supports " \
        + "the commands lesa and skrifa"

if __name__ == "__main__":
   main()
