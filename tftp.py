#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket


def req_header(filename,opcode,mode):
  if opcode == "RRQ":
    codehex = "\x00\x01"
  elif opcode == "WRQ":
    codehex = "\x00\x02"
  return codehex + filename + "\x00" + mode + "\x00"

def read(host,port,filename):
  s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  s.connect((host, port))
  header = req_header(filename,"WRQ","octet")
  print header
  s.sendto(header,(host,port))

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
