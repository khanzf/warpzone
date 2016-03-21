#!/usr/bin/python

#import getopt
import sys, select
import interfaces
import os, sys

# The main function
def main():

    options = options_parse()

    from twisted.internet import reactor

    try:
        if options.client: # The Client code
            import client
            client.client_init(options, reactor)
        elif options.server: # The Server code
            from twisted.internet.error import CannotListenError
            import server
            server.server_init(options, reactor)

        reactor.run()

    except KeyboardInterrupt:
        print "Interrupted by Control-C. Exiting."

def options_parse():
    interface_types = ['stdio', 'tun', 'socks5']
    transport_types = ['tcp', 'http', 'dns', 'udp', 'icmp']
    usage = "usage: %prog [-c or -s] [-i interface] [-t transport] [-e hostname/IP] [-p port] [...]"
    version = "Warpzone 0.1"

    from optparse import OptionParser
    from optparse import OptionGroup

    parser = OptionParser(usage=usage, version=version)
    parser.add_option("-c", "--client", dest="client", action="store_true", help="Run as client", default=False)
    parser.add_option("-s", "--server", dest="server", action="store_true", help="Run as server", default=False)
    parser.add_option("-i", "--interface", dest="interface", type="string", help="Interface: stdio / tun")
    parser.add_option("-t", "--transport", dest="transport", type="string", help="Transport layer")
    parser.add_option("-e", "--endpoint", dest="endpoint", type="string", help="Endpoint IP or Hostname")
    parser.add_option("-p", "--port", dest="port", type="int", help="Port between 1 and 65535")

    group = OptionGroup(parser, "Tuning Options")
    group.add_option("-w", "--throttle", dest="throttle", type="float", help="Speed (Default is 0.1)", default=0.1)
    group.add_option("-f", "--fullduplex", dest="fullduplex", action="store_true", help="Run in full duplex mode (Currently not implemented)", default=False)
    group.add_option("-m", "--mode", dest="mode", type="string", help="Specifies the mode of the protocol")
    parser.add_option_group(group)

    (options, args) = parser.parse_args()

    # Validate the mode of the program 
    if options.client and options.server:
        parser.error("Client [-c] and Server [-s] are mutually exclusive")
    if not options.client and not options.server:
        parser.error("Client [-c] or Server [-s] are required")

    # Validate the interface type
    if options.interface == None:
        parser.error("Failed to set interface [-i] type")
    if options.interface not in interface_types:
        parser.error("Interface type is invalid")

    # Validate the Transport Settings
    if options.transport == None:
        parser.error("Failed to set transports [-t] type")
    if options.transport not in transport_types:
        parser.error("Transport type is invalid")

    # Validate the Endpoint - Only needed if client
    if options.client and not options.endpoint:
        parser.error("Client requires and endpoint [-e]")

    # Validate the port if its a TCP connection
    if options.port==None and (options.transport == 'tcp' or options.transport == 'http' or options.transport == 'udp'):
        parser.error("TCP and HTTP require that a port [-p] is defined")

    # Validate Server settings
    if options.transport=='dns' and options.port:
        parser.error("DNS should not have a port")

    if options.transport=='dns' and not options.endpoint:
        parser.error("DNS requires an endpoint")

    # TCP and HTTP do not need an endpoint
    if options.server and options.endpoint and (options.transport == 'tcp' or options.transport == 'http' or options.transport == 'udp'):
        parser.error("TCP and HTTP as server do not require an endpoint [-e]")

    # Must be a valid port
    if options.port!=None and (options.port > 65536 or options.port < 0):
        parser.error("Port must be between 1 and 655356")

    if options.fullduplex:
        parser.error("Full Duplex currently not implemented")

    return options

# Jump to main because C is awesome :-)
if __name__ == "__main__":
    main()
