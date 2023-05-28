## Robot Control Server

Describe a function of developed application, necessary dependencies (e.g. utilize requirements.txt), how to start it, and last but not least how to run tests from CLI.

Robot Control Server is a server application for guiding robots on a simplified map. \
The process of controlling the robot consists of authentication and guiding the robot to the `(0, 0)` coordinate. \
The application starts a separate thread for each robot. \
The application also contains a GUI for displaying the conversation and the map for each robot.in real time.

This application is a semester project for the course "Python Programming" at FIT CTU in Prague. \
Full assignment is available [here](./task.md).

### Requirements

Requirements are listed in `requirements.txt` file. \
Required Python version: `3.8` or higher.

**Install requirements:**
```bash
pip install -r requirements.txt
```

### Usage

**Common cases:**

Run server in CLI on address `127.0.0.1`, port `61111`:
```bash
python -m robot_server 61111
```
Run server in GUI on address `127.0.0.1`, port `61111`:
```bash
python -m robot_server 61111 -g
```

**General usage:**

<pre>
python -m robot_server [-a A.A.A.A] [-g] [-v] [-l file] PORT

positional arguments:
  PORT                  number of port to listen on

options:
  -a A.A.A.A, --host A.A.A.A
                        host IP address to listen on
  -g, --gui             run with GUI
  -v, --verbose         print messages to console
  -l file, --log file   log file
</pre>

### Running tests

**Run all tests:**
```bash
pytest
```
or
```bash
python -m pytest
```

**Run tests with coverage:**
```bash
coverage run -m pytest ; coverage report
```
or 
```bash
python -m coverage run -m pytest ; python -m coverage report
```

#### Binary tests

Apart from unit tests, there are also binary tests created by the teacher for evaluating the application. \
Instructions for running them are available [here](https://drive.google.com/file/d/1bee4uq4iLhO9HYoCxRXQksOJaKFc2dxq/view?usp=sharing) (in Czech) and [here](https://drive.google.com/file/d/1j-agqvlpSXdkOIe9Anw9rd0mqRvn7r-q/view?usp=sharing) (in English).

Windows users should download the VirtualBox image for running the binary tests. \
The instructions for that are available on links above.

The binary file for the Linux users is available [here](https://drive.google.com/drive/folders/1QzPyzZeLNWZhjtbaTGehyNu-zgHcInta). \
The instructions for running the binary tests on Linux are available [in the task description](./task.md#tester). \
In short: ```tester <port number> <remote address> [test number(s)]```

### Known issues

Tested on Windows 11 with Python 3.11 and Lubuntu 20.04 with Python 3.10.

- When running on Linux, GraphicsView might not display the map properly. \
  Map is displayed properly when the window is scrolled. \
  Presumably, the issue is caused by Qt library.
