from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import protocol
import sys

def client_init(options, reactor):

	import transports
#	from twisted.internet import reactor

	# Start the interfaces part
	if (options.interface == 'stdio'):
		import interfaces
		iface = interfaces.stdiface()
		stdio.StandardIO(iface)
	elif (options.interface == 'tun'):
		import interfaces
		iface = interfaces.tuniface(reactor)
	elif (options.interface == 'socks5'):
		import socks5
		iface = socks5.buildSocksProxy(reactor)
		reactor.listenTCP(8888, iface )
	else:
		print "Currently not supported. Exiting"
		sys.exit(0)

#	import transports

#	from twisted.internet import reactor
	if options.transport == 'tcp':
		transportLayer = transports.tcpTransportFactory(iface, reactor)
		iface.getTransport(transportLayer)
		reactor.connectTCP(options.endpoint,
									options.port,
									transportLayer)
	elif options.transport == 'http':
		transportLayer = transports.httpHandler(reactor,
															iface,
															options)
		iface.getTransport(transportLayer)
		reactor.callWhenRunning( transportLayer.http_init )
	elif options.transport == 'dns':
		transportLayer = transports.dnsClient(reactor, iface, options)
		iface.getTransport(transportLayer)
		reactor.callWhenRunning( transportLayer.requestLoopInit )
	elif options.transport == 'udp':
		transportLayer = transports.udpTransportHandler(iface, reactor, options.endpoint, options.port)
		iface.getTransport(transportLayer)
		reactor.listenUDP(0, transportLayer)
	elif options.transport == 'icmp':
		transportLayer = transports.icmpTransportHandler(iface, reactor, options)
		iface.getTransport(transportLayer)
		reactor.callWhenRunning( transportLayer.pingLoopInit )
	else:
		print "Bad transport layer selected"
		sys.exit(0)


#	reactor.addSystemEventTrigger("before", "shutdown", cleanupFunction, reactor)
#	reactor.run()

