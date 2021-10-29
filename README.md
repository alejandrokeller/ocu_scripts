# Organic Coating Unit: Control & Visualization System
## Collection of scripts for controlling OCU from a RASPI (python and unix shell)
*Application developed in **Python** to work in conjunction a **serial** controlled device.*

### **Installation**
1. Clone repository, setting the branch to **ocu** and the destination folder to either `/logger` or to a directory of your preference:
```bash
$ sudo git clone --branch ocu https://github.com/alejandrokeller/FATCAT-scripts /logger
```
2. Travel to cloned folder:
```bash
$ cd /logger
```
3. Copy the configuration template to the config.ini file and the launchers configuration template to the launchers/config file (no .ini extension). Then open created files and check the **[configuration](#configuration-file)**. You can set here the destination directories for the output files.
```bash
$ cp /logger/config.template /logger/config.ini
$ cp /logger/launchers/config.template /logger/launchers/config
```
5. Create required data and logs directories:
```bash
$ sudo mkdir  ~/ocu/ ~/ocu/data ~/ocu/logs ~/ocu/data/baseline
```
5. Install python requirements:
```bash
$ pip install -r extras/requirements.txt
```
6. Install PySide (for python3 use the `python3-pyside` meta package):
```bash
$ sudo apt-get install python-pyside
```
7. In some linux distributions, e.g. Ubuntu, install python-tk (already installed on the Raspberry Pi):
```bash
sudo apt-get install python-tk
```
## Adding the OCU directories to your user `PATH` environment

1. Open the `.profile` file.
```
nano ~\.profile
```
2. Append the following text (substitute `/logger` with the directory where you installed the scripts):
```
# set PATH so it includes the Fatcat scripts if it exists
if [ -d "/logger" ] ; then
    PATH="/logger:$PATH"
fi
if [ -d "/logger/extras" ] ; then
    PATH="/logger/extras:$PATH"
fi
```
3. Press <kbd>ctl</kbd>+<kbd>x</kbd> followed by <kbd>y</kbd> and then press enter to save the file.
4. The new `PATH` environment will be available next time you start a session.

### Using cron daemon to run scripts

The **logger application** can be set to start at system boot by adding a command to the cron daemon.
1. Enter to crontab edit mode by typing:
```
crontab -e
```
If this is the first time that you use *cron*, the system will ask you to choose a default edit program like, e.g., `nano`. 

2. Go to the end of the line and type the following command:
```
@reboot sh /logger/launchers/launcher.sh >>/home/pi/ocu/logs/devicelog 2>&1
```
This will run the `launcher.sh` script at startup and save the error messages to `/home/pi/ocu/logs/devicelog`. Make sure that the script and log directories are correct and that your user has enough priviliges to read (script directory) or write (log directory), otherwise the command will not run.

3. Press <kbd>ctl</kbd>+<kbd>x</kbd> and then <kbd>y</kbd> to save the changes.

### Launching the graphical user interface at startup (Raspberry Pi)

1. Go to the autostart directory: `cd ~/.config/autostart`
2. Add an autostart file `nano ocu.desktop`
3. Populate the file using:
```
[Desktop Entry]
Type=Application
Name=OCUGUI
Exec=/logger/gui.py &
StartupNotify=false
```
4. Pres <kbd>ctl</kbd>+<kbd>x</kbd> and then <kbd>y</kbd> to seve the changes

## Enabling USB/Serial Port Permissions on Linux (not needed for the Raspberry Pi)

Note: Linux distributions other than Ubuntu may run into issues with the following instructions: 

1. Add yourself to the "dialout" group:
```
sudo usermod -a -G dialout $USER
```
2. Create a rule file to automatically enable permissions when Palette™/P+™ is connected:
```
sudo nano /etc/udev/rules.d/50-local.rules
```
3. Paste this line in the file you just created:
```
ACTION=="add", ATTRS{idProduct}=="0042", ATTRS{idVendor}=="2341", DRIVERS=="usb", RUN+="chmod a+rw /dev/ttyACM0"
```
4. Press `Control-O` and then `Control-X` to save the file and exit.

Note: you may need to log out and log back in (or reboot your computer) for the changes to take effect.

## Installing RealVNC Server for Ubuntu (not required for Raspberry Pi)


These instructions explain how to install VNC Connect (version 6+) on supported Debian-compatible computers.

VNC Connect consists of a VNC Server app for the remote computer you want to control, and a VNC Viewer app for the local device you want to control from.

You can perform all the operations on this page at the command line. Check out our example script.

### Downloading VNC Server

Download the appropriate [VNC Server DEB installer](https://www.realvnc.com/connect/download/vnc/linux/) for the architecture of the remote computer you want to control.

If you do not have administrative privileges, or want to specify non-default installation locations, download the appropriate generic installer instead, and [run the script](https://www.realvnc.com/en/connect/docs/script-install-remove.html#script-install-remove) provided.

### Installing using desktop tools

Open `VNC-Server.deb` using a suitable package manager, and follow the instructions. Administrative privileges are required.

### Installing at the command line

Installing at the command line or via SSH may be quicker and more convenient providing defaults are acceptable. To do this, run the following command as a user with administrative privileges:

```
dpkg -i <VNC-Server>.deb
```

### Licensing VNC Server

You must license VNC Server running on the remote computer or remote access will not be available. You don’t need to license VNC Viewer.

* If you have a Home or Professional subscription, [follow these instructions](https://www.realvnc.com/en/connect/docs/licensing.html#license-home-pro).
* If you have an Enterprise subscription, [follow these instructions](https://www.realvnc.com/en/connect/docs/licensing.html#license-enterprise).

### Setting up the environment for VNC Server

#### VNC Server in Service Mode

Wayland is not supported, so if the remote computer is running Ubuntu 18.04 LTS+, edit the `/etc/gdm3/custom.conf` file, uncomment `WaylandEnable=false`, and reboot in order to remotely access the login screen.

#### VNC Server in Virtual Mode

To use VNC Server in Virtual Mode with the latest Ubuntu distributions, you may need to change the [desktop environment](https://help.realvnc.com/hc/en-us/articles/360003474792?_ga=2.217791824.715315377.1562065979-2142468511.1562065979).

#### SELinux

If SELinux is enabled, run `vncinitconfig -register-SELinux` to register policy modules.

### Starting VNC Server

To start VNC Server in [Service Mode](https://www.realvnc.com/en/connect/docs/server-modes.html#server-modes), run the appropriate command below as a user with administrative privileges:

`systemctl start vncserver-x11-serviced.service` #systemd
`/etc/init.d/vncserver-x11-serviced start` #initd

For other command line operations and modes, see [these instructions](https://www.realvnc.com/en/connect/docs/unix-start-stop.html#unix-start-stop).

### Downloading VNC Viewer

Download the [VNC Viewer DEB installer](https://www.realvnc.com/connect/download/viewer/linux/) to the computer you want to control if you have administrative privileges to install, or the standalone binary if not.

### Removing VNC Connect
#### Using desktop tools

To uninstall VNC Server, open a package manager, conduct a search for the **realvnc-vnc-server** installed package, mark the package for complete removal, and apply the change. Administrative privileges are required. To uninstall VNC Viewer, repeat this operation for ***realvnc-vnc-viewer***.

#### At the command line

Run the following command as a user with administrative privileges:
```
apt-get purge realvnc-vnc-server realvnc-vnc-viewer
```

* To completely remove (benign) configuration and other files or settings that may remain, follow [these instructions](https://www.realvnc.com/en/connect/docs/uninstall.html#uninstall).
