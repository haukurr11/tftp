#!/usr/bin/python
# -*- coding: utf-8 -*-
from sys import argv
import os
import socket
from struct import pack,unpack

BLOCK_SIZE = 512 #bytes
CONNECTION_TIMEOUT = 10 #seconds

OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_ERROR = 5

ERR_UNDEFINED = 0
ERR_NOTFOUND_= 1
ERR_ACCESS = 2
ERR_DISKFULL = 3
ERR_ILLEGAL = 4
ERR_TID = 5
ERR_EXISTS = 6
ERR_NOUSER = 7

class ErrorPacket(Exception):
    pass

class IllegalOperationReceived(Exception):
    pass

class UnknownRequest(Exception):
    pass

class WrongBlock(Exception):
    pass

class FileDoesNotExist(Exception):
    pass

def udp_socket():
    """
    Returns a socket that uses UDP
    @return: socket object that uses UDP
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(CONNECTION_TIMEOUT)
    return sock

def req_header(rtype,filename,mode="octet"):
    """
    Returns a TFTP request header to be sent
    to a server. can be either write(WRQ) or read(RRQ).
    @type  rtype: string
    @param rtype: type of request (WRQ or RRQ)
    @type  filename: string
    @param filename: name of file to send/receive
    @type  mode: string
    @param mode: transfer type(optional,default octet)
    @return: a binary packed header to be sent to a socket
    """
    if rtype == "RRQ":
        statuscode = 1
    elif rtype == "WRQ":
        statuscode = 2
    else:
        raise UnknownRequest("UNKNOWN REQUEST TYPE: " + rtype)
    #pattern : shortint(opnum),string(filename),0byte,string(mode),0byte
    header_pattern = "!H%dsB%dsB" % (len(filename),len(mode))
    return pack(header_pattern,statuscode,filename,0,mode,0)


def opcode(p):
    """
    Returns a TFTP request header to be sent
    to a server. can be either write(WRQ) or read(RRQ).
    @type  p: struct 
    @param p: a packet using the TFTP standard
    @return: opcode from the response header
    """
    return unpack("!H", p[0:2])[0]

def datapacket(blocknum,data):
    """
    Returns a DATA packet using the TFTP standard
    @type  blocknum: int
    @param blocknum: number of block being sent
    @return: data packet using the TFTP standard
    """
    #pattern : shortint(opnum),shortint(blockno),bytes(data)
    return pack("!2H", 3, blocknum) + data

def datapacket_split(p):
    """
    Returns a tuple containing each part of 
    a DATA packet using the TFTP standard
    @type  p: struct
    @param p: a DATA packet using the TFTP standard
    @return: a tuple with each part of a data packet in order of the standard.
    """
    return unpack("!2H", p[0:4]) + (p[4:],)

def errorpacket(errno,errmsg):
    """
    Returns an error packet using the TFTP standard
    @type  errno: int
    @param errno: a DATA packet using the TFTP standard
    @return: a tuple with each part of a data packet in order of the standard.
    """
    #pattern : shortint(opnum),shortint(errno),string(errmsg),0byte
    error_pattern = "!2H%dsB" % len(errmsg)
    return pack(error_pattern, 5, errno, errmsg, 0)

def errorpacket_split(p):
    """
    Returns a tuple containing each part of 
    a error packet using the TFTP standard
    @type  p: struct
    @param p: an error packet using the TFTP standard
    @return: a tuple with each part of an error packet in order of the standard
    """
    return unpack("!2H",p[0:4]) + (p[4:-1],0)

def ackpacket(blocknum):
    """
    Returns a tuple containing each part of 
    a error packet using the TFTP standard
    @type  p: struct
    @param p: an error packet using the TFTP standard
    @return: a tuple with each part of an error packet in order of the standard
    """
    #pattern: shortint(opcode),shortint(blocknum)
    return pack("!2H", 4, blocknum)

def ackpacket_split(p):
    """
    Returns a tuple containing each part of
    an acknowledgement(ACK) packet using the TFTP standard
    @type  p: struct
    @param p: an error packet using the TFTP standard
    @return: a tuple with each part of an error packet in order of the standard
    """
    return unpack("!2H",p[0:4])

def write(host,port,filename):
    """
    Writes a file to an TFTP server
    @type  host: string
    @param host: hostname or ip
    @type  port: int
    @param port: server port
    @type  filename: string
    @param filename: name of a file to write(has to exist on disk)
    """
    if not os.path.isfile(filename):
      raise FileDoesNotExist("No such file: " + filename)
    sock = udp_socket()
    header = req_header("WRQ",filename) #WRQ header
    sock.sendto(header, (host,port) )
    try:
        sending_file = open(filename,"rb+")
    except IOError:
        sock.sendto(errorpacket(ERR_ACCESS,"Access violation"), (host,port) )
        raise
    blocknum = 1 #number of block being written
    req_port = -1 #port to receive from host
    while True:
        try:
            rpacket, rsock_addr = sock.recvfrom(BLOCK_SIZE+4)
            packet_port = rsock_addr[1]
            if blocknum == 1:
               req_port = packet_port
        except socket.timeout:
            print("Server timed out, reconnecting...")
            continue
        if packet_port == req_port: #ignore packets from other ports
            if opcode(rpacket) == OPCODE_ERROR: #ERROR PACKET
                errorcode,errmsg = errorpacket_split(rpacket)[1:-1]
                raise ErrorPacket(
                    ("ERROR(%d): " % errorcode) + errmsg)
            if opcode(rpacket) == OPCODE_ACK: #ACK PACKET
                rblocknum = ackpacket_split(rpacket)[1]
                if rblocknum+1 == blocknum:
                    try:
                        data = sending_file.read(BLOCK_SIZE)
                    except IOError:
                        sock.sendto(
                            errorpacket(ERR_ACCESS,"Access violation"),rsock_addr)
                        raise
                    dpacket = datapacket(blocknum,data)
                    sock.sendto(dpacket,rsock_addr)
                    print("packet %d sent, size: %d bytes" \
                        % (blocknum,len(data)))
                    blocknum += 1
                    if len(dpacket) < BLOCK_SIZE+4: #last block
                        sock.sendto(dpacket,rsock_addr)
                        sending_file.close()
                        print("SUCCESS: the file " \
                            + filename + " has been sent")
                        return
                else:
                    msg = "Wrong block requested: expected %d but got %d" \
                          % (blocknum,rblocknum+1)
                    sock.sendto(
                        errorpacket(ERR_ILLEGAL,msg,rsock_addr))
                    received_file.close()
                    raise WrongBlock(msg)
            else: #unkown operation received
                sock.sendto(
                    errorpacket(ERR_ILLEGAL,"Illegal TFTP Operation",rsock_addr))
                received_file.close()
                raise IllegalOperationReceived("Unexpected Opcode")
    received_file.close()

def read(host,port,filename):
    """
    Reads a file from an TFTP server to a file
    @type  host: string
    @param host: hostname or ip
    @type  port: int
    @param port: server port
    @type  filename: string
    @param filename: name of a file to read(has to exist on server)
    """
    sock = udp_socket()
    header = req_header("RRQ",filename)
    sock.sendto(header, (host,port) )
    try:
        received_file = open(filename,"wb+")
    except IOError:
        sock.sendto(errorpacket(ERR_ACCESS,"Access violation"), (host,port) )
        raise
    blocknum = 1 #number of block being requested
    req_port = -1 #port to receive from host
    while True:
        try:
            rpacket, rsock_addr = sock.recvfrom(BLOCK_SIZE+4)
            packet_port = rsock_addr[1]
            if blocknum == 1:
               req_port = packet_port
        except socket.timeout:
            print("Server timed out, reconnecting...")
            continue
        if packet_port == req_port: #ignore packets from other ports
            if opcode(rpacket) == OPCODE_ERROR: #ERROR PACKET
                errorcode,errmsg = errorpacket_split(rpacket)[1:-1]
                raise ErrorPacket(
                    ("ERROR(%d): " % errorcode) + errmsg)
            if opcode(rpacket) == OPCODE_DATA: #DATA PACKET
                rblocknum,data = datapacket_split(rpacket)[1:]
                if blocknum == rblocknum: #correct block received
                    sock.sendto( ackpacket(blocknum), rsock_addr)
                    try:
                        received_file.write(data)
                        print("packet %d received, size: %d bytes" \
                            % (rblocknum,len(data)))
                    except IOError:
                        sock.sendto(
                            errorpacket(ERR_DISKFULL,
                                "Disk full or allocation exceeded"),rsock_addr)
                        received_file.close()
                        raise
                    blocknum += 1
                    if len(rpacket) < BLOCK_SIZE+4: #last block
                        received_file.close()
                        print("SUCCESS: the file " \
                            + filename + " has been received")
                        return
                else:
                    msg = "Wrong block received: expected %d but got %d" \
                          % (blocknum,rblocknum)
                    sock.sendto(
                        errorpacket(ERR_ILLEGAL,msg,rsock_addr))
                    received_file.close()
                    raise WrongBlock(msg)
            else:
                sock.sendto(
                    errorpacket(ERR_ILLEGAL,"Illegal TFTP Operation",rsock_addr))
                received_file.close()
                raise IllegalOperationReceived("Unexpected Opcode")
    received_file.close()

def main():
    if len(argv) != 4 and len(argv) != 5:
        print("The program takes 3-4 arguments:" \
            +" servername, command,filename and port(optional)")
        return
    host = argv[1]
    command = argv[2]
    filename = argv[3]
    if len(argv)>4:
        try:
            port = int(argv[4])
        except ValueError:
            print("the port has to be an integer number")
            return
    else:
        port = 69
    if command == "lesa":
        read(host,port,filename)
    elif command == "skrifa":
        write(host,port,filename)
    else:
        print("the program only supports " \
              + "the commands lesa and skrifa")

if __name__ == "__main__":
   main()
