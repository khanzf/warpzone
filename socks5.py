from twisted.internet import protocol, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
import struct
import stringbuffer

import socket
import sys

import time

ip="0.0.0.0"
port=7777

VER="\x05"
METHOD="\x00"

SUCCESS="\x00"
SOCKFAIL="\x01"
NETWORKFAIL="\x02"
HOSTFAIL="\x04"
REFUSED="\x05"
TTLEXPIRED="\x06"
UNSUPPORTCMD="\x07"
ADDRTYPEUNSPPORT="\x08"
UNASSIGNED="\x09"


class ClientConnection(protocol.Protocol):
    def __init__(self):
        pass
    def connectionMade(self):
        pass
    def sendData(self, data):
        self.transport.write(data)

class SocksProxy(protocol.Protocol):
    def __init__(self, reactor):
        self.iver = None 
        self.rver = None 
        self.reactor = reactor

    def dataReceived(self, data):
        if not self.iver:
            print "Round one"
            self.iver,self.inmethods,self.imethods = struct.unpack("BBB", data)
            self.transport.write(VER+METHOD)
        elif not self.rver:
            print "Round two"
            addrlen = data.__len__() - 6
            unpackstring = "BBBB" + str(addrlen) + "s2s"
            self.rver,self.rcmd,self.rrsv,self.ratyp, self.rdst_addr, self.rdst_port = struct.unpack(unpackstring, data)

            if self.ratyp == 1: # IPv4
                print "@@@@@@@@@@@@@@@@@@@ IPv4 Value"
                self.endclient = '.'.join([chr(ord(i)) for i in self.rdst_addr])
            elif self.ratyp == 3: # Domain
                self.endclient = ''.join([chr(ord(i)) for i in self.rdst_addr])
                print "@@@@@@@@@@@@@@@@@@@ Domain Value", self.endclient
            else:
                print "@@@@@@@@@@@@@@@@@@@ Something weird happened"

            self.endport = ord(self.rdst_port[0])*256+ord(self.rdst_port[1])
#            print "A", type(self.endclient), "A", type(self.endport), "A"
            server_ip="".join([chr(int(i)) for i in ip.split(".")])
            responseTwo=VER+SUCCESS+'\x00'+'\x01'+server_ip+chr(8888/256)+chr(8888%256)
            self.transport.write(responseTwo)

            point = TCP4ClientEndpoint(reactor, self.endclient, self.endport)
            self.connection = ClientConnection()
            d = connectProtocol(point, self.connection) 

        else:
            print "We got this data:", ord(data[1])
            print data
            self.connection.sendData(data)


    def getTransport(self, transportLayer):
        self.transportLayer = transportLayer

class buildSocksProxy(protocol.Factory):
    def __init__(self, reactor):
        self.reactor = reactor
        self.SocksProxyServer = SocksProxy(reactor)

    def buildProtocol(self, addr):
        return self.SocksProxyServer 

    def getTransport(self, transportLayer):
        self.SocksProxyServer.getTransport(transportLayer)

        ver = newClient.recv(1)
        nmethods = newClient.recv(1)
        methods = newClient.recv(1)

        newClient.sendall(VER+METHOD)

        ver = newClient.recv(1)
        cmd = newClient.recv(1)
        rsv = newClient.recv(1) 
        atyp = newClient.recv(1)

        dst_addr=None
        dst_port=None

        if atyp=='\x01': # IPv4 Address
            dst_addr, dst_port=sock.recv(4), sock.recv(2)
            dst_address = ''.join([str(ord(i)) for i in dst_address])
        elif atyp=='\x03': # DNS
            addr_len = ord(newClient.recv(1))
            dst_addr,dst_port = newClient.recv(addr_len), newClient.recv(2)
            dst_address = ''.join([unichr(ord(i)) for i in dst_addr])
        elif atyp=='\x04': # IPv6 Address
            print "Let me come back to this. Currently no IPv6 support"
            newClient.close()

        print "Here 1"
        dst_port = ord(dst_port[0])*256+ord(dst_port[1])
        server_ip=''.join([chr(int(i)) for i in ip.split('.')])
        newClient.sendall(VER+SUCCESS+'\x00'+'\x01'+server_ip+chr(port/256)+chr(port%256))

        newSocksHandler(self.reactor, newClient, dst_address, dst_port)
        print "Kicked it off to the Connection Handler"

    def getTransport(self, transportLayer):
        self.transportLayer = transportLayer

    def fileno(self):
        return self.transformer.fileno()

    def logPrefix(self):
        return "socks5"

    def connectionLost(self, reason):
        print "SOCKS connection died"
        print reason.getErrorMessage()

    def sendData(self, payload):
        print "Right now, doing nothing with your data. Sorry!"
