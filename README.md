# SAXSControl

A GUI written in Python to control and monitor beamtime setups.

## Setup/Requirements

This program is designed for use with Python 3 (not Python 2). Also, it's designed to work on Windows computers. It may or may not work on \*nix and Macs; it's not been tested.

First of all, go to National Instruments' website to install the 64bit LabView Run-Time Engine: http://www.ni.com/en-us/support/downloads/software-products/download.labview.html#301740 . Download the installer and run it (this may take half an hour or an hour, even, so be prepared!). It'll prompt you to restart your computer. Do that, and then open up the NI Package Manager. Then go back and download the 2015 version instead, which Elveflow requires. (There's probably a smarter way to do this, but I'm not sure exactly how, and besides, it works.) It'll prompt you to restart your computer again, but before you do that, you'll need to install one more thing. To actually read from the Elveflow, you'll need its name, a hexadecimal number that you can find by connecting the Elveflow by USB and running the NI MAX software, which can installed from the NI Package Manager by installing NI Serial. Now you can restart your computer. (Our machine seems to have a name 01A377A5 but I'm not sure if this sort of thing changes each time you connect it or what.)

Matplotlib 3 [has a bug](https://github.com/matplotlib/matplotlib/issues/13293) that causes crashing when you use it to graph in a Tkinter GUI on anything other than a main thread. So for the moment, this program requires Matplotlib 2 and not 3. All requirements are listed in `requirement.txt`, which `pip` can understand and install everything for you. To install all requirements, run

    pip install -r requirements.txt

or

    python -m pip install -r requirements.txt

If you have Matplotlib 3 already installed on your computer, this will force a downgrade back to Matplotlib 2. If you do want to leave Matplotlib 3 installed on your computer (for other projects, for example), Python has a feature where you can create and run python a virtual environment containing a separate set of installed dependencies. To create the virtual environment (you only need to do this once), in the root folder of this project, run:

    python -m venv SAXSControlEnv

("SAXSControlEnv" is an arbitrary name).

To use the virtual environment, go `cd` into the new folder created, `SAXSControlEnv`, and then go into its `Scripts` subfolder, and run `activate`. You are now in the virtual environment. You can now go back to the root folder and install requirements as per the instructions above without messing with anything already installed on your computer.

## What is implemented or in progress

- oil level display (alex-dev branch)
- oil syringe
- logging items into a file (derrick-dev branch)
- Syringe pump UART Control
- Rheodyne valve USB(UART) Control

## TODO

- interfacing with the following systems:
  - cleaning station
  - Elveflow
  - Arduino Control
  - CHESS systems
- display elements
  - cleaning station
  - flow rates
  - PID loop for setting the flow rate rather than setting the pressure
    - relatedly, limit the pressure gradient
