import io
import socket
import sys

from PIL import Image

from packet import Packet, parse_probability, send_packet, recv_packet

OUTPUT_FILE = "flipped_capybara.jpg"


def main():
    if len(sys.argv) != 4:
        print("Usage: python server.py [PORT] [CORRUPTION PROBABILITY] [MSS]")
        sys.exit(1)
    port = int(sys.argv[1])
    corrupt_prob = parse_probability(sys.argv[2])
    mss = int(sys.argv[3])

    received = {}  # sequence number -> bytes

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("localhost", port))
        s.listen(1)
        print(f"Server listening on port {port}...")
        conn, addr = s.accept()
        with conn:
            print(f"Client connected: {addr}\n")
            while True:
                packet = recv_packet(conn)
                seq = packet.sequence_number

                # Corrupted data packet: throw it out and send a NAK.
                if not packet.is_valid():
                    print(f"Received packet {seq}: CORRUPTED. Sending NAK")
                    send_packet(conn, Packet(seq, packet_type="NAK"), corrupt_prob)
                    continue

                # Duplicate data packet (our last ACK was corrupted): discard it.
                if seq in received:
                    print(f"Received packet {seq}: DUPLICATE, discarding. "
                          f"Sending ACK again")
                    send_packet(conn, Packet(seq, packet_type="ACK"), corrupt_prob)
                    continue

                received[seq] = packet.message
                is_last = packet.length < mss
                print(f"Received packet {seq} (length {packet.length}): valid. "
                      f"Sending ACK")
                # The ACK for the final packet is never corrupted.
                send_packet(conn, Packet(seq, packet_type="ACK"), corrupt_prob,
                            can_corrupt=not is_last)

                if is_last:
                    break

    # Put the packets back together in sequence-number order.
    data = b"".join(received[seq] for seq in sorted(received))
    print(f"\nAll {len(received)} packets received ({len(data)} bytes). "
          f"Reassembling image...")

    image = Image.open(io.BytesIO(data))
    flipped = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    flipped.save(OUTPUT_FILE)
    print(f"Flipped image saved as {OUTPUT_FILE}")
    flipped.show()
    print("Server shutting down.")


if __name__ == "__main__":
    main()
