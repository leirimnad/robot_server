import sys

from .server import RobotServer
import argparse
import re
import logging


def port_type(x):
    x = int(x)
    if not (49152 <= x <= 65535):
        raise argparse.ArgumentTypeError("Port must be in range 49152-65535")
    return x


def ip_type(arg_value):
    if not re.match(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", arg_value):
        raise argparse.ArgumentTypeError("invalid IP")
    return arg_value


parser = argparse.ArgumentParser(description='Robot control server')
parser.add_argument('port', metavar='PORT', type=port_type, help='number of port to listen on')
parser.add_argument('-a', '--host', metavar='A.A.A.A', type=ip_type, default="127.0.0.1",
                    help='host IP address to listen on')
parser.add_argument('-g', '--gui', default=False, action='store_true', help='run with GUI')
parser.add_argument('-v', '--verbose', default=False, action='store_true', help='print messages to console')
parser.add_argument('-l', '--log', metavar='file', type=str, default=None, help='log file')


args = parser.parse_args()

if __name__ == "__main__":
    server = RobotServer(args.host, args.port)

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO)

    if args.verbose:
        if not args.log:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    if args.gui:
        from .gui.application import RobotServerApplication
        app = RobotServerApplication(server)
        app.run()
    else:
        server.start()
