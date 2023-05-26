from .server import RobotServer

if __name__ == "__main__":
    GUI = True
    HOST = "127.0.0.1"
    PORT = 61111
    server = RobotServer(HOST, PORT)
    if GUI:
        from .gui.application import RobotServerApplication
        app = RobotServerApplication(server)
        app.run()
    else:
        server.start()
