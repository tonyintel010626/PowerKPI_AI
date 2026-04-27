#Run SATA Hotplug Surprise Removal Silicon for 4 SATA devices connected to Quarch 4 Array Controller
#Owner : Ulul-Azmin, Ainalmardhiah (ainalmardhiah.ulul-azmin@intel.com)

import os, sys, time 

from quarchpy import *

#Used it to parse the arguement
import argparse

#used it to define pch and cpu
import namednodes as _namednodes

#import baseaccess
from svtools.common import baseaccess

#from svtools import ExitCodeEnum
from svtools import report

#import AsciiTable
from pysvtools.asciitable import AsciiTable

#import json
import json

#used it to initialize itp
itp = baseaccess.getglobalbase()

_namednodes.sv.initialize()

#used it to define sv
sv = _namednodes.sv

#used it to define cpu
#cpu = _namednodes.sv.socket.get_all()[0]

#used it to define pch
pch = _namednodes.sv.pch.get_all()[0]

report = report.Report("SATA_Hotplug_Surprise_Removal_Silicon")

report.summary="This SATA_Hotplug_Surprise_Removal_Silicon report was created using svtools.reports!"

json_dict = report.as_dict()

basename="SATA_Hotplug_Surprise_Removal_Silicon"
with open(basename + ".report.json", "w") as f:
    f.write(json.dumps(json_dict, indent=4))

report.sys.software.domain("content").domain("Pythonsv").domain("Python").add_data("Version","3.8") 

#OPTIONAL REPORT INFO: Useful for Axon/debug
report.sys.software.os("windows").add_data("version", 10)
report.sys.hardware.domain("socket0").domain("Quarch Technology").add_data("Module","QTL1461") 
report.sys.hardware.domain("socket0").domain("Quarch Technology").add_data("Module","Torridon 4-Port Array Controller") 
#report.sys.hardware.domain("socket0").domain("Quarch Technology").add_data("GEN","QTL1461") 
report.sys.hardware.domain("socket0").domain("SATA").add_data("GEN","3") 
report.sys.hardware.domain("socket0").domain("SATA").add_data("Brand","Samsung and Intel")

# report.sys.firmware.domain("bios").add_data("version","1.3.10")
# report.sys.firmware.bios.knobs.add_defeature("PkgC_Limit", "6")
#report.sys.firmware.domain("Quarch").domain("Quarch Technology").add_data("Version","4.001") 

#parse the arguments given
def parse_args():
    parser = argparse.ArgumentParser(description='SATA_Hotplug_Surprise_Removal_Silicon')
    parser.add_argument("-d", "--devices", default = "1", type=int, help='select SATA port for hotplug')
    parser.add_argument("-cycle", "--cyclehotplug", default = "1", type=int, help='loop of cycle for run hotplug')   
    args = parser.parse_args()
    return args    
args = parse_args()

#setup logging
try:
    #Open one file and execute in write mode
    f=open('SATA_Hotplug_Surprise_Removal_Silicon.log','w')
    
    #Log will be written into stdout
    sys.stdout=f

    #Raise exception if log file doesnt exist
except Exception as e:
    
    #Print the error into stderr
    print_to_stderr(e)

def print_to_stderr(err):
    #print error into stderr
    print(err, file = sys.stderr)
	
