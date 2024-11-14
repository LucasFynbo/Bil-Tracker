import network
import socket
import sys
import time

ssid_value:str = None
pass_value:str = None

class AccessPoint:
    def __init__(self):
        self.ssid = "Tracker Setup"
        self.password = "Wpa2Pskx31!"
    
    def activate(self):
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        time.sleep(2)
        ap.config(essid=self.ssid,password=self.password, authmode=4) 
        ap.config(max_clients=254)
        ap.config(dhcp_hostname="tracker")

        ap.ifconfig(('10.0.0.1', '255.255.255.0', '10.0.0.1', '10.0.0.1'))

        while ap.active() == False:
            time.sleep(0.5)
            pass

        print('WiFi started')
        status = ap.ifconfig()
        print('IP address = ' + status[0])
        print('subnet mask = ' + status[1])
        print('gateway  = ' + status[2])
        print('DNS server = ' + status[3])

class WebSocket:
    def __init__(self):
        self.serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host: str = '10.0.0.1'
        port: int = 80
        
        try:
            self.serv_sock.bind((host, port))
            sys.stdout.write('Listeng on %s:%d' % (host, port))
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                sys.stdout.write('[i] Address is already in use. Waiting for it to be released...')
                self.serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.serv_sock.bind((host, port))  # Prøver at binde igen på den genbrugte adresse.
                sys.stdout.write('[i] Listeng on %s:%d' % (host, port))
            else:
                sys.stdout.write('[!] Socket Error: %s' % (e))
        
        self.serv_sock.listen(1)
        
    def accept_connection(self):
        client_socket, client_addr = self.serv_sock.accept()

        try:
            self.handle_client(client_socket)
        except Exception as e:
            sys.stdout.write('[!] Error handling client: %s' % (e))
        finally:
            client_socket.close()

    def handle_client(self, client_socket):
        global ssid_value, pass_value
        
        request = client_socket.recv(1024).decode('utf8')
        cut_req = request.split(' ')[1]
        
        client_socket.send(b'HTTP/1.1 200 OK\r\n')
        
        # Printer den spurgte path
        sys.stdout.write('Full req: %s \nReq Path: %s' % (request, cut_req))

        if "POST" in request:
            post_data_start = request.find("\r\n\r\n") + 4
            post_data = request[post_data_start:]

            data_pairs = post_data.split('&')
            

            for pair in data_pairs:
                key, value = pair.split('=')
                if key == "ssid":
                    ssid_value = value
                elif key == "pass":
                    pass_value = value

            print("Received ssid:", ssid_value)
            print("Received pass:", pass_value)

            with open('network_credentials.txt', 'w') as file:
                file.write(f"SSID:{ssid_value}\nPASS:{pass_value}")

            
        # Hvis klienten spørger efter index.html (det samme som '/').
        if cut_req == '/':
            
            # html variablet (html variablet holder en kopi af vores index.html fil).
            website_indexfile = './ConnectionPage/index.html'
            with open(website_indexfile, 'r') as f:
                html = f.read()     
                html = html.encode('utf-8')
                
            # Vi sender derefter vores Content-Type og fortæller klienten at vi vil sende html til den.
            client_socket.send(b'Content-Type: text/html\r\n')
            
            # Regner længden ud på vores html. Dette giver et integer værdi af hvor mange karakterer vores html dokument indeholder. 
            html_len = len(html)
            html_len_b = str(html_len).encode('utf-8')	# Encoder det til et byte objekt så vi kan concatenate det sammen med vores Content-Length header vi sender på linjen nedenfor. 
            client_socket.send(b'Content-Length: ' + html_len_b + b'\r\n')	# Vi bruger Content-Length til at give besked til klienten at den nu modtager en fil på den specificerede længde
            client_socket.send(b'\r\n')
            client_socket.send(html)	# Sender vores index.html til klienten.
        
        # Hvis klienten ikke spørger om '/' vil dette else statement blive udført.
        else:
            
            # Vi sender bare Content-Type headeren til klienten og resten af vores HTTP headers bliver udført længere nede i koden.
            if cut_req.endswith('.js'):
                client_socket.send(b'Content-Type: text/javascript\r\n')
            elif cut_req.endswith('.css'):
                client_socket.send(b'Content-Type: text/css\r\n')
            elif cut_req.endswith('.otf'):
                client_socket.send(b'Content-Type: font/otf\r\n')
            elif cut_req.endswith('.ico'):
                client_socket.send(b'Content-Type: image/x-icon\r\n')
            else:
                client_socket.send(b'None')
            
            # Da klienten sender en GET request med en path på favicon der er anderledes fra vores folder struktur, bliver vi nød til at behandle denne GET request anderledes.
            if cut_req.endswith('.ico'):
                favicon_path = './ConnectionPage/favicon.ico'
                with open(favicon_path, 'rb') as f:
                    favicon = f.read()
                
                favicon_len = len(favicon)
                favicon_len_b = str(favicon_len).encode('utf-8')
                client_socket.send(b'Content-Length: ' + favicon_len_b + b'\r\n')
                client_socket.send(favicon)
                
            # Hvis det ikke er favicon kører vi dette else statement.  
            else:
                with open("."+cut_req, 'rb') as f:
                    file_get = f.read()
                
                # Sender de sidste HTTP headers og derefter vores fil til klienten.
                content_len = len(file_get)
                content_len_b = str(content_len).encode('utf-8')
                client_socket.send(b'Content-Length: ' + content_len_b + b'\r\n')
                client_socket.send(b'\r\n')
                client_socket.send(file_get)
            
        client_socket.close()

    def close(self):
        self.serv_sock.close()    
    
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
        

def trackerConnection(tracker_id):
    tracker_id = tracker_id
    AP = AccessPoint(tracker_id)
    AP.activate()
    
    web = WebSocket()
    
    while ssid_value == None and pass_value == None:
        web.accept_connection()
        
    print(ssid_value, pass_value)
    
    connect_to_wifi = ConnectHandler(ssid_value, pass_value)
    return connect_to_wifi.activate()

if __name__ == "__main__":
    trackerConnection("Tracker%1531")

