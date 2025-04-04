import socket
import struct
import time
import threading
import random
import csv

# Constants
TIMEOUT = 0.05
WINDOW_SIZE = 10
PACKET_SIZE = 1024
EOF_SEQ = 0xFFFFFFFF
CSV_FILENAME = "completion_times.csv"


class Sender:
    def __init__(self, receiver_ip, receiver_port, file_path, error_rate=0.0, loss_rate=0.0):
        self.receiver_addr = (receiver_ip, receiver_port)
        self.file_path = file_path
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.01)
        self.error_rate = error_rate
        self.loss_rate = loss_rate

        self.base = 0
        self.next_seq = 0
        self.lock = threading.Lock()
        self.timer = None
        self.buffer = {}
        self.done = False

    def make_packets(self):
        with open(self.file_path, 'rb') as file:
            seq = 0
            while chunk := file.read(PACKET_SIZE):
                pkt = struct.pack('!I', seq) + chunk
                self.buffer[seq] = pkt
                seq += 1
        self.total_packets = seq

    def start_timer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(TIMEOUT, self.timeout_handler)
        self.timer.start()

    def timeout_handler(self):
        with self.lock:
            print(f"Timeout! Resending from seq {self.base}")
            self.start_timer()
            for seq in range(self.base, min(self.next_seq, self.base + WINDOW_SIZE)):
                self.sock.sendto(self.buffer[seq], self.receiver_addr)

    def corrupt_ack(self, ack):
        if random.random() < self.error_rate:
            print("Simulating ACK bit error.")
            return ack ^ 1
        return ack

    def send_file(self):
        self.make_packets()
        self.start_timer()
        start_time = time.time()

        while not self.done:
            with self.lock:
                while self.next_seq < self.base + WINDOW_SIZE and self.next_seq < self.total_packets:
                    self.sock.sendto(self.buffer[self.next_seq], self.receiver_addr)
                    self.next_seq += 1

            try:
                ack_pkt, _ = self.sock.recvfrom(4)

                # Simulate ACK loss
                if random.random() < self.loss_rate:
                    print("Simulating ACK loss.")
                    continue

                ack = struct.unpack('!I', ack_pkt)[0]
                ack = self.corrupt_ack(ack)

                with self.lock:
                    if ack >= self.base:
                        self.base = ack + 1
                        if self.base == self.next_seq:
                            if self.timer:
                                self.timer.cancel()
                        else:
                            self.start_timer()

            except socket.timeout:
                # Handle timeout without getting stuck
                if self.base == self.total_packets:
                    break

            if self.base == self.total_packets:
                self.done = True

        self.sock.sendto(struct.pack('!I', EOF_SEQ), self.receiver_addr)
        if self.timer:
            self.timer.cancel()
        self.sock.close()

        duration = time.time() - start_time
        print(f"File sent in {duration:.3f} seconds.")
        return duration


if __name__ == "__main__":
    # Hardcoded test configuration
    scenario = 2
    rate = 0.1
    port = 5003
    file_path = "tiger.jpg"

    error_rate = 0.0
    loss_rate = 0.0  # This will only affect ACK loss in the receiver

    if scenario == 2:
        error_rate = rate
    elif scenario == 4:
        loss_rate = rate

    sender = Sender("127.0.0.1", port, file_path, error_rate, loss_rate)
    time_taken = sender.send_file()

    with open(CSV_FILENAME, "a") as f:
        writer = csv.writer(f)
        writer.writerow([scenario, rate, time_taken])
