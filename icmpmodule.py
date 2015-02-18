#!/usr/bin/python

import socket
import struct
from twisted.internet import reactor

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0


class icmpTransportHandler(object):

	def __init__(self, reactor, options, host):
		from stringbuffer import stringBuffer
		self.queue = stringBuffer() 
		self.reactor = reactor
		self.options = options
		self.host = socket.gethostbyname(host)
		self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
		self.reactor.addReader(self)

	def pingLoopInit(self):
		self.timeout = self.reactor.callWhenRunning(self.pingLoop)

	def fileno(self):
		return self.s.fileno()

	def sendData(self, payload):
		self.queue.put(payload)

	def doRead(self):
		(rawPacket, address) = self.s.recvfrom(65535)
		payload = rawPacket[36:]

		if address[0] == None:
			self.host = address[0] 

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

	def pingLoopInit(self):
		from random import randrange
		packetId = randRange(9999)
		packetChecksum = 0
		header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, packetChecksum, packetId, 1)
		payload = self.queue.get(65507) # Max Packet 65535 - (IP Hdr) 20 - (ICMP Hdr) 8 = 65507
		packetChecksum = self.queue(header + payload)
		header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(packetChecksum), packetId, 1)
		packet = header + payload
		self.s.sendto(packet, (destination, 1))

		self.timeout = self.reactor.callLater(self.options.throttle, self.pingLoop)

'''
	def sendPacket(self, destination, payload):
		from random import randrange
		packetId = randrange(9999)

		packetChecksum = 0
		header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, packetChecksum, packetId, 1)
		packetChecksum = self.checksum(header + payload)
		header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(packetChecksum), packetId, 1)
		packet = header + payload

		self.s.sendto(packet, (destination, 1))
'''
