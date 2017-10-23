#!/usr/bin/python
"""
Generate udev rules for +ASM disk

Author: Joel E Carlson <Joel_Carlson@uhc.com>
"""
import re, socket, sys, getopt
import os.path
from subprocess import Popen, PIPE

hostname = (socket.gethostname()).upper()

revision = "1.0.4"
rules = "/etc/udev/rules.d/99-asmdisk.rules"
dg = {}
id_to_udev = {}

class DiskMap:
	""" DiskMap class maps sg, sd, size """
	def __init__(self):
		self.sg_to_sd = {}   # sg to sd
		self.sd_to_sg = {}   # sd to sg
		self.sd_to_id = {}   # sd to scsi target
		self.sd_to_uuid = {} # sd to scsi_id
		self.sd_to_size = {} # sd to size
		self.dm_to_uuid = {} # dm to wwn
		self.uuid_to_sd = {} # reverse mapping
		self.virtual = self.is_virt()
		self.disk_map()

	def disks(self):
		if self.virtual:
			return self.sd_to_id.items()
		else:
			return self.dm_to_uuid.items()

	def without_dev(self,x):
		return (re.split("/dev/", x))[1]

	def with_dev(self,x):
		return "/dev/" + x

	def is_virt(self):
		try:
			p = Popen(["/sbin/lspci"], stdout=PIPE)
			for i in p.stdout:
				if re.search("VMware", i):
					return True
		except OSError:
			raise
		return False

	def map_multipath(self):
		try:
			p = Popen(["/sbin/dmsetup", "ls", "-o", "blkdevname"], stdout=PIPE)
			for i in p.stdout:
				if re.match("^\d+", i):
					id = (re.split("\s+", i))[0]
					dm = (re.split("\s+", i))[1]
					dm = re.sub('\(', '', dm)
					dm = re.sub('\)', '', dm)
					self.dm_to_uuid[dm] = id
					self.uuid_to_sd[id] = dm
		except OSError:
			raise

	def map_partitions(self):
		try:
			for i in open("/proc/partitions"):
				if re.search("^\s+\d+", i):
					sz = (re.split("\s+", i))[3]
					sd = (re.split("\s+", i))[4]
					self.sd_to_size[sd] = sz
		except IOError:
			raise

	def map_scsi(self, x):
		try:
			p = Popen(["/sbin/scsi_id", "-g", "-u", "-d", self.with_dev(x)], stdout=PIPE)
			for i in p.stdout:
				return (i.split())[0]
		except OSError:
			raise

	def disk_map(self):
		self.map_multipath()
		self.map_partitions()
		try:
			p = Popen(["/usr/bin/sg_map", "-x"], stdout=PIPE)
			for i in p.stdout:
				d = i.split()
				try:
					sg = self.without_dev(d[0])
					sd = self.without_dev(d[6])
					tg = "%s:%s:%s:%s:%s" %(d[1], d[2], d[3], d[4], d[5])
					id = self.map_scsi(sd)
				except:
					continue
				if sd != "scd0" and sd != "sr0":
					self.sg_to_sd[sg] = sd
					self.sd_to_sg[sd] = sg
					self.sd_to_id[sd] = tg
					self.sd_to_uuid[sd] = id
					self.uuid_to_sd[id] = sd
		except OSError:
			raise

	def uuid_and_size(self, x):
		if self.virtual:
			return [self.sd_to_uuid[x], self.sd_to_size[x]]
		else:
			return [self.dm_to_uuid[x], self.sd_to_size[x]]
			
# -*-*-*- DiskMap -*-*-*-

