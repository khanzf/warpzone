#!/usr/bin/python

from StringIO import StringIO
from twisted.web.client import FileBodyProducer

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import protocol, reactor
from twisted.web.client import Agent, HTTPConnectionPool, readBody

from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.http_headers import Headers

from twisted.web.server import Site
from twisted.web.resource import Resource

from twisted.names import dns
from twisted.names.client import lookupText
from twisted.names import client

from random import randrange

import sys
import time
import base64
import socket

# Queue class used for protocols not designed for asynchronous communication
class asymQueue():
    # Assigns the interface and creates the Queue
    def __init__(self, iface):
        from stringbuffer import stringBuffer
        self.iface = iface
        self.queue = stringBuffer()

    # Data from the interface to the Queue, waiting polling
    def sendData(self, newPayload):
        self.queue.put(newPayload)

    # Data to be returned to the Tunnel after being polled 
    def readQueue(self, count = -1):
        payload = self.queue.get(count)
        return payload
        #self.iface.rawDataSent(payload)

# DNS Transport Client
class dnsClient():

    def __init__(self, reactor, iface, options):
        from twisted.names.client import createResolver
        from stringbuffer import stringBuffer
        self.reactor = reactor
        self.options = options 
        self.iface = iface
        self.resolver = createResolver()
        self.mtu = (( 240 - 2 - options.endpoint.__len__() ) / 4) * 4
#        self.mtu = 240 - (((options.endpoint.__len__() + 2)/4)*4)
        self.queue = stringBuffer()

    def requestLoopInit(self):
        self.timeout = self.reactor.callWhenRunning(self.requestLoop)

    def dnsError(self, failure):
        print "Error"
        print failure
        print failure.getErrorMessage()
        reactor.stop()

    def printResult(self, a):
        answers, auth, addition = a
#        print answers[0].payload.data[0]
        payloadEncoded = answers[0].payload.data[0][2:]
        payload = base64.b64decode(payloadEncoded)
        self.iface.rawDataSent(payload)

    def sendData(self, payload):
        self.queue.put(payload)
#        self.timeout.cancel()
#        self.requestLoop(payload)

    def requestLoop(self):

        payload = self.queue.get( (self.mtu / 4) * 3 )
        encodedRequest = self.dnsModulate(payload)
        d = self.resolver.lookupText(encodedRequest).addCallback(self.printResult)
        d.addErrback(self.dnsError)

        self.timeout = reactor.callLater(self.options.throttle, self.requestLoop)

    def dnsModulate(self, payload):
        from string import ascii_letters, digits
        from random import choice

        fixedLength = self.options.endpoint.__len__() + 2
        encodedPayload = base64.b64encode(payload)
        encodedLength = encodedPayload.__len__()
        random = ''
        for x in range(0, 3):
            random += choice(ascii_letters + digits)

        encodedRequest = random
        if encodedLength > 60:
            octetone = encodedPayload[0:60]
            encodedRequest += octetone
            if encodedLength > 120:
                octettwo = encodedPayload[60:120]
                encodedRequest += '.' + octettwo
                if encodedLength > 180:
                    octetthree = encodedPayload[120:180]
                    encodedRequest += '.' + octetthree
                    if encodedLength > (240 - fixedLength):
                        octetfour = encodedPayload[180: self.mtu]
                    else:
                        if encodedPayload[180:] != '':
                            octetfour = encodedPayload[180:]
                            encodedRequest += '.' + octetfour
                else:
                    if encodedPayload[120:] != '':
                        octetthree = encodedPayload[120:]
                        encodedRequest += '.' + octetthree
            else:
                if encodedPayload[60:] != '':
                    octettwo = encodedPayload[60:]
                    encodedRequest += '.' + octettwo
        else:
            octetone = encodedPayload
            encodedRequest += octetone

        encodedRequest += '.' + self.options.endpoint
        return encodedRequest

# DNS Transport Server
class dnsServer(object):
    def __init__(self, iface, options):
        from stringbuffer import stringBuffer
        self.iface = iface
        self.options = options
        self.domainLength = self.options.endpoint.__len__()
        self.duplicate = ''
        self.queue = stringBuffer()
        self.mtu = 240 - (((options.endpoint.__len__() + 2)/4)*4)
        print "MTU is", self.mtu

    def decodeRequest(self, queried):
        queryLength = queried.__len__()
        payloadEncoded = queried[3:queryLength - (self.domainLength+1)]
        minusPeriods = payloadEncoded.replace('.', '')
        payload = base64.b64decode(minusPeriods)
        return payload 

    def encodeResponse(self):
        payload = self.queue.get(((self.mtu / 4) * 3))
        payloadEncoded = base64.b64encode(payload)
        rfc1035 = "r=" + payloadEncoded
        return rfc1035 

    def sendData(self, payload):
        self.queue.put(payload)

    def query(self, query, timeout=None):
        queried = query.name.name

        if queried[:4] == self.duplicate:
            return [], [], []
        self.duplicate = queried[:4]

        payload = self.decodeRequest(queried)

        if payload != '':
            self.iface.rawDataSent(payload)

        response = self.encodeResponse()

        answers = []
        authority = []
        additional = []

