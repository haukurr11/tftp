#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket
from struct import pack,unpack

BLOCK_SIZE = 512
MAX_RETRIES = 5
CONNECTION_TIMEOUT = 10

class TooManyRetries(Exception):
    pass

class ErrorPacket(Exception):
    pass

class IllegalOperationReceived(Exception):
    pass

class UnknownRequest(Exception):
    pass

class WrongBlock(Exception):
    pass

def udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(CONNECTION_TIMEOUT)
    return sock

def req_header(rtype,filename,mode="octet"):
    if rtype == "RRQ":
        statuscode = 1
    elif rtype == "WRQ":
        statuscode = 2
    else:
        raise UnknownRequest("UNKNOWN REQUEST TYPE: " + rtype)
    header_pattern = "!H%dsB%dsB" % (len(filename),len(mode))
    return pack(header_pattern,statuscode,filename,0,mode,0)

def get_opcode(p):
    return unpack("!H", p[0:2])[0]

def datapacket(block,data):
    return pack("!2H", 3, block) + data

def datapacket_split(p):
    return unpack("!2H", p[0:4]) + (p[4:],)

def errorpacket(errno,errmsg):
    error_pattern = "!2H%dsB" % len(errmsg)
    return pack(error_pattern, 5, errno, errmsg, 0)

def errorpacket_split(p):
    return unpack("!2H",p[0:4]) + (p[4:-1],)

def ackpacket(blocknum):
    return pack("!2H", 4, blocknum)

def ackpacket_split(p):
    return unpack("!2H",p[0:4])

def write(host,port,filename):
    sock = udp_socket()
    opacket = req_header("WRQ",filename)
    sock.sendto(opacket, (host,port) )
    try:
        sending_file = open(filename,"rb+")
    except IOError:
        sock.sendto(errorpacket(2,"Access violation"), (host,port) )
        raise
    retries = 0
    blocknum = 1
    while retries < MAX_RETRIES:
        try:
            rpacket, rsock = sock.recvfrom(BLOCK_SIZE+4)
            retries = 0
        except socket.timeout:
            retries += 1
            continue
        opcode = get_opcode(rpacket)
        if opcode == 5: #ERROR PACKET
            errorcode,errmsg = errorpacket_split(rpacket)[1:]
            raise ErrorPacket(
                ("ERROR(%d): " % errorcode) + errmsg)
        elif opcode == 4: #ACK PACKET
            rblocknum = ackpacket_split(rpacket)[1]
            if rblocknum+1 == blocknum:
                try:
                    data = sending_file.read(BLOCK_SIZE)
                except IOError:
                    sock.sendto(
                        errorpacket(2,"Access violation"),rsock)
                    raise
                dpacket = datapacket(blocknum,data)
                sock.sendto(dpacket,rsock)
                print "packet %d sent, size: %d bytes" \
                    % (blocknum,len(data))
                blocknum += 1
                if len(dpacket) < BLOCK_SIZE+4:
                    sock.sendto(dpacket,rsock)
                    sending_file.close()
                    print "SUCCESS: the file " \
                        + filename + " has been sent"
                    return
            else:
                received_file.close()
                raise WrongBlock("Wrong block requested: expected %d but got %d" \
                % (blocknum,rblocknum+1))
        else:
            sock.sendto(
                errorpacket(4,"Illegal TFTP Operation",rsock))
            received_file.close()
            raise IllegalOperationReceived("Unexpected Opcode")
    received_file.close()
    raise TooManyRetries(
        "Failed after %d retries" % MAX_RETRIES)

def read(host,port,filename):
    sock = udp_socket()
    opacket = req_header("RRQ",filename)
    sock.sendto(opacket, (host,port) )
    try:
        received_file = open(filename,"wb+")
    except IOError:
        sock.sendto(errorpacket(2,"Access violation"), (host,port) )
        raise
    retries = 0
    blocknum = 1
    while retries < MAX_RETRIES:
        try:
            rpacket, rsock = sock.recvfrom(BLOCK_SIZE+4)
            retries = 0
        except socket.timeout:
            retries += 1
            continue
        opcode = get_opcode(rpacket)
        if opcode == 5: #ERROR PACKET
            errorcode,errmsg = errorpacket_split(rpacket)[1:]
            raise ErrorPacket( 
                ("ERROR(%d): " % errorcode) + errmsg)
        elif opcode == 3: #DATA PACKET
            rblocknum,data = datapacket_split(rpacket)[1:]
            if blocknum == rblocknum:
                sock.sendto( ackpacket(blocknum), rsock)
                try:
                    received_file.write(data)
                    print "packet %d received, size: %d bytes" \
                        % (rblocknum,len(data))
                except IOError:
                    sock.sendto(
                        errorpacket(3,
                            "Disk full or allocation exceeded"),rsock)
                    received_file.close()
                    raise
                blocknum += 1
                if len(rpacket) < BLOCK_SIZE+4:
                    received_file.close()
                    print "SUCCESS: the file " \
                        + filename + " has been received"
                    return
            else:
                received_file.close()
                raise WrongBlock("Wrong block received: expected %d but got %d" \
                % (blocknum,rblocknum))
        else:
            sock.sendto(
                errorpacket(4,"Illegal TFTP Operation",rsock))
            received_file.close()
            raise IllegalOperationReceived("Unexpected Opcode")
    raise TooManyRetries(
        "Failed after %d retries" % MAX_RETRIES)

def main():
    if len(sys.argv) != 4 and len(sys.argv) != 5:
        print "The program takes 3-4 arguments:" \
            +" servername, command,filename and port(optional)"
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