# ORAC diskgroup example the sizes have to be changed to match ESD
def v_diskgroup(disk):
	o_ct = 0 
	r_ct = 0
	r2_ct = 0
	t_ct = 0
	a_ct = 0
	a2_ct = 0
	d_ct = 0
	ct = 0
	for k,v in disk.sd_to_sg.items():
		if k == "sda" or k == "sdb" or k == "sdc":
			continue
		x = int(disk.sd_to_size[k]) 
		if x <= 2097152 and o_ct < 5:
			o_ct += 1
			dg[k] = "ORAC01_%d" %(o_ct)
		elif x <= 16777216 and t_ct < 1 :
			t_ct += 1
			dg[k] = "TEMP01_%d" %(t_ct)
		elif x <= 16777216 and r_ct < 1:
			r_ct += 1
			dg[k] = "REDO01_%d" %(r_ct)
		elif x <= 16777216 and r2_ct < 1:
			r2_ct += 1
			dg[k] = "REDO02_%d" %(r2_ct)
		elif x <= 33554432 and a_ct < 1:
			a_ct += 1
			dg[k] = "ARCH01_%d" %(a_ct)
		elif x <= 33554432 and a2_ct < 1:
			a2_ct += 1
			dg[k] = "ARCH02_%d" %(a2_ct)
		elif x <= 67108864:
			d_ct += 1
			dg[k] = "DATA01_%d" %(d_ct)
		else:
			ct += 1
			dg[k] = "ASMDISK_%d" %(ct)

# ORAC diskgroup example the sizes have to be changed to match ESD
def d_diskgroup(disk):
	o_ct = 0 
	r_ct = 0
	r2_ct = 0
	t_ct = 0
	a_ct = 0
	a2_ct = 0
	d_ct = 0
	ct = 0
	for k,v in disk.dm_to_uuid.items():
		x = int(disk.sd_to_size[k]) 
		if x <= 1049280 and o_ct < 5:
			o_ct += 1
			dg[k] = "ORAC01_%d" %(o_ct)
		elif x <= 16777920 and r_ct < 8:
			r_ct += 1
			dg[k] = "REDO01_%d" %(r_ct)
		elif x <= 16777920 and r2_ct < 8:
			r2_ct += 1
			dg[k] = "REDO02_%d" %(r2_ct)
		elif x <= 134218560 and t_ct < 4 :
			t_ct += 1
			dg[k] = "TEMP01_%d" %(t_ct)
		elif x <= 134218560 and a_ct < 4:
			a_ct += 1
			dg[k] = "ARCH01_%d" %(a_ct)
		elif x <= 134218560 and a2_ct < 4:
			a2_ct += 1
			dg[k] = "ARCH02_%d" %(a2_ct)
		elif x <= 134218560 and d_ct  < 12:
			d_ct += 1
			dg[k] = "DATA01_%d" %(d_ct)
		else:
			ct += 1
			dg[k] = "ASMDISK_%d" %(ct)

# grammar file to determine diskgroup
def g_diskgroup(arg):
	seen = {}
	# set seen on current ruleset
	if os.path.exists(rules):
		for k,v in dg.items():
			d = re.search(r"(\S+)_\d+", v)
			n = re.search(r"_(\d+)", v)
			seen[d.group(1)] = int(n.group(1))
	try:
		for i in open(arg):
			if re.match("^#", i):
				pass
			d = (re.split("\s+", i))[0]
			g = (re.split("\s+", i))[1]
			if g in seen:
				seen[g] += 1
			else:
				seen[g] = 1
			dg[d] = "%s_%d" %(g, seen[g])
	except IOError:
		raise

# od --read-bytes=128 --format=c /dev/sdd to determine diskgroup
def o_diskgroup(diskmap):
	seen = {}
	for k,v in diskmap.disks():
		if k == "sda" or k == "sdb":
			continue
		g = "none"
		try:
			p = Popen(["/usr/bin/od", "--read-bytes=128", "--format=c", "/dev/" + k], stdout=PIPE)
			for i in p.stdout:
				if re.search("D\s+A\s+T\s+A\s+0\s+1", i):
					g = "DATA01"
				elif re.search("D\s+A\s+T\s+A\s+0\s+2", i):
					g = "DATA02"
				elif re.search("A\s+R\s+C\s+H\s+0\s+1", i):
					g = "ARCH01"
				elif re.search("A\s+R\s+C\s+H\s+0\s+2", i):
					g = "ARCH02"
				elif re.search("R\s+E\s+D\s+O\s+0\s+1", i):
					g = "REDO01"
				elif re.search("R\s+E\s+D\s+O\s+0\s+2", i):
					g = "REDO02"
				elif re.search("T\s+E\s+M\s+P\s+0\s+1", i):
					g = "TEMP01"
				elif re.search("O\s+R\s+A\s+C\s+0\s+1", i):
					g = "ORAC01"
		except OSError:
			raise
		if g in seen:
			seen[g] += 1
		else:
			seen[g] = 1
		dg[k] = "%s_%d" %(g, seen[g])

