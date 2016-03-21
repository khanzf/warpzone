from twisted.internet import stdio
from twisted.protocols import basic
#from twisted.internet import reactor, protocol
from twisted.internet import protocol

import sys

def server_init(options, reactor):

    import transports
#    from twisted.internet import reactor

    if (options.interface == 'stdio'):
        import interfaces
        iface = interfaces.stdiface()
        stdio.StandardIO(iface)

    elif (options.interface == 'tun'):
        import interfaces
        iface = interfaces.tuniface(reactor)
#        f, s = iface.ifaceSockets()

    else:
        print "Currently not supported. Exiting"
        sys.exit(0)

#    import transports

#    from twisted.internet import reactor
    if options.transport == 'tcp':
        transportLayer = transports.tcpTransportFactory(iface, reactor)
        iface.getTransport(transportLayer)
        reactor.listenTCP( options.port , transportLayer)
    elif options.transport == 'http':
        from twisted.web.resource import Resource
        from twisted.web.server import Site

        transportLayer = transports.asymQueue(iface)

        root = Resource()
        root.putChild("warpzone", transports.httpServe(iface, transportLayer) )
        site = Site(root)
        iface.getTransport(transportLayer)
        reactor.listenTCP(options.port, site)

    elif options.transport == 'dns':
        from twisted.names.server import DNSServerFactory
        from twisted.names import dns
        transportLayer = transports.dnsServer(iface, options)
        factory = DNSServerFactory( clients = [transportLayer] )
        protocol = dns.DNSDatagramProtocol(controller=factory)

        iface.getTransport(transportLayer)

        reactor.listenUDP(53, protocol)
        reactor.listenTCP(53, factory)
    elif options.transport == 'udp':
        transportLayer = transports.udpTransportHandler(iface, reactor, None, None)
        iface.getTransport(transportLayer)
        reactor.listenUDP(options.port, transportLayer)
    elif options.transport == 'icmp':
        transportLayer = transports.icmpTransportHandler(iface, reactor, options)
        iface.getTransport(transportLayer)

    else:
        print "Bad transport layer selected"
        sys.exit(0)

#    reactor.addSystemEventTrigger("before", "shutdown", cleanupFunction, reactor)
#    reactor.run()