#        answer = dns.RRHeader(
#            name = queried,
#            payload = dns.Record_A(address=b'1.2.3.4')
#        )
#        answers.append(answer)

        answer = dns.RRHeader(
            name = queried,
            type = dns.TXT,
            ttl = 1,
            payload = dns.Record_TXT(response)
        )
        answers.append(answer)

        return answers, authority, additional

# Escape out Base64 to URL
def base64_to_cgi(original):
    original = original.replace('/', '%2F')
    original = original.replace('+', '%2B')
    return original

def cgi_to_base64(original):
    original = original.replace('%2F', '/')
    original = original.replace('%2B', '+')
    return original

# HTTP Server Code
class httpServe(Resource):

    def __init__(self, iface, dataQueue):
        self.iface = iface
        self.dataQueue = dataQueue
    # Nothing happens here, because data is gathered from the Queue
    def sendData(self, rawData):
        pass
    # A generic response to a GET request
    def render_GET(self, request):
        return "Danger! Danger Will Robinson!"
    # Request to a proper POST request
    def render_POST(self, request):
        # Capture the received POST data in the p variable
        try:
            receiveData =  base64.b64decode( cgi_to_base64( request.args["p"][0]))
        except TypeError as e:
            print "@@@@@@@@@@@ The error is:", e
            print request.args["p"][0]
        # If the request is empty, nothing to send to the interface
        if receiveData != '':
            self.iface.rawDataSent( receiveData )
        # Dump the contents of the Queue
        return base64_to_cgi(base64.b64encode( self.dataQueue.readQueue() ))

# HTTP Transport Layer
class httpHandler():
    def __init__(self, reactor, iface, options):

        self.reactor = reactor
        pool = HTTPConnectionPool(self.reactor)
        self.agent = Agent(self.reactor, pool=pool, connectTimeout=5)
        self.iface = iface
        self.options = options

    def http_init(self): #Initialize the requests, immediately jump to sendReceiveData()
        reactor.callLater(0, self.sendReceiveData, '')

    # Send data from the interface to the transport
    def sendData(self, rawData):
        self.timeout.cancel()                # Cancel all previous callbacks
        self.sendReceiveData(rawData)        # Send the raw data over

    # Performs both submissions of data and requests back
    def sendReceiveData(self, rawPostData):

        # Encodes data that was sent over as a POST request parameter
        body = FileBodyProducer(StringIO('p='+ base64_to_cgi(base64.b64encode(rawPostData) )))
        # Builds the request
        r = self.agent.request(
            'POST',
            'http://' + self.options.endpoint + ':' + str(self.options.port) + '/warpzone',
                Headers({'Content-Type' : ['application/x-www-form-urlencoded'],
                            'Connection'    : ['keep-alive']
                          }),
            body)
        # Sets up the request
        r.addCallback(self.cbRequest)
        # If there is an error, go here
        r.addErrback(self.cbError)
        # Performs the automatic callback
        self.timeout = reactor.callLater(self.options.throttle, self.sendReceiveData, '' )

    def cbError(self, failure): # An error occurred
        print "Client connection failure, exiting."
        print failure
        reactor.stop()

    def cbRequest(self, response): # Gets back the request data
        d = readBody(response)
        d.addCallback(self.cbBody)
        d.addErrback(self.cbError)
        return d

    def cbBody(self, body): # Gets back the body of the request
        if body != '':
            self.iface.rawDataSent(base64.b64decode(cgi_to_base64(body)))

