import pyvisa

class InstrumentConnection:
    def __init__(self, resource_name, timeout=10000):
        self.connection = None
        self.timeout = timeout
        self.resource_name = resource_name
        self.resource_type = resource_name[resource_name.rfind("::") + 2:]
        self.ip = resource_name[
                  resource_name.find("::") + 2: resource_name.find("::", resource_name.find("::") + 1)]
        self.port = resource_name[resource_name.find(self.ip) + len(self.ip) + 2: resource_name.find("::",
                    resource_name.find(self.ip) + len(self.ip) + 1)]

    def connect(self):
        if self.resource_type == "INSTR":
            # self.connection = InstrumentVisaConnection().connect(self.resource_name, self.timeout)
            return InstrumentVisaConnection(self.resource_name, self.timeout)
        else:
            print("ResourceType undefined ; it must be INSTR")
            raise ResourceWarning

class InstrumentVisaConnection:

    def __init__(self, resource_name, timeout):
        self.resource_name = resource_name
        self.timeout = timeout
        self.q_response = None
        self.shockline_visa = None
        self.rm = pyvisa.ResourceManager()
        self.connect()
        self.shockline_visa.timeout = timeout

    def connect(self):
        try:
            self.shockline_visa = self.rm.open_resource(self.resource_name)
        except Exception as e:
            print("Failed to initialize VISA connection, message error is :\n")
            print(e)

    def write(self, w_command):
        try:
            self.shockline_visa.write(w_command)
        except Exception as e:
            print(f'Failed to write command "{w_command}", message error is :\n')
            print(e)

    def query(self, q_command):
        self.q_response = self.shockline_visa.query(q_command)
        return self.q_response.rstrip()

    def close(self):
        try:
            self.shockline_visa.close()
            self.rm.close()
        except Exception as e:
            print("Failed to disconnect VISA connection, message error is :\n")
            print(e)

