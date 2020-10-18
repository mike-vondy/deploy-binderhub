apt-get install nfs-kernel-server -y
mkdir -p /srv/nfs/binder
chmod -R 777 /srv/nfs/binder
chown -R nobody:nogroup /srv/nfs/binder

mv nfs-export.conf /etc/exports
exportfs -rav

systemctl start nfs-server
systemctl enable nfs-server