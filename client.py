import socket

HOST = 'localhost'
PORT = 12345

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((HOST, PORT))
            print(f"[CLIENT] Conectat la serverul {HOST}:{PORT}")
        except Exception as e:
            print(f"[EROARE] Nu m-am putut conecta la server: {e}")
            return

        while True:
            command = input("Introdu comanda (LOCK/RELEASE nume_semafor sau EXIT): ").strip()
            if command.upper() == "EXIT":
                print("[CLIENT] Închidere conexiune.")
                break

            sock.sendall(command.encode())

            try:
                response = sock.recv(1024).decode()
                if not response:
                    print("[CLIENT] Serverul a închis conexiunea.")
                    break
                print(f"[SERVER] {response.strip()}")
            except Exception as e:
                print(f"[EROARE] La primirea răspunsului: {e}")
                break

if __name__ == "__main__":
    main()