# read 99-asmdisk.rules
def asmdisk():
	try:
		for i in open(rules):
			if re.search("ID_SERIAL", i):
				id = re.search(r"ENV{ID_SERIAL}==\"(\w+)\"", i)
				t = re.search(r"SYMLINK\+=\"(\S+)\"", i)
				id_to_udev[id.group(1)] = t.group(1)
			elif re.search("DM_NAME", i):
				id = re.search(r"ENV{DM_NAME}==\"(\w+)\"", i)
				t = re.search(r"SYMLINK\+=\"(\S+)\"", i)
				id_to_udev[id.group(1)] = t.group(1)
	except IOError:
		raise

# dump 99-asmdisk.rules
def asmdisk_dump(diskmap):
	fmt="%-35s %-4s %-10s %-s"
	print fmt %("UUID", "Dev", "Size", "Oracle Diskgroup")
	for k,v in id_to_udev.items():
		try:
			sd = diskmap.uuid_to_sd[k]
			sz = diskmap.sd_to_size[sd]
			sz = "%2.2f GiB" %( (int(sz)>>10)>>10 )
		except:
			sd = "unk"
			sz = "0.0 GiB"
		print fmt %(k, sd, sz, v)


def rule(fmt, id, sd, t, sz, target):
	target = "udevlinks/" + hostname + "_" + target
	print "#", id, sd, t, sz 
	print fmt %(id, target)

def usage():
	print """finduuid.py: [-h|--help] [-d|--delta] [-g|--grammar=<def>] [-m|--map] [-o|--od]
where
\t--help    print usage summary
\t--delta   print diff from 99-asmdisk.rules
\t--grammar use definition file for rules
\t--map     dump current 99-asmdisk.rules
\t--od      rules based on od scan

revision: %s
""" %(revision)

def main(argv):
	_delta   = False
	diskmap  = DiskMap()

	if diskmap.virtual:
		fmt = 'KERNEL=="sd*", BUS=="scsi", ENV{ID_SERIAL}=="%s", SYMLINK+="%s", OWNER="oracle", GROUP="dba", MODE="0660"'
		v_diskgroup(diskmap)
	else:
		fmt = 'ACTION=="add|change", ENV{DM_NAME}=="%s", SYMLINK+="%s", OWNER="oracle", GROUP="dba", MODE="0660"'
		d_diskgroup(diskmap)

	# command line arguments
	try:
		opts, args = getopt.getopt(argv, "hdmog:", ["help", "delta", "map", "od", "grammar="])
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	for opt,arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt in ("-d", "--delta"):
			_delta = True
			asmdisk()
		elif opt in ("-m", "--map"):
			asmdisk()
			asmdisk_dump(diskmap)
			sys.exit()
		elif opt in ("-o", "--od"):
			o_diskgroup(diskmap)
		elif opt in ("-g", "--grammar"):
			g_diskgroup(arg)
		
	for k,v in diskmap.disks():
		(id,sz) = diskmap.uuid_and_size(k)
		try:
			target = dg[k]
		except:
			continue
		if _delta and id in id_to_udev:
			pass
		else:
			if diskmap.virtual:
				rule(fmt, id, k, v, sz, target)
			else:
				rule(fmt, v, k, '', sz, target) 

if __name__ == '__main__':
	main(sys.argv[1:])
	sys.exit()
