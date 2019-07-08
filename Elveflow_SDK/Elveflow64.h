#include "extcode.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef uint16_t  Z_regulator_type;
#define Z_regulator_type_none 0
#define Z_regulator_type__0_200_mbar 1
#define Z_regulator_type__0_2000_mbar 2
#define Z_regulator_type__0_8000_mbar 3
#define Z_regulator_type_m1000_1000_mbar 4
#define Z_regulator_type_m1000_6000_mbar 5
typedef uint16_t  Z_sensor_type;
#define Z_sensor_type_none 0
#define Z_sensor_type_Flow_1_5_muL_min 1
#define Z_sensor_type_Flow_7_muL_min 2
#define Z_sensor_type_Flow_50_muL_min 3
#define Z_sensor_type_Flow_80_muL_min 4
#define Z_sensor_type_Flow_1000_muL_min 5
#define Z_sensor_type_Flow_5000_muL_min 6
#define Z_sensor_type_Press_70_mbar 7
#define Z_sensor_type_Press_340_mbar 8
#define Z_sensor_type_Press_1_bar 9
#define Z_sensor_type_Press_2_bar 10
#define Z_sensor_type_Press_7_bar 11
#define Z_sensor_type_Press_16_bar 12
#define Z_sensor_type_Level 13
typedef uint16_t  Z_Sensor_digit_analog;
#define Z_Sensor_digit_analog_Analog 0
#define Z_Sensor_digit_analog_Digital 1
typedef uint16_t  Z_Sensor_FSD_Calib;
#define Z_Sensor_FSD_Calib_H2O 0
#define Z_Sensor_FSD_Calib_IPA 1
typedef uint16_t  Z_D_F_S_Resolution;
#define Z_D_F_S_Resolution__9Bit 0
#define Z_D_F_S_Resolution__10Bit 1
#define Z_D_F_S_Resolution__11Bit 2
#define Z_D_F_S_Resolution__12Bit 3
#define Z_D_F_S_Resolution__13Bit 4
#define Z_D_F_S_Resolution__14Bit 5
#define Z_D_F_S_Resolution__15Bit 6
#define Z_D_F_S_Resolution__16Bit 7

/*!
 * Elveflow Library
 * AF1 Device
 * 
 * IInitiate the AF1 device using device name (could be obtained in NI MAX), 
 * and regulator, and sensor. It return the AF1 ID (number >=0) to be used 
 * with other function 
 */
int32_t __cdecl AF1_Initialization(char Device_Name[], 
	Z_regulator_type Pressure_Regulator, Z_sensor_type Sensor, 
	int32_t *AF1_ID_out);
/*!
 * Elveflow Library
 * Sensor Reader or Flow Reader Device
 * 
 * Initiate the F_S_R device using device name (could be obtained in NI MAX) 
 * and sensors. It return the F_S_R ID (number >=0) to be used with other 
 * function. 
 * NB: Flow reader can only accept Flow sensor
 * NB 2: Sensor connected to channel 1-2 and 3-4 should be the same type 
 * otherwise they will not be taken into account and the user will be informed 
 * by a prompt message.
 */
int32_t __cdecl F_S_R_Initialization(char Device_Name[], 
	Z_sensor_type Sens_Ch_1, Z_sensor_type Sens_Ch_2, Z_sensor_type Sens_Ch_3, 
	Z_sensor_type Sens_Ch_4, int32_t *F_S_Reader_ID_out);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Initiate the MUX device using device name (could be obtained in NI MAX). It 
 * return the F_S_R ID (number >=0) to be used with other function
 */
int32_t __cdecl MUX_Initialization(char Device_Name[], int32_t *MUX_ID_out);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Valves are set by a array of 16 element. If the valve value is equal or 
 * below 0, valve is close, if it's equal or above 1 the valve is open. The 
 * index in the array indicate the selected  valve as shown below : 
 * 0   1   2   3
 * 4   5   6   7
 * 8   9   10  11
 * 12  13  14  15
 * If the array does not contain exactly 16 element nothing happened
 * 
 */
int32_t __cdecl MUX_Set_all_valves(int32_t MUX_ID_in, 
	int32_t array_valve_in[], int32_t len);
/*!
 * Elveflow Library
 * MUXDistributor Device
 * 
 * Initiate the MUX Distributor device using device com port (ASRLXXX::INSTR 
 * where XXX is the com port that could be found in windows device manager). 
 * It return the MUX Distributor ID (number >=0) to be used with other 
 * function
 */
