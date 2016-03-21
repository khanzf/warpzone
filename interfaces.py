#!/usr/bin/python

from twisted.internet import stdio
from twisted.protocols import basic

# For stdiface
#import sys

# For Tun interface
#import os, sys
from socket import *
from select import select
import getopt, struct
import os, sys

class stdiface(basic.LineReceiver):
    from os import linesep as delimiter

    def assignAddress(self, address):
        self.address = address
    def getTransport(self, transportLayer):
        self.transportLayer = transportLayer
    def connectionMade(self):
        self.setRawMode()
    def rawDataReceived(self, line):
        self.transportLayer.sendData(line)
    def rawDataSent(self, data):
        sys.stdout.write(data)
        sys.stdout.flush()

class tuniface(object):
    # This function is used to create a warp interface, which is just a tun interface
    # Twisted's Tuntap interface is broken
    def __init__(self, reactor):

        from fcntl import ioctl # Needed to configure /dev/net/tun
        
        self.reactor = reactor # Set the reactor

        # Stolen from standard code on opening a tun interface
        TUNSETIFF = 0x400454ca
        TUNMODE = 0x0001

        try:
            # Opens the /dev/net/tun interface
            self.tun = os.open("/dev/net/tun", os.O_RDWR)
            # Set its mode, assign it name as warp0
            self.ifs = ioctl(self.tun, TUNSETIFF, struct.pack("16sH", "warp%d", TUNMODE))
            # Remove the extraneous \x00's
            self.ifname = self.ifs[:16].strip("\x00")
        except IOError as e:
            print "Unable to create tun interface. Are you running as root?"
            sys.exit(1)

        self.reactor.addReader(self) # add this newly opened object to the reactor's reader block

        print "Assigned device %s. Assign it an IP address" % self.ifname
        print "You will need to adjust the MTU"

    def fileno(self): # Return the file descriptor, as required by the addReader handler
        return self.tun

    def connectionLost(self, reason): 
        self.reactor.removeReader(self)        # Remove the reader from the reactor
        os.close(self.tun)                        # Close the Tunnel interface

    def doRead(self): # Read data from the warp interface, send it to the tunnel
        data = os.read(self.tun, 1500)
        self.transportLayer.sendData(data)

    def logPrefix(self): # I genuinely do not know the purpose of this
        pass

    # Set the transport Layer
    def getTransport(self, transportLayer):
        self.transportLayer = transportLayer

    # Received raw data, send it to the transport Layer
    def rawDataReceived(self, line):
        self.transportLayer.sendData(line)

    # Write data to the tunnel interface, only write if the data isn't blank
    def rawDataSent(self, data):
        if data != '':
            os.write(self.tun, data)

