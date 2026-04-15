from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
import time

class DynamicHostBlocker(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DynamicHostBlocker, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        
        # Dictionary to store ping timestamps per MAC
        self.ping_history = {} 
        
        # Configuration for dynamic blocking
        self.MAX_PINGS = 10         # Max allowed pings within the TIME_WINDOW
        self.TIME_WINDOW = 1.0      # Time window in seconds
        
        # Keep track of blocked MACs
        self.blocked_macs = set()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry
        # We specify NO BUFFER to controller to ensure we get the whole packet
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Proactively send ALL ICMP traffic to the controller (Priority 50)
        # This prevents generic forwarding rules from bypassing the security check
        match_icmp = parser.OFPMatch(eth_type=0x0800, ip_proto=1)
        actions_icmp = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                               ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 50, match_icmp, actions_icmp)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, idle_timeout=idle_timeout,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, idle_timeout=idle_timeout, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
                              
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
            
        dst = eth.dst
        src = eth.src
        
        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        # Check for ICMP packet for malicious activity detection
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt.proto == ipv4.inet.IPPROTO_ICMP:
                icmp_pkt = pkt.get_protocol(icmp.icmp)
                if icmp_pkt:
                    # It is an ICMP packet
                    if src in self.blocked_macs:
                        # Already blocked, ignore packet_in (though flow rule should drop it)
                        # We might still get some inflight packets
                        return
                    
                    current_time = time.time()
                    
                    if src not in self.ping_history:
                        self.ping_history[src] = []
                    
                    self.ping_history[src].append(current_time)
                    
                    # Remove timestamps older than the exact window
                    self.ping_history[src] = [t for t in self.ping_history[src] 
                                              if current_time - t <= self.TIME_WINDOW]
                                              
                    # Check if threshold is breached
                    if len(self.ping_history[src]) > self.MAX_PINGS:
                        self.logger.warning("\n" + "="*50)
                        self.logger.warning("[ALERT] Suspicious activity! Ping flood detected from MAC %s", src)
                        self.logger.warning("[ACTION] Installing BLOCK rule for MAC %s with Priority 100", src)
                        self.logger.warning("="*50 + "\n")
                        
                        # Add high priority drop flow rule
                        match = parser.OFPMatch(eth_src=src)
                        # Empty actions list implies a DROP action in OpenFlow
                        self.add_flow(datapath, priority=100, match=match, actions=[])
                        
                        self.blocked_macs.add(src)
                        return # Drop this packet here by not forwarding

        # Learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            # Critical Logic: If it is an ICMP packet, DO NOT install a flow rule.
            # This ensures that ALL ICMP traffic is sent to the controller.
            # If we installed a rule, the switch would forward it directly without controller's knowledge,
            # and we wouldn't be able to detect the flood!
            is_icmp = False
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                 ip_pkt = pkt.get_protocol(ipv4.ipv4)
                 if ip_pkt.proto == ipv4.inet.IPPROTO_ICMP:
                      is_icmp = True
                      
            if not is_icmp:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src, eth_type=eth.ethertype)
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id, idle_timeout=10)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions, idle_timeout=10)
                    
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)