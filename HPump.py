"""
Class definition to control a Hardvard pump through UART serial communication
The class shares a COM port. This ennables to configure several pumps though a
PUMP chai- Therefore it doesn't support multiple pumps connected directly to
Computer

Version 1-04/04/19
Pollack Lzb- Ccornell University
Josue San Emeterio
"""


import serial #needs serial- does import need to be elsewhere?


class HPump:


	#need a single serisl for the clsss
	pumpserial=serial.Serial()

	#Set port protperties
	pumpserial.baudrate=9600
	pumpserial.stopbits=2
	pumpserial.timeout=1



	#function to initialize ports
	def setport(self,number,resource=pumpserial):
		if resource.is_open:
			resource.close()
		resource.port="COM"+str(number)
		#TODO: implent for things other than COM(num)


	#Pump intialization need pump number
	#need to set defsults fpr simpler impoementation
	def __init__(self,address="",running=False,infusing=True):
		self.address=address
		self.running=running
		self.infusing=infusing
		#add init for syringe dismeter,flowrate, Direction etc








#Pump action commands
#To do in all. Read in confirmstion from pump.
	def startpump(self,resource=pumpserial):
		resource.open()
		resource.write((self.address+"RUN\n\r").encode()) #neets both terminators
		val=resource.read_until("\n\r")
		resource.close()
		self.running=True #Consider switching to after checking with pump
		return val.decode()

	def	stoppump(self,resource=pumpserial):
		resource.open()
		resource.write((self.address+"STP\n\r").encode())
		val=resource.read_until("\n\r")
		resource.close()
		self.running=False #consider moving to after checking with pump
		return val.decode()

	def setinfuserate(self,rate,units="UM",resource=pumpserial):
		#consider moving to after checking with pump
		ratestr=str(rate).zfill(5)
		resource.open()
		resource.write((self.address+"RAT"+ratestr+units+"\n\r").encode())
		val=resource.read(4)
		#TODO: add possibillity to change units
		self.infuserate=rate #consider moving to after checking with pump
		resource.close()
		return val.decode()


	def setrefillrate(self,rate,units="UM",resource=pumpserial):
		#consider moving to after checking with pump
		ratestr=str(rate).zfill(5)
		resource.open()
		resource.write((self.address+"RFR"+ratestr+units+"\n\r").encode())
		val=resource.read(4)
		#TODO: add possibillity to change units
		self.fillrate=rate #consider moving to after checking with pump
		resource.close()
		return val.decode()


	def setflowrate(self,rate,units="UM",resource=pumpserial):
		#Function to change the current flowrate whether infuse or withdraw
		if(self.infusing):
			return setinfuserate(rate,units)
		else:
			return setrefillrate(rate,units)


	def	sendcommand(self,command,resource=pumpserial): #sends an albitrary command
		resource.open()
		resource.write((command).encode())
		resource.close()

	def infuse(self):
		self.infusing=True
		resource.open()
		resource.write(b'DIRINF')
		resource.close()

	def refill(self):
		self.infusing=False
		resource.open()
		resource.write(b'DIRREF')
		resource.close()

	def reverse(self):
		self.infusing=(not self.infusing)
		resource.open()
		resource.write(b'DIRREV')
		resource.close()

	def setmodepump(self):
		resource.open()
		resource.write(b'MOD PMP')
		resource.close()

	def setmodevol(self):
		resource.open()
		resource.write(b'MOD PMP')
		resource.close()

	def setmodeprogam(self):
		resource.open()
		resource.write(b'MOD PMP')
		resource.close()

	def settargetvol(self,value):
		resource.open()
		resource.write(b'MOD PMP')
		resource.close()


#TODO: Add functions to querry pump- double check Diameter, fslowraate, and check volume
