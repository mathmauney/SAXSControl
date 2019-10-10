#include "Serial2/Serial2.h"
SYSTEM_MODE(MANUAL);


int argument1;
int argument2;
int argument3;
int argument4[32];
volatile bool state=true;
volatile bool statechanged=false;
LEDStatus blinkRed(RGB_COLOR_RED, LED_PATTERN_BLINK, LED_SPEED_NORMAL, LED_PRIORITY_IMPORTANT);
LEDStatus notconnected(RGB_COLOR_MAGENTA, LED_PATTERN_BLINK, LED_SPEED_SLOW);



 void setup() {
Serial.begin(9600); //begin Communication with computer 
Serial1.begin(9600);//beginserial to pump- Configuration trully calls for 8N2- however this is not supported in current device OS (Hardware does support though)
                    //to compensate we will use 120us delays after each byte. Single Threaded blocking used as precautions 
Serial2.begin(9600); //Set up secondary RS232 channel- Use for VICI valve: Future- Option to change baudrate?

Wire.setSpeed(20000);//Lower I2C speed. MXII needs lower than default 1k which can timeout with cable and high pullup
Wire.begin(); // Begin I2C connection 


RGB.mirrorTo(A2, A3, A4, false, true);
//Add a system interrupt to be able to do an override stop:
//Todo: Add function to stop all pumps.


pinMode(D3, INPUT_PULLUP);
delay(100);//Give time for debounce circuit capacitor to charge
attachInterrupt(D3,stopinterrupt,CHANGE);

//Led Control for sanity check 
}


void loop() {
    if(statechanged && !state){   //Function to stop pumps if the interrupt was detected. 
        stopall();
        statechanged=false;
    }
    
    
    notconnected.setActive(!Serial.isConnected()); 
    
    //Serial.println("This is sending things");
   // delay(500);
} //LEft empty... handling things in serialEvent loops

void serialEvent(){
    
    //Serial.println(r);
  if(state){  
    switch(Serial.read()){
        
        //set of commands for Rheodyne Valve through I2C-aka wire
        case 'P': //Switch valve command "Pxxxy" xxx=I2C address y=possition
            argument1=readnumber(3);
            argument2=Serial.read()-48;
            Serial.println(switchvalve(argument1,argument2));
            break;
            
        case 'S': //Valve Status command "Sxxx" xxx=!2C address
            argument1=readnumber(3);
            Serial.println(readpossition(argument1));
            break;
            
        case 'I': //Scan for available I2C Addresses
            i2cscanner();
            break;
            
        case 'N'://Reset I2C address
            argument1=readnumber(3);
            argument2=readnumber(3);
            setI2C(argument1,argument2);
            break;
        
        case 'F'://Forse set I2C address
            argument1=readnumber(3);
            if(argument1>16&&argument1<255){
            forcei2caddress(argument1);
            }
            break;
            
        
        //Command to syringe pump through Serial1
        case 'R':
            if(Serial.available()){
                argument1=Serial.read();
                argument2=Serial.read();
                runpumpaddress(argument1,argument2);
            }
            else{
            runpump();
            }
            break;
            
        case 'T':
            if(Serial.available()){
                argument1=Serial.read();
                argument2=Serial.read();
                stoppumpaddress(argument1,argument2);
            }
            else{            
            stoppump();
            }
            break;
            
        case 'V':
            if(Serial.available()){
                argument1=Serial.read();
                argument2=Serial.read();
                reverseaddress(argument1,argument2);
            }
            else{        
            reverse();
            }
            break;

        case 'E':
            if(Serial.available()){
                argument1=Serial.read();
                argument2=Serial.read();
                setinfuseaddress(argument1,argument2);
            }
            else{        
            setinfuse();
            }
            break;
            
        case 'L':
            if(Serial.available()){
                argument1=Serial.read();
                argument2=Serial.read();
                setrefilladdress(argument1,argument2);
            }
            else{            
            setrefill();
            }
            break;
            
        case 'Q':
            if(Serial.available()==7){
            for(int i=0;i<7;i++){
                argument3=Serial.read();
                argument4[i]=argument3;
            }
            setinfuserate(argument4);
            }      //No Address set 6 bit flowrate
            else if(Serial.available()==2){
                argument1=Serial.read();
                argument2=Serial.read();                
            askinfuserateaddress(argument1,argument2);    
            } //Ask pump with Address
            else if(Serial.available()==9){
                argument1=Serial.read();
                argument2=Serial.read();
                for(int i=0;i<7;i++){
                argument3=Serial.read();
                argument4[i]=argument3;
                }
            setinfuserateaddress(argument1,argument2,argument4);    
            } //Set rate for pump with address 
            else{
                askinfuserate();
            }                           //Ask without address
            break;
    
        case 'A':
            if(Serial.available()==7){
            for(int i=0;i<7;i++){
                argument3=Serial.read();
                argument4[i]=argument3;
            }
            setrefillrate(argument4);
            }      //No Address set 6 bit flowrate
            else if(Serial.available()==2){
                argument1=Serial.read();
                argument2=Serial.read();                
            askrefillrateaddress(argument1,argument2);    
            } //Ask pump with Address
            else if(Serial.available()==9){
                argument1=Serial.read();
                argument2=Serial.read();
                for(int i=0;i<7;i++){
                argument3=Serial.read();
                argument4[i]=argument3;
                }
            setrefillrateaddress(argument1,argument2,argument4);    
            } //Set rate for pump with address 
            else{
                askrefillrate();
            }                           //Ask without address
            break;
    
        case '-': //Sends Buffer to Serial1-- This function essentially makes the rest of the functions redundant.....
                argument1=Serial.available(); //Get buffersize to transmit
                for(int i=0;i<argument1;i++){  //Collect Buffer
                argument3=Serial.read();
                argument4[i]=argument3;
                }//Read Buffer
                
                SINGLE_THREADED_BLOCK(){        //This dissables thread switching and other OS processes that can affect the timing
                for(int i=0;i<argument1;i++){  //Send Buffer at the right stop bit and baudrate
                Serial1.write(argument4[i]); Serial1.flush();
                delayMicroseconds(120);
                }//Send Buffer
                }
                delay(100);
                while(Serial1.available()>0){
                    Serial.write(Serial1.read());
                }//Frompump
            break;

        case '+': //Sends Buffer to Serial2
                while(Serial.available()>0){
                    Serial2.write(Serial.read());
                }
                delay(100);
                while(Serial2.available()>0){
                    Serial.write(Serial2.read());
                }//Frompump
            break;
            
        case '!':
                stopall();
            break;
            
            
        default://Nothing happens
            Serial.println(-1);
            break;
        }
  }
  else{
      while(Serial.available()>0){
      Serial.read();
      }
      Serial.println("Stop Pressed- Command Ignored");
  }
}
//General functions
//Function to parse several bytes into one number
//Serial commands are parsed with 120us delay between bytes to make up for the missing stopbit 8N1->8N2
//SINGLE THREADED BLOCK is implemented as a precaution to ensure the transmission and delays are not interrupted. Works without it though. 
int readnumber(int size){
    int val=0;
    for(int i=0;i<size;i++){
        val=val*10+(Serial.read()-48);  //todo check it is actually a number 48-57=0-9 in ASCII
    }
    return val;
}

