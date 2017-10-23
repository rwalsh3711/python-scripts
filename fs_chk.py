#!/usr/bin/python
import subprocess

fs_str = input("What filesystem? ")
max_int = input("Max utilization? ")

for line in subprocess.check_output("df -k", shell=True).splitlines()[1:]:
	fs_name = line.split()[5]
	usage_var = line.split()[4].rstrip('%')
	usage_int = int(usage_var)
  	if fs_str == fs_name:
   		if usage_int >= max_int:
   			print "Filesytem %s is at %s%% which exceeds max setting of %s%%!" % (fs_str, usage_int, max_int)
   		else:
   			print "Filesytem %s is at %s%% which is below max setting of %s%%!" % (fs_str, usage_int, max_int)

