from server.server import RobotServer

if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = 61111
    server = RobotServer(HOST, PORT)
    server.start()