def main(address, timeout):

    # 0. Instrument connection
    shockline_instrument = InstrumentConnection(address, timeout).connect()

    # 1. Read Instrument type
    instrument_info = shockline_instrument.query("*IDN?")
    instrument_family_number = instrument_info[12]
    print(instrument_info)
    print(f"Instrument belongs to the {instrument_family_number}00's family")

    # 2. System Preset
    # shockline_instrument.write(":SYST:PRES")

    # 3. Define 4 traces - S11, S21, S12 & S22
    shockline_instrument.write(":CALC1:PAR:COUN 4")

    shockline_instrument.write(":CALC1:PAR1:DEF S11")
    shockline_instrument.write(":CALC1:PAR2:DEF S21")
    shockline_instrument.write(":CALC1:PAR3:DEF S12")
    shockline_instrument.write(":CALC1:PAR4:DEF S22")

    # 4. Define LOG MAG response
    shockline_instrument.write(":CALC1:PAR1:FORM MLOG")
    shockline_instrument.write(":CALC1:PAR2:FORM MLOG")
    shockline_instrument.write(":CALC1:PAR3:FORM MLOG")
    shockline_instrument.write(":CALC1:PAR4:FORM MLOG")

    # 5. Set frequency range 1GHz - 4GHz
    # can also use :SENS1:FREQ:STAR 1e9
    # :SENS1:FREQ:CTOP 4e9
    shockline_instrument.write(":SENS1:FREQ:SPAN 3e9") 
    shockline_instrument.write(":SENS1:FREQ:CENT 2.5e9") # Read(Query) instead of write 

    # 6. Set 501 points
    shockline_instrument.write(":SENS1:SWE:POIN 501")

    # 7. Set 100KHz IFBW
    shockline_instrument.write(":SENS1:BAND 1E5")

    # 8. Set instrument on Hold
    shockline_instrument.write(":SENS1:HOLD:FUNC HOLD")
    opc_done = shockline_instrument.query("*OPC?")
    # 9. Perform a SOLT calibration
    # shockline_instrument.write(":SENS1:CORR:COLL:METH SOLT")
    # calibration_method = shockline_instrument.query(":SENS1:CORR:COLL:METH?")
    # print(f"The Calibration method used is: {calibration_method}")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT12:FULL2")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT1:CONN CFKT")
    # connector_type_port_1 = shockline_instrument.query(":SENS1:CORR:COLL:PORT1:CONN?")
    # print(f"Port1 Connector set to: {connector_type_port_1}")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT2:CONN CFKT")
    # connector_type_port_2 = shockline_instrument.query(":SENS1:CORR:COLL:PORT2:CONN?")
    # print(f"Port2 Connector set to: {connector_type_port_2}")
    # input("Please connect the LOAD to port 1 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT1:LOAD")
    # input("Please connect the OPEN to port 1 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT1:OPEN")
    # input("Please connect the SHORT to port 1 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT1:SHORT")
    # input("Please connect the LOAD to port 2 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT2:LOAD")
    # input("Please connect the OPEN to port 2 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT2:OPEN")
    # input("Please connect the SHORT to port 2 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT2:SHORT")
    # input("Please connect a THRU between port 1 and port 2 and press ENTER to continue")
    # shockline_instrument.write(":SENS1:CORR:COLL:PORT12:THRU")
    # shockline_instrument.write(":SENS1:CORR:COLL:SAVE")
    # opc_done = shockline_instrument.query("*OPC?")  # OPC = "Operation Complete Query"; Program flow is allowed to
    # proceed to the next command in the input buffer.
    if not (opc_done == "1"):
        print(f"Error, Opc returned unexpected value while waiting for calibration to finish (expected '1', received {opc_done}); ending code execution.")
        shockline_instrument.close()
        exit()
    input("Please connect DUT and press ENTER to continue")

    # 10. Perform a sweep and wait until done
    shockline_instrument.write(":TRIG:SING")
    shockline_instrument.query("*OPC?")
    if not (opc_done == "1"):
        print(f"Error, Opc returned unexpected value while waiting for a single sweep to finish (expected '1', received {opc_done}); ending code execution.")
        shockline_instrument.close()
        exit()

    # 11. Read Frequency list
    print("Frequency list")
    frequency_data_query = shockline_instrument.query(":SENS1:FREQ:DATA?")
    print(frequency_data_query)

    # 12. Read S Parameters
    print("Param 1 - S11 - SData")
    s11_sdata_query = shockline_instrument.query(":CALC1:PAR1:DATA:SDAT?")  # Reading S-data from trace 1 - S11
    print(s11_sdata_query)
    print("Param 2 - S21 - SData")
    s21_sdata_query = shockline_instrument.query(":CALC1:PAR2:DATA:SDAT?")  # Reading S-data from trace 2 - S21
    print(s21_sdata_query)
    print("Param 3 - S12 - SData")
    s12_sdata_query = shockline_instrument.query(":CALC1:PAR3:DATA:SDAT?")  # Reading S-data from trace 3 - S12
    print(s12_sdata_query)
    print("Param 4 - S22 - SData")
    s22_sdata_query = shockline_instrument.query(":CALC1:PAR4:DATA:SDAT?")  # Reading S-data from trace 4 - S22
    print(s22_sdata_query)

    # 13. Read Formatted data
    # print("Param 1 - S11 - FData")
    # s11_fdata_query = shockline_instrument.query(":CALC1:PAR1:DATA:FDAT?")  # Reading F-data from trace 1 - S11
    # print(s11_fdata_query)
    # print("Param 2 - S21 - FData")
    # s21_fdata_query = shockline_instrument.query(":CALC1:PAR2:DATA:FDAT?")  # Reading F-data from trace 2 - S21
    # print(s21_fdata_query)
    # print("Param 3 - S12 - FData")
    # s12_fdata_query = shockline_instrument.query(":CALC1:PAR3:DATA:FDAT?")  # Reading F-data from trace 3 - S12
    # print(s12_fdata_query)
    # print("Param 4 - S22 - FData")
    # s22_fdata_query = shockline_instrument.query(":CALC1:PAR4:DATA:FDAT?")  # Reading F-data from trace 4 - S22
    # print(s22_fdata_query)



    # 14. Connection closing
    shockline_instrument.close()


if __name__ == "__main__":
    # main(address="TCPIP0::127.0.0.1::5001::SOCKET", timeout=20000)
    main(address="TCPIP0::127.0.0.1::inst0::INSTR", timeout=20000)