void stopinterrupt(){
    state=!state;
    statechanged=true;
    blinkRed.setActive(!state);
}

//TODO: Consider making pump address mandatory to reduce functions
//Syringe Pump Functions
void stopall(){
    Serial1.write(13);Serial1.flush(); //CR to stop pumps
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
}



//R
int runpump(){
    
//Send Command RUN. It needs to be brocken up with delay so that
SINGLE_THREADED_BLOCK(){
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("U");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("N");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
}


int runpumpaddress(int num1,int num2){
    
//Send Command RUN. It needs to be brocken up with delay so that 
SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);

    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("U");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("N");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

}
//T
int stoppump(){
//Send command STP
 SINGLE_THREADED_BLOCK(){
    Serial1.write("S");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("P");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
    
 }   
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

}
int stoppumpaddress(int num1,int num2){
//Send command STP
SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);
    

    Serial1.write("S");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("P");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

}
//V
int reverse(){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("E");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("V");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}
int reverseaddress(int num1,int num2){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);
    

    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("E");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("V");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}

//E
int setinfuse(){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("N");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}
int setinfuseaddress(int num1, int num2){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("N");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}
//L
int setrefill(){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("E");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}
int setrefilladdress(int num1, int num2){
    //Send command DIRREV-Reverse direction
 SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("D");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("I");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("E");Serial1.flush();
    delayMicroseconds(120);

    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
            
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\r");
}
    delay(100); //Give pump time to respond
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }

    
}
//Q -with options or no options
int setinfuserate(int input[]){
 SINGLE_THREADED_BLOCK(){   
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("A");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    for(byte i=0;i<7;i++){
        Serial1.write(input[i]);Serial1.flush();
        delayMicroseconds(120); 
    }
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    
 }    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int setinfuserateaddress(int num1, int num2, int input[]){
  SINGLE_THREADED_BLOCK(){  
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);    
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("A");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    for(byte i=0;i<7;i++){
        Serial1.write(input[i]);Serial1.flush();
        delayMicroseconds(120); 
    }
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    
  }
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int askinfuserate(){
   SINGLE_THREADED_BLOCK(){ 
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("A");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
   }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int askinfuserateaddress(int num1, int num2){
    SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("A");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("T");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
//A -with options or no options
int setrefillrate(int input[]){
    SINGLE_THREADED_BLOCK(){
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    for(byte i=0;i<7;i++){
        Serial1.write(input[i]);Serial1.flush();
        delayMicroseconds(120); 
    }
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int askrefillrate(){
    SINGLE_THREADED_BLOCK(){
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int setrefillrateaddress(int num1, int num2, int input[]){
    SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);    
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    for(byte i=0;i<7;i++){
        Serial1.write(input[i]);Serial1.flush();
        delayMicroseconds(120); 
    }
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}
int askrefillrateaddress(int num1, int num2){
    SINGLE_THREADED_BLOCK(){
    Serial1.write(num1);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write(num2);Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("F");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("R");Serial1.flush();
    delayMicroseconds(120);
    
    Serial1.write("\n");Serial1.flush();
    delayMicroseconds(120);
    Serial1.write("\r");
    }
    
    delay(100); //Give pump time to respond?
    while(Serial1.available()){
        Serial.write(Serial1.read());
    }
    
    
    
    
}




//Rheodyne functions
//Function to switch reodyne valve
//P
int switchvalve(int address,int pos) {
    Wire.beginTransmission(address/2);
    Wire.write(80);//80 is equivalent to P command
    Wire.write(pos);
    Wire.write(address^80^pos);
    int c=Wire.endTransmission();
    return c; 
}

//Funciton to change I2C address 
//TODO: Convince with Scan function
//N
int setI2C(int address, int addressnew){
    if(addressnew%2==0){
    Wire.beginTransmission(address/2);
    Wire.write(78);//80 is equivalent to P command
    Wire.write(addressnew);
    Wire.write(address^78^addressnew);
    int c=Wire.endTransmission();
    Serial.println("Address Changed");
    return c;
}
    else{
        Serial.println("Address not acepted");
        return -1;
    }
}

//Function to read possition from valve.
//S
int readpossition(int Address){
    int f=-1;
    Wire.beginTransmission(Address/2);
    Wire.write(83);//S command
    Wire.write(0);//Non Important byte
    Wire.write(Address^83^0);;
    int c=Wire.endTransmission();
    Wire.requestFrom(Address/2,2);
    
    while(Wire.available()){   // slave may send less than requested
    f = Wire.read();    // receive a byte as character         // print the character
  }
    return f; // I suppose I am only returning last value 
}

//Function to scan for available I2C Addresses
//I
int i2cscanner(){
	byte error, address;
	int nDevices;

	Serial.println("Scanning...");

	nDevices = 0;
	for(address = 1; address < 127; address++ )
	{
		// The i2c_scanner uses the return value of
		// the Write.endTransmisstion to see if
		// a device did acknowledge to the address.
		Wire.beginTransmission(address);
		error = Wire.endTransmission();

		if (error == 0)
		{
			Serial.print("I2C device found at address 0x");
			if (address<16)
				Serial.print("0");
			Serial.print(address,HEX);
			Serial.println("  !");

			nDevices++;
		}
		else if (error==4)
		{
			Serial.print("Unknow error at address 0x");
			if (address<16)
				Serial.print("0");
			Serial.println(address,HEX);
		}
	}
	if (nDevices == 0)
		Serial.println("No I2C devices found\n");
	else
		Serial.println("done\n");

	delay(5000);           // wait 5 seconds for next scan
}

//Change I2C adddress for connected pump
//F
int forcei2caddress(int newaddress){
    

	byte error, address;
	int nDevices;
	int change;

//	Serial.println("Scanning...");

	nDevices = 0;
	for(address = 1; address < 127; address++ )
	{
		// The i2c_scanner uses the return value of
		// the Write.endTransmisstion to see if
		// a device did acknowledge to the address.
		Wire.beginTransmission(address);
		error = Wire.endTransmission();

		if (error == 0)
		{
		    change=setI2C(address,newaddress); //use change its I2C address
			
			if(change!=-1){
			Serial.print("I2C device at address 0x");
			if (address<16)
				Serial.print("0");
			Serial.print(address,HEX);
			Serial.print("  has been changed to ");
			Serial.println(newaddress);

			nDevices++;
			}
		}
//		else if (error==4)
//		{
//			Serial.print("Unknow error at address 0x");
//			if (address<16)
//				Serial.print("0");
//			Serial.println(address,HEX);
//		}
	}
	
	
//	if (nDevices == 0)
//		Serial.println("No I2C devices found\n");
//	else
//		Serial.println("done\n");

//	delay(5000);           // wait 5 seconds for next scan

    
}



//Valco Functions:
//Todo