int32_t __cdecl MUX_Dist_Initialization(char Visa_COM[], 
	int32_t *MUX_Dist_ID_out);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Initialize the OB1 device using device name and regulators type (see SDK 
 * Z_regulator_type for corresponding numbers). It modify the OB1 ID (number 
 * >=0). This ID can be used be used with other function to identify the 
 * targed OB1. If an error occurs during the initialization process, the OB1 
 * ID value will be -1. 
 */
int32_t __cdecl OB1_Initialization(char Device_Name[], 
	Z_regulator_type Reg_Ch_1, Z_regulator_type Reg_Ch_2, 
	Z_regulator_type Reg_Ch_3, Z_regulator_type Reg_Ch_4, int32_t *OB1_ID_out);
/*!
 * Elveflow Library
 * OB1-AF1 Device
 * 
 * Set default Calib in Calib cluster, len is the Calib_Array_out array length
 */
int32_t __cdecl Elveflow_Calibration_Default(double Calib_Array_out[], 
	int32_t len);
/*!
 * Elveflow Library
 * OB1-AF1 Device
 * 
 * Load the calibration file located at Path and returns the calibration 
 * parameters in the Calib_Array_out. len is the Calib_Array_out array length. 
 * The function asks the user to choose the path if Path is not valid, empty 
 * or not a path. The function indicate if the file was found.
 */
int32_t __cdecl Elveflow_Calibration_Load(char Path[], 
	double Calib_Array_out[], int32_t len);
/*!
 * Elveflow Library
 * OB1-AF1 Device
 * 
 * Save the Calibration cluster in the file located at Path. len is the 
 * Calib_Array_in array length. The function prompt the user to choose the 
 * path if Path is not valid, empty or not a path.
 */
int32_t __cdecl Elveflow_Calibration_Save(char Path[], 
	double Calib_Array_in[], int32_t len);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Launch OB1 calibration and return the calibration array. Before 
 * Calibration, ensure that ALL channels are proprely closed with adequate 
 * caps. 
 * Len correspond to the Calib_array_out length.
 */
int32_t __cdecl OB1_Calib(int32_t OB1_ID_in, double Calib_array_out[], 
	int32_t len);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * 
 * Get the pressure of an OB1 channel. 
 * 
 * Calibration array is required (use Set_Default_Calib if required) and 
 * return a double . Len correspond to the Calib_array_in length. 
 * 
 * If Acquire_data is true, the OB1 acquires ALL regulator AND ALL analog 
 * sensor value. They are stored in the computer memory. Therefore, if several 
 * regulator values (OB1_Get_Press) and/or sensor values (OB1_Get_Sens_Data) 
 * have to be acquired simultaneously, set the Acquire_Data to true only for 
 * the First function. All the other can used the values stored in memory and 
 * are almost instantaneous. 
 */
int32_t __cdecl OB1_Get_Press(int32_t OB1_ID, int32_t Channel_1_to_4, 
	int32_t Acquire_Data1True0False, double Calib_array_in[], double *Pressure, 
	int32_t Calib_Array_len);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Set the pressure of the OB1 selected channel, Calibration array is required 
 * (use Set_Default_Calib if required). Len correspond to the Calib_array_in 
 * length.
 */
int32_t __cdecl OB1_Set_Press(int32_t OB1_ID, int32_t Channel_1_to_4, 
	double Pressure, double Calib_array_in[], int32_t Calib_Array_len);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Launch AF1 calibration and return the calibration array. Len correspond to 
 * the Calib_array_out length.
 */
int32_t __cdecl AF1_Calib(int32_t AF1_ID_in, double Calib_array_out[], 
	int32_t len);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Get the pressure of the AF1 device, Calibration array is required (use 
 * Set_Default_Calib if required). Len correspond to the Calib_array_in 
 * length.
 */
int32_t __cdecl AF1_Get_Press(int32_t AF1_ID_in, int32_t Integration_time, 
	double Calib_array_in[], double *Pressure, int32_t len);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Set the pressure of the AF1 device, Calibration array is required (use 
 * Set_Default_Calib if required).Len correspond to the Calib_array_in length.
 * 
 */
int32_t __cdecl AF1_Set_Press(int32_t AF1_ID_in, double Pressure, 
	double Calib_array_in[], int32_t len);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Close communication with OB1
 */
