# Installing OpenCV on Raspberry Pi Zero

* <https://yoursunny.com/t/2018/install-OpenCV3-PiZero/>
* (this didn't work) <https://towardsdatascience.com/installing-opencv-in-pizero-w-8e46bd42a3d3>

```shell
sudo su -
raspi-config --expand-rootfs
reboot
# wait and log back in...
sudo nano /etc/dphys-swapfile
# expand swap file to 2048
reboot
# wait and log back in...
sudo apt update
sudo apt install python3-opencv
python3 -c 'import cv2; print(cv2.__version__)'
python -c "import cv2; print(cv2.getBuildInformation())"
```
