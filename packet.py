import pickle
import random
import struct


class Packet:
    """A data packet or an ACK/NAK packet."""

    def __init__(self, sequence_number, message=b"", packet_type="DATA"):
        self.sequence_number = sequence_number  # 1, 2, 3, ...
        self.checksum = "Valid"                 # "Valid" or "Invalid"
        self.length = len(message)              # never more than the MSS
        self.message = message                  # the bytes of the picture
        self.packet_type = packet_type          # "DATA", "ACK" or "NAK"

    def is_valid(self):
        return self.checksum == "Valid"


def parse_probability(text):
    """Accept .2, 0.2, 20 or 20% and return a number between 0 and 1."""
    text = text.strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100
    value = float(text)
    if value > 1:
        value = value / 100
    return value


def send_packet(sock, packet, corrupt_prob, can_corrupt=True):
    """Maybe corrupt the packet, then send it through the socket."""
    if can_corrupt and random.random() < corrupt_prob:
        packet.checksum = "Invalid"
    else:
        packet.checksum = "Valid"
    data = pickle.dumps(packet)
    # Put the size in front so the other side knows how many bytes to read.
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("The other side closed the connection.")
        data += chunk
    return data


def recv_packet(sock):
    """Read one whole packet from the socket."""
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    return pickle.loads(recv_exact(sock, size))
