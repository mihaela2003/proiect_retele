import socket
import threading

HOST = 'localhost'
PORT = 12345

# Structura semafoarelor: { 'semafor1': {'holder': client_socket, 'queue': [client1, client2]} }
semaphores = {}
lock = threading.Lock()  # Protejăm accesul la dicționarul de semafoare


def handle_client(client_socket, address):
    print(f"[+] Client conectat: {address}")

    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break  # Clientul a închis conexiunea
            print(f"[{address}] Mesaj primit: {data}")
            parts = data.strip().split()

            if len(parts) != 2:
                client_socket.sendall(b"ERROR Comanda invalida\n")
                continue

            command, sem_name = parts

            with lock:
                if sem_name not in semaphores:
                    semaphores[sem_name] = {'holder': None, 'queue': []}

                sem = semaphores[sem_name]

                if command == "LOCK":
                    if sem['holder'] is None:
                        sem['holder'] = client_socket
                        client_socket.sendall(b"LOCK_GRANTED\n")
                        print(f"[{sem_name}] Acces acordat clientului {address}")
                    else:
                        sem['queue'].append(client_socket)
                        client_socket.sendall(b"LOCK_DENIED\n")
                        print(f"[{sem_name}] Clientul {address} adaugat in coada")

                elif command == "RELEASE":
                    if sem['holder'] == client_socket:
                        if sem['queue']:
                            next_client = sem['queue'].pop(0)
                            sem['holder'] = next_client
                            try:
                                next_client.sendall(f"LOCK_GRANTED\n".encode())
                            except:
                                sem['holder'] = None  # Clientul s-a deconectat
                        else:
                            sem['holder'] = None
                        client_socket.sendall(b"RELEASE_OK\n")
                        print(f"[{sem_name}] S-a eliberat semaforul de catre {address}")
                    else:
                        client_socket.sendall(b"RELEASE_DENIED\n")
    except Exception as e:
        print(f"[!] Eroare cu clientul {address}: {e}")
    finally:
        with lock:
            for sem_name, sem in semaphores.items():
                if sem['holder'] == client_socket:
                    if sem['queue']:
                        next_client = sem['queue'].pop(0)
                        sem['holder'] = next_client
                        try:
                            next_client.sendall(f"LOCK_GRANTED\n".encode())
                        except:
                            sem['holder'] = None
                    else:
                        sem['holder'] = None
                if client_socket in sem['queue']:
                    sem['queue'].remove(client_socket)

        client_socket.close()
        print(f"[-] Conexiune închisă: {address}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"[SERVER] Ascult pe {HOST}:{PORT}...")

    while True:
        client_socket, address = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, address), daemon=True)
        thread.start()


if __name__ == "__main__":
    start_server()
