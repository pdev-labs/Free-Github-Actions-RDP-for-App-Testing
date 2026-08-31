#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y sudo openssh-server xrdp dbus-x11 xorgxrdp xfce4 xfce4-goodies
useradd -m -s /bin/bash runner
echo "runner:ThePassword123!" | chpasswd
usermod -aG sudo runner
echo "exec dbus-launch --exit-with-session startxfce4" > /home/runner/.xsession
chown runner:runner /home/runner/.xsession
chmod +x /home/runner/.xsession
cat << 'STARTWM' > /etc/xrdp/startwm.sh
#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
export XDG_SESSION_TYPE=x11
export XDG_SESSION_DESKTOP=xfce
export XDG_CURRENT_DESKTOP=XFCE
exec /home/runner/.xsession
STARTWM
chmod +x /etc/xrdp/startwm.sh
mkdir -p /run/dbus
dbus-daemon --system --nofork &
/etc/init.d/xrdp start
sleep 3