def main():
	#Create a device using the module connection string
	moduleStr = "USB:QTL1461-06-662"	
	myDevice = quarchDevice(moduleStr)
	#myDevice.sendCommand("*Serial?")
	
	print("**********************************************************************************")
	print("*                   Log file for SATA HotPlug Surprise Removal                   *")
	print("**********************************************************************************\n")
	print("Module Name:",myDevice.sendCommand("hello?"))
	print(("Total cycle: %d") %(args.cyclehotplug))
	
    # Ensure the module is in default state at start of test. Default state is put all devices in plugged state
	state = myDevice.sendCommand("config:default state <1-4>")
	print("\nPut devices in default state:")
	print(state)
	
    # Check the power up state of the module
	print("\nChecking the State of the Devices and Power up if necessary.")
	isDevice_1 = myDevice.sendCommand("run:power? <1>")
	isDevice_2 = myDevice.sendCommand("run:power? <2>")
	isDevice_3 = myDevice.sendCommand("run:power? <3>")
	isDevice_4 = myDevice.sendCommand("run:power? <4>")
	device_connected = 0

    # Ensure the module is in Power up state
	if isDevice_1 == "1:PULLED" or isDevice_2 == "2:PULLED" or isDevice_3 == "3:PULLED" or isDevice_4 == "4:PULLED":
		print("Devices is PULLED. Plugging all the devices...")
		myDevice.sendCommand("run:power up <1-4>")
		i=0
		while i<5:
			time.sleep(20)
			print ('Waiting {0}/5 seconds for power up to complete.\r'.format(i)),
			i+=1
		print ("\n")
	else:
		print("\nAll devices already plug")
		
	if isDevice_1 == "1:FAIL: 0x26 -No device is attached to this port":
		print_to_stderr("1:FAIL: 0x26 -No device is attached to this port")
	else:
		device_connected +=1
		
	if isDevice_2 == "2:FAIL: 0x26 -No device is attached to this port":
		print_to_stderr("2:FAIL: 0x26 -No device is attached to this port")
	else:
		device_connected +=1
		
	if isDevice_3 == "3:FAIL: 0x26 -No device is attached to this port":
		print_to_stderr("3:FAIL: 0x26 -No device is attached to this port")
	else:
		device_connected +=1
			
	if isDevice_4 == "4:FAIL: 0x26 -No device is attached to this port":
		print_to_stderr("4:FAIL: 0x26 -No device is attached to this port")
	else:
		device_connected +=1

	
	print("\nDevice Connected are: ", device_connected)
	
	isPluged = myDevice.sendCommand("run:power? <1-4>")
	print("\nState of the Devices before run HotPlug:"),
	print(isPluged + "\n")
	
	#Read SATA status for initial. This status will compare after devices are pull and plug to module
	itp.unlock()
	port0_initial = pch.sata.port0.pxssts0
	port1_initial = pch.sata.port1.pxssts1
	port2_initial = pch.sata.port2.pxssts2
	port3_initial = pch.sata.port3.pxssts3
	port4_initial = pch.sata.port4.pxssts4
	port5_initial = pch.sata.port5.pxssts5 
	port6_initial = pch.sata.port6.pxssts6
	port7_initial = pch.sata.port7.pxssts7
	print("SATA status before run HotPlug:")
	print("Port 0 status: ",port0_initial)
	print("Port 1 status: ",port1_initial)
	print("Port 2 status: ",port2_initial)
	print("Port 3 status: ",port3_initial)
	print("Port 4 status: ",port4_initial)
	print("Port 5 status: ",port5_initial)
	print("Port 6 status: ",port6_initial)
	print("Port 7 status: ",port7_initial)
	
    #Creating a loop for Hot-Plug cycle
	print("\n----------------------------------")
	print("|     Starting HotPlug cycle     |")
	print("----------------------------------")	
	flag = 0
	for i in range (args.cyclehotplug):
		print("\nHotPlug Cycle: %d"%i)
		print("\nPulling the device" + ",\n")
		
        # Power down (pull) the device
		myDevice.sendCommand("run:power down <1-4>"),
		time.sleep(30)
		
		isDevice = myDevice.sendCommand("run:power? <1-4>")
		print("State of the Devices:"),
		print(isDevice + "\n")
		
		pull_device = 0
		plug_device = 0
		pulled = 0 
		plug_error = 0
		
		print("SATA status after devices are pulled:")
		print("Port 0 status: ",pch.sata.port0.pxssts0)
		print("Port 1 status: ",pch.sata.port1.pxssts1)
		print("Port 2 status: ",pch.sata.port2.pxssts2)
		print("Port 3 status: ",pch.sata.port3.pxssts3)
		print("Port 4 status: ",pch.sata.port4.pxssts4)
		print("Port 5 status: ",pch.sata.port5.pxssts5)
		print("Port 6 status: ",pch.sata.port6.pxssts6)
		print("Port 7 status: ",pch.sata.port7.pxssts7)	
		
		if myDevice.sendCommand("run:power? <1>") == "1:PULLED":
			pull_device += 1
		else:
			print_to_stderr("Device on Port 1 not Pulled")
		
		if myDevice.sendCommand("run:power? <2>") == "2:PULLED":
			pull_device += 1
		else:
			print_to_stderr("Device on Port 2 not Pulled")
			
		if myDevice.sendCommand("run:power? <3>") == "3:PULLED":
			pull_device += 1
		else:
			print_to_stderr("Device on Port 3 not Pulled")
			
		if myDevice.sendCommand("run:power? <4>") == "4:PULLED":
			pull_device += 1
		else:
			print_to_stderr("Device on Port 4 not Pulled")
			
		#check sata status using PythonSV
		if pch.sata.port0.pxssts0 == 0x0 or pch.sata.port0.pxssts0 == 0x4:
			if port0_initial != 0x0 and port0_initial != 0x4:
				pulled += 1
				
		if pch.sata.port1.pxssts1 == 0x0 or pch.sata.port1.pxssts1 == 0x4:
			if port1_initial != 0x0 and port1_initial != 0x4:
				pulled += 1		
				
		if pch.sata.port2.pxssts2 == 0x0 or pch.sata.port2.pxssts2 == 0x4:
			if port2_initial != 0x0 and port2_initial != 0x4:
				pulled += 1
					
		if pch.sata.port3.pxssts3 == 0x0 or pch.sata.port3.pxssts3 == 0x4:
			if port3_initial != 0x0 and port3_initial != 0x4:
				pulled += 1
		
		if pch.sata.port4.pxssts4 == 0x0 or pch.sata.port4.pxssts4 == 0x4:
			if port4_initial != 0x0 and port4_initial != 0x4:
				pulled += 1
				
		if pch.sata.port5.pxssts5 == 0x0 or pch.sata.port5.pxssts5 == 0x4:
			if port5_initial != 0x0 and port5_initial != 0x4:
				pulled += 1
				
		if pch.sata.port6.pxssts6 == 0x0 or pch.sata.port6.pxssts6 == 0x4:
			if port6_initial != 0x0 and port6_initial != 0x4:
				pulled += 1
		
		if pch.sata.port7.pxssts7 == 0x0 or pch.sata.port7.pxssts7 == 0x4:
			if port7_initial != 0x0 and port7_initial != 0x4:
				pulled += 1
	
		# Power up (plug) the device
		print("\nPlugging the device.\n"),
		myDevice.sendCommand("run:power up <1-4>"),
		time.sleep(30)
		
		isDevice = myDevice.sendCommand("run:power? <1-4>")
		print("State of the Devices:"),
		print(isDevice + "\n")
		
		print("SATA status after devices are plugged:")
		print("Port 0 status: ",pch.sata.port0.pxssts0)
		print("Port 1 status: ",pch.sata.port1.pxssts1)
		print("Port 2 status: ",pch.sata.port2.pxssts2)
		print("Port 3 status: ",pch.sata.port3.pxssts3)
		print("Port 4 status: ",pch.sata.port4.pxssts4)
		print("Port 5 status: ",pch.sata.port5.pxssts5)
		print("Port 6 status: ",pch.sata.port6.pxssts6)
		print("Port 7 status: ",pch.sata.port7.pxssts7)		

		if myDevice.sendCommand("run:power? <1>")== "1:PLUGGED":
			plug_device += 1
		else:
			print_to_stderr("Device on Port 1 not plugged back")
		
		if myDevice.sendCommand("run:power? <2>") == "2:PLUGGED":
			plug_device += 1
		else:
			print_to_stderr("Device on Port 2 not plugged back")
			
		if myDevice.sendCommand("run:power? <3>") == "3:PLUGGED":
			plug_device += 1
		else:
			print_to_stderr("Device on Port 3 not plugged back")
			
		if myDevice.sendCommand("run:power? <4>") == "4:PLUGGED":
			plug_device += 1
		else:
			print_to_stderr("Device on Port 4 not plugged back")

		#check sata status using PythonSV
		if port0_initial != 0x0 and port0_initial != 0x4:
			if pch.sata.port0.pxssts0 == 0x0 or pch.sata.port0.pxssts0 == 0x4:
				plug_error += 1
		
		if port1_initial != 0x0 and port1_initial != 0x4:
			if pch.sata.port1.pxssts1 == 0x0 or pch.sata.port1.pxssts1 == 0x4:
				plug_error += 1
		
		if port2_initial != 0x0 and port2_initial != 0x4:
			if pch.sata.port2.pxssts2 == 0x0 or pch.sata.port2.pxssts2 == 0x4:
				plug_error += 1
		
		if port3_initial != 0x0 and port3_initial != 0x4:
			if pch.sata.port3.pxssts3 == 0x0 or pch.sata.port3.pxssts3 == 0x4:
				plug_error += 1
		
		if port4_initial != 0x0 and port4_initial != 0x4:
			if pch.sata.port4.pxssts4 == 0x0 or pch.sata.port4.pxssts4 == 0x4:
				plug_error += 1
		
		if port5_initial != 0x0 and port5_initial != 0x4:
			if pch.sata.port5.pxssts5 == 0x0 or pch.sata.port5.pxssts5 == 0x4:
				plug_error += 1

		if port6_initial != 0x0 and port6_initial != 0x4:
			if pch.sata.port6.pxssts6 == 0x0 or pch.sata.port6.pxssts6 == 0x4:
				plug_error += 1
		
		if port7_initial != 0x0 and port7_initial != 0x4:
			if pch.sata.port7.pxssts7 == 0x0 or pch.sata.port7.pxssts7 == 0x4:
				plug_error += 1

		print("\n-------------------------------------------------------")
		print("|Total SATA devices pulled from Quarch module     : %d |" %int(pull_device))
		print("|Total SATA devices plugged back to Quarch module : %d |" %int(plug_device))
		print("|Total SATA devices pulled from PythonSV          : %d |" %int(pulled))
		print("|Total SATA devices not plugged back              : %d |" %int(plug_error))
		print("-------------------------------------------------------")
		if pull_device == device_connected and plug_device == device_connected and pulled == device_connected and plug_error == 0:
			print("Cycle %d : All SATA devices success to run HotPlug Surprise Removal" %i)
			flag += 1
		
		else:
			print("Cycle %d : All SATA devices not pulled or not plugged back" %i)
			print_to_stderr("Cycle %d : All SATA devices not pulled or not plugged back" %i)
		
	print("\nCycle finished!")
	
	if flag == args.cyclehotplug:
		print("PASSED: All SATA devices success to run HotPlug Surprise Removal for %d cycle" %args.cyclehotplug)
		report.create_insight('SW.CONTENT', message = "PASSED: All SATA devices able to run HotPlug Surprise Removal", result="PASS", error_code=0x0, name="SATA_Hotplug_Surprise_Removal_Silicon") 
		report.as_html(basename+".report.html", online=True) 
		sys.exit(0)
	else:
		print("FAILED: All SATA devices failed to run HotPlug Surprise Removal for %d cycle" %args.cyclehotplug)
		print_to_stderr("FAILED: All SATA devices not pulled or not plugged back for %d cycle" %args.cyclehotplug)
		report.create_insight('SW.CONTENT', message = "FAILED: All SATA devices not pulled or not pluged back", result="FAIL", error_code=0x1, name="SATA_Hotplug_Surprise_Removal_Silicon")  
		report.as_html(basename+".report.html", online=True)
		sys.exit(1)
		
		

if __name__== "__main__":
    main()   