import network
import sys
import time

ssid_value:str = None
pass_value:str = None 
    
class ConnectHandler:
    def activate(ssid, password):
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        
        sta_if = network.WLAN(network.STA_IF)

        if not sta_if.isconnected():
            sta_if.active(True)
            
            try:
                sta_if.config(dhcp_hostname="tracker")
                sta_if.connect(ssid, password)
            except Exception as err:
                sta_if.active(False)
                print("Error:", err)
                sys.exit()
            print("Connecting", end="")
            n = 0
            while not sta_if.isconnected():
                print(".", end="")
                time.sleep(1)
                n += 1
                if n == 200:
                    break
            if n == 200:
                sta_if.active(False)
                print("\nGiving up! Not connected!")
                return ""
            else:
                print("\nNow connected with IP: ", sta_if.ifconfig()[0])
                return sta_if.ifconfig()[0]
        else:
            print("Already Connected. ", sta_if.ifconfig()[0])
            return sta_if.ifconfig()[0]


