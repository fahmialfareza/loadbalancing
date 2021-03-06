import random
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
import hashlib

def md5(key):
	return long(hashlib.md5(key).hexdigest(), 16)

class Skripsi(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Skripsi, self).__init__(*args, **kwargs)
        self.i = 1
        self.m = 2
        self.mac_to_port = {}
        self.serverlist = []  # Creating a list of servers
        self.virtual_ip = "10.0.1.100"  # IP dari virtual LB
        self.virtual_mac = "AB:BA:AB:BA:AB:BC"  # Mac dari virtual LB

        #list server
        self.serverlist.append({'ip': "10.0.0.1", 'mac': "00:00:00:00:00:01", "outport": "1"})
        self.serverlist.append({'ip': "10.0.0.2", 'mac': "00:00:00:00:00:02", "outport": "2"})
        self.serverlist.append({'ip': "10.0.0.3", 'mac': "00:00:00:00:00:03", "outport": "3"})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    # Fungsi dari arp
    def function_for_arp_reply(self, dst_ip, dst_mac):
        arp_mac = dst_mac
        # Making the load balancers IP and MAC as source IP and MAC
        src_ip = self.virtual_ip
        src_mac = self.virtual_mac

        arp_opcode = 2  # ARP opcode is 2 for ARP reply
        hardware_type = 1  # 1 indicates Ethernet ie 10Mb
        arp_protocol = 2048  # 2048 means IPv4 packet
        ether_protocol = 2054  # 2054 indicates ARP protocol
        len_mac = 6  # Indicates length of MAC in bytes
        len_ip = 4  # Indicates length of IP in bytes

        pkt = packet.Packet()
        ether_frame = ethernet.ethernet(dst_mac, src_mac,
						ether_protocol)  # Dealing with only layer 2

        arp_pkt = arp.arp(hardware_type, arp_protocol, len_mac, len_ip,
				arp_opcode, src_mac, src_ip,arp_mac, dst_ip)
				# Building the ARP reply packet, dealing with layer 3

        pkt.add_protocol(ether_frame)
        pkt.add_protocol(arp_pkt)
        pkt.serialize()
        return pkt

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        # print("Debugging purpose dpid", dpid)

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src

        self.mac_to_port.setdefault(dpid, {})

        self.mac_to_port[dpid][src] = in_port

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        # Jika ethernet frame type = 2054 mengindikasikan ARP packet..
        if eth.ethertype == ether.ETH_TYPE_ARP:
            arp_header = pkt.get_protocols(arp.arp)[0]

            # dan jika destination IP adalah virtual IP LB dan Opcode = 1 mengindikasikan ARP Request
            if arp_header.dst_ip == self.virtual_ip and arp_header.opcode == arp.ARP_REQUEST:
                # memanggil fungsi untuk membangun packet ARP reply dengan parameter MAC dan IP src
                reply_packet = self.function_for_arp_reply(
								arp_header.src_ip, arp_header.src_mac)

                actions = [parser.OFPActionOutput(in_port)]
                packet_out = parser.OFPPacketOut(datapath=datapath,
							in_port=ofproto.OFPP_ANY,
							data=reply_packet.data,actions=actions, buffer_id=0xffffffff)

                datapath.send_msg(packet_out)
                return
            else:
                self.mac_to_port.setdefault(dpid, {})

                # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

                # learn a mac address to avoid FLOOD next time.
                self.mac_to_port[dpid][src] = in_port

                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                else:
                    out_port = ofproto.OFPP_FLOOD

                actions = [parser.OFPActionOutput(out_port)]

                # install a flow to avoid packet_in next time
                if out_port != ofproto.OFPP_FLOOD:
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                    # verify if we have a valid buffer_id, if yes avoid to send both
                    # # flow_mod & packet_out
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match,
                                      actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 1, match, actions)
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath,
						buffer_id=msg.buffer_id,
						in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)
                return

        ip_header = pkt.get_protocols(ipv4.ipv4)[0]
        # print("IP_Header", ip_header)
        tcp_header = pkt.get_protocols(tcp.tcp)[0]
        # print("TCP_Header", tcp_header)

        if tcp_header.dst_port == 80:
			source_ip = ip_header.src
			arr_oktet = str(source_ip).split('.')
			binery1 = bin(int(arr_oktet[0])) [2:].zfill(8)
			binery2 = bin(int(arr_oktet[1])) [2:].zfill(8)
			binery3 = bin(int(arr_oktet[2])) [2:].zfill(8)
			binery4 = bin(int(arr_oktet[3])) [2:].zfill(8)

			# Hashing
			hashing = md5(binery1) + md5(binery2)+ md5(binery3)+ md5(binery4)
			mod = hashing % 3
			index = mod
			server_mac_selected = self.serverlist[index]['mac']
			server_ip_selected = self.serverlist[index]['ip']
			server_outport_selected = int(self.serverlist[index]['outport'])
			index1 = index + 1

			print("Server ", index1)

            # Route to server
			match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype,
					eth_src=eth.src, eth_dst=eth.dst,ip_proto=ip_header.proto,
					ipv4_src=ip_header.src, ipv4_dst=ip_header.dst)

			actions = [parser.OFPActionSetField(eth_dst=server_mac_selected),
                       parser.OFPActionSetField(ipv4_dst=server_ip_selected),
                       parser.OFPActionOutput(server_outport_selected)]
			inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
					actions)]
			cookie = random.randint(0, 0xffffffffffffffff)
			flow_mod = parser.OFPFlowMod(datapath=datapath, match=match,
						idle_timeout=0, instructions=inst,
						buffer_id=msg.buffer_id, cookie=cookie)
			datapath.send_msg(flow_mod)

            # Reverse route from server
			match = parser.OFPMatch(in_port=server_outport_selected,
					eth_type=eth.ethertype, eth_src=server_mac_selected,
                    eth_dst=eth.src, ip_proto=ip_header.proto,
                    ipv4_src=server_ip_selected, ipv4_dst=ip_header.src)

			actions = [parser.OFPActionSetField(eth_src=self.virtual_mac),
                       parser.OFPActionSetField(ipv4_src=self.virtual_ip),
                       parser.OFPActionOutput(in_port)]

			inst2 = [parser.OFPInstructionActions(
					ofproto.OFPIT_APPLY_ACTIONS, actions)]
			cookie = random.randint(0, 0xffffffffffffffff)
			flow_mod2 = parser.OFPFlowMod(datapath=datapath, match=match,
						idle_timeout=0, instructions=inst2, cookie=cookie)
			datapath.send_msg(flow_mod2)
