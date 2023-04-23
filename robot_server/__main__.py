import socket
from .robot_thread import RobotThread

if __name__ == "__main__":

    HOST = "127.0.0.1"
    PORT = 61111
    threads = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        print(f"Started server on {HOST}, port {PORT}")
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                thread = RobotThread(conn, addr)
                threads.append(thread)
                thread.start()
            except KeyboardInterrupt:
                break
        for thread in threads:
            thread.to_final()
