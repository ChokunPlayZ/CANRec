PI      ?= root@192.168.99.1
BUILD   ?= chokun@lilac.ckl.moe
WEBROOT  = buildroot/board/canrec/pi4/rootfs_overlay/var/www

.PHONY: deploy-web build

# Push web files live to the running Pi (no reflash needed).
# Reboot reverts to the last flashed image; flash to make permanent.
deploy-web:
	rsync -avz --delete --no-owner --no-group $(WEBROOT)/ $(PI):/tmp/www/

# Rebuild the rootfs image on the build server and pull the result.
build:
	ssh $(BUILD) 'git -C ~/CANRec pull && rm -f ~/canrec-build/images/rootfs.ext4 && make -C ~/canrec-build'
