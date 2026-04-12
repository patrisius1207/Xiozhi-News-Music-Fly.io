#!/data/data/com.termux/files/usr/bin/bash
source ~/.bashrc
sshd
sleep 2
python -u ~/server.py > ~/server.log 2>&1 &
