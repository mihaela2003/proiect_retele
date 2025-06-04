import socket
import threading
import time

HOST = 'localhost'
PORT = 12345

class SemaphoreClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.username = ""
        self.running = True
    
    def connect(self):
        self.username = input("Introdu numele tau de utilizator: ").strip()
        if not self.username:
            print("[EROARE] Username-ul nu poate fi gol!")
            return False

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            print(f"[CLIENT] Conectat la serverul {HOST}:{PORT}")
            
            self.sock.sendall(f"USERNAME {self.username}".encode())
            self.connected = True
            
            receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receiver_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[EROARE] Nu m-am putut conecta la server: {e}")
            return False
    
    def receive_messages(self):
        while self.running and self.connected:
            try:
                response = self.sock.recv(4096).decode()
                if not response:
                    print("[CLIENT] Serverul a inchis conexiunea.")
                    self.connected = False
                    break
                
                lines = response.strip().split('\n')
                for line in lines:
                    if line.strip():
                        self.handle_server_message(line.strip())
                        
            except Exception as e:
                if self.running:
                    print(f"[EROARE] La primirea raspunsului: {e}")
                self.connected = False
                break
    
    def handle_server_message(self, message):
        if message == "PING":
            try:
                self.sock.sendall(b"PONG")
            except:
                pass
            return
        
        if message.endswith("_RESPONSE"):
            return 
        
        if message.startswith(("LOCK_GRANTED", "LOCK_DENIED", "RELEASE_OK", "RELEASE_DENIED")):
            print(f"\n[SERVER] {message}")
            self.show_prompt()
        elif message.startswith("ERROR"):
            print(f"\n[EROARE] {message[6:]}")  
            self.show_prompt()
        elif message.startswith(("LIST_RESPONSE", "INFO_RESPONSE", "STATS_RESPONSE", "HELP_RESPONSE")):
            pass
        else:
            lines = message.split('\\n')
            for line in lines:
                if line.strip():
                    print(f"[SERVER] {line}")
    
    def show_prompt(self):
        print("Comenzi disponibile: LOCK <nume>, RELEASE <nume>, INFO <nume>, LIST, STATS, HELP, EXIT")
        print("Introdu comanda: ", end="", flush=True)
    
    def send_command(self, command):
        if not self.connected:
            print("[EROARE] Nu esti conectat la server!")
            return False
        
        try:
            self.sock.sendall(command.encode())
            return True
        except Exception as e:
            print(f"[EROARE] Nu am putut trimite comanda: {e}")
            self.connected = False
            return False
    
    def wait_for_response(self, response_type, timeout=5):
        start_time = time.time()
        response_lines = []
        
        while time.time() - start_time < timeout:
            try:
                if not self.connected:
                    break
                    
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                
                lines = data.strip().split('\n')
                collecting = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line == response_type:
                        collecting = True
                        continue
                    
                    if collecting:
                        if line.startswith(("LOCK_", "RELEASE_", "ERROR", "LIST_RESPONSE", "INFO_RESPONSE", "STATS_RESPONSE", "HELP_RESPONSE")):
                            if line != response_type:
                                return '\n'.join(response_lines)
                        response_lines.append(line)
                
                if collecting and response_lines:
                    return '\n'.join(response_lines)
                    
            except:
                break
        
        return None
    
    def run(self):
        if not self.connect():
            return
        
        print(f"\n[CLIENT] Conectat cu succes ca '{self.username}'!")
        self.show_prompt()
        
        try:
            while self.running and self.connected:
                try:
                    command = input().strip()
                    
                    if not command:
                        continue
                    
                    if command.upper() == "EXIT":
                        print("[CLIENT] Inchidere conexiune.")
                        break
                    
                    cmd_upper = command.upper()
                    if cmd_upper in ["LIST", "STATS", "HELP"] or cmd_upper.startswith("INFO "):
                        if self.send_command(command):
                            time.sleep(0.5)
                        continue
                    
                    if self.send_command(command):
                        pass
                    
                except KeyboardInterrupt:
                    print("\n[CLIENT] Intrerupere de la tastatura.")
                    break
                except EOFError:
                    print("\n[CLIENT] Input inchis.")
                    break
                except Exception as e:
                    print(f"[EROARE] {e}")
                    
        finally:
            self.running = False
            self.connected = False
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            print("[CLIENT] Deconectat.")

def main():
    print("Conectare la server...")
    
    client = SemaphoreClient()
    client.run()

if __name__ == "__main__":
    main()