# TCP Transport Layer
from twisted.internet.protocol import Protocol, ClientFactory
class tcpTransportHandler(Protocol):

    def __init__(self, iface, reactor):
        from stringbuffer import stringBuffer
        self.iface = iface
        self.reactor = reactor
        self.connection = False
        self.queue = stringBuffer()

    # Received data from the Tunnel, sends it to Interface
    def dataReceived(self, data):
        self.iface.rawDataSent(data)

    # Received data from the Interface, sends it to the Tunnel
    def sendData(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        self.reactor.stop()

    def connectionMade(self):
        self.connection = True
        storedData = self.queue.get()
        self.sendData(storedData)

class tcpTransportFactory(ClientFactory):

    # Receives Assigns the TCP Protocol
    def buildProtocol(self, addr):
        return self.protocol

    def __init__(self, iface, reactor):
        self.iface = iface
        self.reactor = reactor
        self.protocol = tcpTransportHandler(self.iface, self.reactor)

    # Received data from the interface, sending it to the Tunnel
    def sendData(self, data):
        if self.protocol.connection == True:
            self.protocol.sendData(data)
        elif self.protocol.connection == False:
            self.protocol.queue.put(data)

# UDP Transport Handler
class udpTransportHandler(DatagramProtocol):
    def __init__(self, iface, reactor, host, port):
        from stringbuffer import stringBuffer
        from socket import gethostbyname

        self.reactor = reactor
        self.iface = iface
        self.port = port 
        if host == None: # We are the server
            self.queue = stringBuffer()
            self.host = None # It was none anyways 
        else: # We are the client
            self.host = gethostbyname(host)

    def startProtocol(self):
        if self.host != None:
            self.transport.connect(self.host, self.port)

    def datagramReceived(self, data, (host, port)):
        if self.host == None:
            self.host = host
            self.port = port
            storedData = self.queue.get()
            if storedData != '':
                self.transport.write(storedData, (self.host, self.port) )
        self.iface.rawDataSent(data)

    def sendData(self, data):
        if self.host != None:
            self.transport.write(data, (self.host, self.port) )
        else:
            self.queue.put(data)

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

class icmpTransportHandler(object):

    def __init__(self, iface, reactor, options):
        from stringbuffer import stringBuffer
        self.iface = iface
        self.queue = stringBuffer() 
        self.reactor = reactor
        self.options = options
        if options.endpoint:
            self.host = socket.gethostbyname(options.endpoint)
        else:
            self.host = None
        self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        self.reactor.addReader(self)
        self.sequence = 1

        if options.client: # Client sends the requests
            self.packetType = ICMP_ECHO_REQUEST
            self.identifier = randrange(65535)
        else: # Server sends back replies
            self.packetType = ICMP_ECHO_REPLY
            self.identifier = None

    def pingLoopInit(self):
        self.timeout = self.reactor.callWhenRunning(self.pingLoop, 1 )

    def fileno(self):
        return self.s.fileno()

    def sendData(self, payload):
        self.queue.put(payload)

    def doRead(self):
        import struct
        (rawPacket, address) = self.s.recvfrom(65535)
        icmpHeader = rawPacket[20:28]
        icmptype, code, checksum, identifier, sequence = struct.unpack("bbHHh", icmpHeader) 

        if icmptype != self.packetType:
            payload = rawPacket[28:]
            self.iface.rawDataSent(payload)

            if self.options.server:
                if self.host == None:
                    self.host = socket.gethostbyname(address[0])
                    self.identifier = identifier
                payload = self.queue.get(65507) # 65535-IP Hdr-ICMP Hdr=65507
                self.sendPacket(payload, sequence)

    def logPrefix(self):
        return "icmp"

    def connectionLost(self, reason):
        print "Socket died"
        self.reactor.stop()

    def checksum(self, source):
        csum = 0
        countTo = (len(source) / 2) * 2
        count = 0
        while count < countTo:
            thisVal = ord(source[count + 1]) * 256 + ord(source[count])
            csum = csum + thisVal
            csum = csum & 0xffffffffL
            count = count + 2
        if countTo < len(source):
            csum = csum + ord(source[len(source) - 1])
            csum = csum & 0xffffffffL
        csum = (csum >> 16) + (csum & 0xffff)
        csum = csum + (csum >> 16)
        answer = ~csum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return answer

    def pingLoop(self, sequence):
        payload = self.queue.get(65507)
        self.sendPacket(payload, sequence)
        self.sequence += 1
        self.timeout = self.reactor.callLater(self.options.throttle, self.pingLoop, self.sequence)

    def sendPacket(self, payload, sequence):
        from struct import pack
        packetChecksum = 0
        header = pack("bbHHh", self.packetType, 0, packetChecksum, self.identifier, 1)
        packetChecksum = self.checksum(header + payload)
        header = pack("bbHHh", self.packetType, 0, socket.htons(packetChecksum), self.identifier, 1)
        packet = header + payload
        self.s.sendto(packet, (self.host, 1))

