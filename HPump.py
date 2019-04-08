"""
Class definition to control a Hardvard pump through UART serial communication
The class shares a COM port. This ennables to configure several pumps though a 
PUMP chai- Therefore it doesn't support multiple pumps connected directly to 
Computer

Version 1-04/04/19
Pollack Lzb- Ccornell University
Josue Ssn Emeterio
"""


import serial #needs serial- does import need to be elsewhere?


class HPump:
	
	
	#need a single serisl for the clsss
	pumpserial=serial.Serial()
	
	#Set port protperties
	pumpserial.baudrate=9600
	pumpserial.stopbits=2
	

	
	
	#function to initialize ports
	def setport(self,number,resource=pumpserial):
		if resource.is_open:
			resource.close()
		resource.port="COM"+str(number)
		#TODO: implent for things other than COM(num)
		
	
	#Pump intialization need pump number
	#need to set defsults fpr simpler impoementation
	def __init__(self,address="",running=False):
		self.address=address 
		self.running=running
		#add init for syringe dismeter,flowrate, Direction etc 
		
		
		
		
		
		
		
		
#Pump action commands 	 
#To do in all. Read in confirmstion from pump. 
	def startpump(self,resource=pumpserial):
		resource.open()
		resource.write((self.address+"RUN\n\r").encode()) #neets both terminators
		resource.close()
		self.running=True #Consider switching to after checking with pump
		return 1

	def	stoppump(self,resource=pumpserial):
		resource.open()
		resource.write((self.address+"STP\n\r").encode())
		resource.close()
		self.running=False #consider moving to after checking with pump
		return 0
		
	def setflowrate(self,rate,resource=pumpserial):
		#consider moving to after checking with pump
		resource.write((self.address+"RAT"+str(rate)+"UM/n/r").encode())
		#TODO: add possibillity to change units
		self.flowrate=rate #consider moving to after checking with pump
		return rate
		
#TODO: Add functions to querry pump- double check Diameter, fslowraate, and check volume
