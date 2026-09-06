"""Topology helpers shared by transceiver scenario tests."""
from collections import namedtuple


PeerInfo = namedtuple("PeerInfo", ("host", "device", "port", "primary_port"))


def resolve_remote_peer(duthost, duthosts, conn_graph_facts, local_port, lport_to_first_subport_mapping):
    """Return ``(PeerInfo, error)`` for a local port's connection-graph peer."""
    dut_conn = conn_graph_facts.get("device_conn", {}).get(duthost.hostname, {})
    peer_entry = dut_conn.get(local_port)
    if not peer_entry:
        return None, "{} has no remote peer in conn_graph_facts".format(local_port)

    peer_device = peer_entry.get("peerdevice")
    peer_port = peer_entry.get("peerport")
    if not peer_device or not peer_port:
        return None, "{} peer entry missing peerdevice/peerport: {}".format(local_port, peer_entry)

    if peer_device == duthost.hostname:
        peer_host = duthost
        peer_primary = lport_to_first_subport_mapping.get(peer_port, peer_port)
    else:
        try:
            peer_host = duthosts[peer_device]
        except (KeyError, TypeError):
            return None, "{} peer device {} is not available as a DUT host".format(local_port, peer_device)
        peer_primary = peer_port

    return PeerInfo(peer_host, peer_device, peer_port, peer_primary), None