int32_t __cdecl OB1_Destructor(int32_t OB1_ID);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Read the sensor of the requested channel. ! This Function only convert data 
 * that are acquired in OB1_Acquire_data
 * Units : Flow sensor µl/min
 * Pressure : mbar
 * 
 * If Acquire_data is true, the OB1 acquires ALL regulator AND ALL analog 
 * sensor value. They are stored in the computer memory. Therefore, if several 
 * regulator values (OB1_Get_Press) and/or sensor values (OB1_Get_Sens_Data) 
 * have to be acquired simultaneously, set the Acquire_Data to true only for 
 * the First function. All the other can used the values stored in memory and 
 * are almost instantaneous. For Digital Sensor, that required another 
 * communication protocol, this parameter have no impact
 * 
 * NB: For Digital Flow Senor, If the connection is lots, OB1 will be reseted 
 * and the return value will be zero
 */
int32_t __cdecl OB1_Get_Sens_Data(int32_t OB1_ID, int32_t Channel_1_to_4, 
	int32_t Acquire_Data1True0False, double *Sens_Data);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Get the trigger of the OB1 (0 = 0V, 1 =3,3V)
 */
int32_t __cdecl OB1_Get_Trig(int32_t OB1_ID, int32_t *Trigger);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Set the trigger of the OB1 (0 = 0V, 1 =3,3V)
 */
int32_t __cdecl OB1_Set_Trig(int32_t OB1_ID, int32_t trigger);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Close Communication with AF1
 */
int32_t __cdecl AF1_Destructor(int32_t AF1_ID_in);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Get the Flow rate from the flow sensor connected on the AF1
 */
int32_t __cdecl AF1_Get_Flow_rate(int32_t AF1_ID_in, double *Flow);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Get the trigger of the AF1 device (0=0V, 1=5V).
 * 
 */
int32_t __cdecl AF1_Get_Trig(int32_t AF1_ID_in, int32_t *trigger);
/*!
 * Elveflow Library
 * AF1 Device
 * 
 * Set the Trigger of the AF1 device (0=0V, 1=5V).
 */
int32_t __cdecl AF1_Set_Trig(int32_t AF1_ID_in, int32_t trigger);
/*!
 * Elveflow Library
 * Sensor Reader or Flow Reader Device
 * 
 * Close Communication with F_S_R.
 */
int32_t __cdecl F_S_R_Destructor(int32_t F_S_Reader_ID_in);
/*!
 * Elveflow Library
 * Sensor Reader or Flow Reader Device
 * 
 * Get the data from the selected channel.
 */
int32_t __cdecl F_S_R_Get_Sensor_data(int32_t F_S_Reader_ID_in, 
	int32_t Channel_1_to_4, double *output);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Close the communication of the MUX device
 */
int32_t __cdecl MUX_Destructor(int32_t MUX_ID_in);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Get the trigger of the MUX device (0=0V, 1=5V).
 */
int32_t __cdecl MUX_Get_Trig(int32_t MUX_ID_in, int32_t *Trigger);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Set the state of one valve of the instrument. The desired valve is 
 * addressed using Input and Output parameter which corresponds to the 
 * fluidics inputs and outputs of the instrument. 
 */
int32_t __cdecl MUX_Set_indiv_valve(int32_t MUX_ID_in, int32_t Input, 
	int32_t Ouput, int32_t OpenClose);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Set the Trigger of the MUX device (0=0V, 1=5V).
 */
int32_t __cdecl MUX_Set_Trig(int32_t MUX_ID_in, int32_t Trigger);
/*!
 * Elveflow Library
 * MUXDistributor Device
 * 
 * Close Communication with MUX distributor device
 */
int32_t __cdecl MUX_Dist_Destructor(int32_t MUX_Dist_ID_in);
/*!
 * Elveflow Library
 * MUXDistributor Device
 * 
 * Get the active valve
 */
int32_t __cdecl MUX_Dist_Get_Valve(int32_t MUX_Dist_ID_in, 
	int32_t *selected_Valve);
/*!
 * Elveflow Library
 * MUXDistributor Device
 * 
 * Set the active valve
 */
int32_t __cdecl MUX_Dist_Set_Valve(int32_t MUX_Dist_ID_in, 
	int32_t selected_Valve);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Add sensor to OB1 device. Select the channel n° (1-4) the sensor type. 
 * 
 * For Flow sensor, the type of communication (Analog/Digital), the 
 * Calibration for digital version (H20 or IPA) should be specify as well as 
 * digital resolution (9 to 16 bits). (see SDK user guide,  Z_sensor_type_type 
 * , Z_sensor_digit_analog, Z_Sensor_FSD_Calib and Z_D_F_S_Resolution for 
 * number correspondance)
 * 
 * For digital version, the sensor type is automatically detected during this 
 * function call. 
 * 
 * For Analog sensor, the calibration parameters is not taken into account. 
 * 
 * If the sensor is not compatible with the OB1 version, or no digital sensor 
 * are detected an error will be thrown as output of the function.
 */
