#!/usr/bin/python3

import sys, os, subprocess

apk2src_path = os.path.dirname(os.path.realpath(__file__))      # this is the current running path

jadx_path = apk2src_path + '/jadx'
# bin_path = jadx_path + '/build/jadx/bin'
bin_path = jadx_path + "/bin"


sys.path.insert(0, jadx_path)
sys.path.insert(0, bin_path)


apk_path = sys.argv[1]					# get the aph's absolute path from args

# dir_name = apk_path[:-4]				# get the dir name when we put the decompiled app
# print(f'DECOMPILER: {dir_name}')

apk_name = apk_path[:-4].split("/")[-1]
main_dir_path = apk_path[:-4].split(apk_name)[0]
dec_dir_path = main_dir_path + "decompiled/"
dir_name = dec_dir_path + apk_name

if not os.path.isfile(f"{bin_path}/jadx"):											# if the bin 'jadx' doesn't exist...
	subprocess.run([f"jadx", apk_path, "-d", dir_name])						# try to see if it is installed in PATH
else :
	subprocess.run([f"{bin_path}/jadx", apk_path, "-d", dir_name])						# otherwise run from subdir

	
