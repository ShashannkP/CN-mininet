#!/usr/bin/python

"""
Mininet Topology for Dynamic Host Blocking System
Topology: Simple network with 4 hosts and 1 switch
"""

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    """
    Create network topology:
    
         h1
          |
    h2 - s1 - h3
          |
         h4
    
    h1: Normal host (10.0.0.1)
    h2: Normal host (10.0.0.2)
    h3: Attacker/Suspicious host (10.0.0.3) - will be blocked
    h4: Normal host (10.0.0.4)
    """
    
    info('\n*** Creating Dynamic Host Blocking Network ***\n')
    
    # Create Mininet network with remote controller
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info('*** Adding controller\n')
    # Remote controller (Ryu) at localhost:6653
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6653
    )
    
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    
    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')  # Attacker
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
    
    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)
    
    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])
    
    info('\n*** Network Configuration ***\n')
    info('Switch: s1\n')
    info('Hosts:\n')
    info('  h1: 10.0.0.1 (Normal Host)\n')
    info('  h2: 10.0.0.2 (Normal Host)\n')
    info('  h3: 10.0.0.3 (Attacker/Suspicious Host)\n')
    info('  h4: 10.0.0.4 (Normal Host)\n')
    info('\nController: Ryu (localhost:6653)\n')
    
    info('\n*** Testing basic connectivity ***\n')
    net.pingAll()
    
    info('\n*** Available commands:\n')
    info('  pingall          - Test connectivity between all hosts\n')
    info('  h1 ping h2       - Ping from h1 to h2\n')
    info('  h3 ping h1 -c 100 - Generate high traffic from h3 (will be blocked)\n')
    info('  xterm h1         - Open terminal on h1\n')
    info('  exit             - Exit Mininet\n\n')
    
    info('*** Running CLI\n')
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