int32_t __cdecl OB1_Add_Sens(int32_t OB1_ID, int32_t Channel_1_to_4, 
	Z_sensor_type SensorType, Z_Sensor_digit_analog DigitalAnalog, 
	Z_Sensor_FSD_Calib FSens_Digit_Calib, 
	Z_D_F_S_Resolution FSens_Digit_Resolution);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Close Communication with BFS device
 */
int32_t __cdecl BFS_Destructor(int32_t BFS_ID_in);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Initiate the BFS device using device com port (ASRLXXX::INSTR where XXX is 
 * the com port that could be found in windows device manager). It return the 
 * BFS ID (number >=0) to be used with other function 
 */
int32_t __cdecl BFS_Initialization(char Visa_COM[], int32_t *BFS_ID_out);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Get fluid density (in g/L) for the BFS defined by the BFS_ID
 */
int32_t __cdecl BFS_Get_Density(int32_t BFS_ID_in, double *Density);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Measure thefluid flow in (microL/min). !!! This function required an 
 * earlier density measurement!!! The density can either be measured only once 
 * at the beginning of the experiment (ensure that the fluid flow through the 
 * sensor prior to density measurement), or before every flow measurement if 
 * the density might change. If you get +inf or -inf, the density wasn't 
 * correctly measured. 
 */
int32_t __cdecl BFS_Get_Flow(int32_t BFS_ID_in, double *Flow);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Get the fluid temperature (in °C) of the BFS defined by the BFS_ID
 */
int32_t __cdecl BFS_Get_Temperature(int32_t BFS_ID_in, double *Temperature);
/*!
 * Elveflow Library
 * BFS Device
 * 
 * Elveflow Library
 * BFS Device
 * 
 * Set the instruement Filter. 0.000001= maximum filter -> slow change but 
 * very low noise.  1= no filter-> fast change but noisy. 
 * 
 * Default value is 0.1  
 */
int32_t __cdecl BFS_Set_Filter(int32_t BFS_ID_in, double Filter_value);
/*!
 * Elveflow Library - ONLY FOR ILLUSTRATION - 
 * OB1 and AF1 Devices
 * 
 * This function is only provided for illustration purpose, to explain how to 
 * do your own feedback loop. Elveflow does not guarante neither efficient nor 
 * optimum regulation with this illustration of PI regulator . With this 
 * function the PI parameters have to be tuned for every regulator and every 
 * microfluidic circuit.   
 * 
 * In this function need to be initiate with a first call where PID_ID =-1. 
 * The PID_out will provide the new created PID_ID. This ID should be use in 
 * further call. 
 * 
 * General remarks of this PI regulator :
 * 
 * The error "e" is calculate for every step as e=target value-actual value
 * There are 2 contributions to a PI regulator: proportional contribution 
 * which only depend on this step and  Prop=e*P and integral part which is the 
 * "memory" of the regulator. This value is calculated as 
 * Integ=integral(I*e*dt) and can be reset. 
 *   
 */
int32_t __cdecl Elveflow_EXAMPLE_PID(int32_t PID_ID_in, double actualValue, 
	int32_t Reset, double P, double I, int32_t *PID_ID_out, double *value);
/*!
 * Elveflow Library
 * Mux Device
 * 
 * Valves are set by a array of 16 element. If the valve value is equal or 
 * below 0, valve is close, if it's equal or above 1 the valve is open. If the 
 * array does not contain exactly 16 element nothing happened
 * 
 */
int32_t __cdecl MUX_Wire_Set_all_valves(int32_t MUX_ID_in, 
	int32_t array_valve_in[], int32_t len);
/*!
 * Elveflow Library
 * OB1 Device
 * 
 * Set the pressure of all the channel of the selected OB1. Calibration array 
 * is required (use Set_Default_Calib if required). Calib_Array_Len correspond 
 * to the Calib_array_in length. It uses an array as pressures input. 
 * Pressure_Array_Len corresponds to the the pressure input array. The first 
 * number of the array correspond to the first channel, the seconds number to 
 * the seconds channels and so on. All the number above 4 are not taken into 
 * account. 
 * 
 * If only One channel need to be set, use OB1_Set_Pressure.
 */
int32_t __cdecl OB1_Set_All_Press(int32_t OB1_ID, double Pressure_array_in[], 
	double Calib_array_in[], int32_t Pressure_Array_Len, int32_t Calib_Array_Len);
/*!
 * BFS_Zeroing
 */
int32_t __cdecl BFS_Zeroing(int32_t BFS_ID_in);

MgErr __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

#ifdef __cplusplus
} // extern "C"
#endif

