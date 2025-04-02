import socket
import struct
import random

PACKET_SIZE = 1024
EOF_SEQ = 0xFFFFFFFF


class Receiver:
    def __init__(self, port, output_file, error_rate=0.0, loss_rate=0.0):
        self.port = port
        self.output_file = output_file
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", port))
        self.expected_seq = 0
        self.error_rate = error_rate
        self.loss_rate = loss_rate

    @staticmethod
    def corrupt_data(data, error_rate):
        if random.random() < error_rate:
            corrupted = bytearray(data)
            corrupted[0] ^= 0b1
            print("Simulating data bit error.")
            return bytes(corrupted)
        return data

    def receive_file(self):
        with open(self.output_file, 'wb') as f:
            while True:
                try:
                    packet, sender_addr = self.sock.recvfrom(4 + PACKET_SIZE)

                    if random.random() < self.loss_rate:
                        print("Simulating data packet loss. Dropping packet.")
                        continue

                    seq_num = struct.unpack('!I', packet[:4])[0]

                    if seq_num == EOF_SEQ:
                        print("EOF received.")
                        break

                    data = self.corrupt_data(packet[4:], self.error_rate)

                    if seq_num == self.expected_seq:
                        f.write(data)
                        self.expected_seq += 1

                    ack = struct.pack('!I', self.expected_seq - 1)

                    if random.random() < self.loss_rate:
                        print("Simulating ACK loss. Not sending ACK.")
                        continue

                    self.sock.sendto(ack, sender_addr)
                except Exception as e:
                    print("Exception:", e)

        self.sock.close()
        print("File received successfully.")


if __name__ == "__main__":
    # Hardcoded test configuration
    scenario = 2
    rate = 0.1
    port = 5003

    error_rate = 0.0
    loss_rate = 0.0

    if scenario == 3:
        error_rate = rate
    elif scenario in [4, 5]:
        loss_rate = rate

    receiver = Receiver(port, "received_tiger.jpg", error_rate, loss_rate)
    receiver.receive_file()
