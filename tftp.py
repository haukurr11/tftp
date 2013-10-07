#!/usr/bin/python
import sys
import os
import re


def read(host,port,filename):
  print "host " + host
  print "filename " + filename 
  print "port " + str(port)

def write(host,port,filename):
  if not os.path.isfile(filename):
     print "file not found"
     return
  print "host " + host
  print "filename " + filename 
  print "port " + str(port)

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
