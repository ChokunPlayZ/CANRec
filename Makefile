PI      ?= root@192.168.99.1
BUILD   ?= chokun@lilac.ckl.moe
WEBROOT  = buildroot/board/canrec/pi4/rootfs_overlay/var/www

# Dropbear regenerates host keys each boot (read-only root); skip checking.
SSH_OPTS = -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

.PHONY: deploy-web ssh build

# Push web files live to the running Pi (no reflash needed).
# Uses tar-over-SSH — no rsync needed on the Pi.
# Reboot reverts to the last flashed image; flash to make permanent.
deploy-web:
	tar -czf - -C $(WEBROOT) . | ssh $(SSH_OPTS) $(PI) 'tar -xzf - -C /tmp/www'

# Open a shell on the Pi.
ssh:
	ssh $(SSH_OPTS) $(PI)

# Rebuild the rootfs image on the build server and pull the result.
build:
	ssh $(BUILD) 'git -C ~/CANRec pull && rm -f ~/canrec-build/images/rootfs.ext4 && make -C ~/canrec-build'
