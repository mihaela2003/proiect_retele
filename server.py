import socket
import threading
import logging
import datetime
import time

HOST = 'localhost'
PORT = 12345

logging.basicConfig(
    filename=f'semaphore_server_{datetime.date.today()}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

semaphores = {}
clients = {} 
client_last_ping = {} 
lock = threading.Lock() 

stats = {
    'total_requests': 0,
    'active_connections': 0,
    'semaphores_created': 0,
    'server_start_time': time.time()
}

def send_heartbeat():
    """Periodically check client connections"""
    while True:
        time.sleep(10) 
        with lock:
            dead_clients = []
            for client_socket in list(clients.keys()):
                try:
                    client_socket.sendall(b"PING\n")
                    if time.time() - client_last_ping.get(client_socket, time.time()) > 30:
                        dead_clients.append(client_socket)
                except:
                    dead_clients.append(client_socket)
        
            for client_socket in dead_clients:
                cleanup_client(client_socket)
                logging.warning(f"Removed dead client: {clients.get(client_socket, 'Unknown')}")

def cleanup_client(client_socket):
    """Clean up client from all semaphores and tracking"""
    username = clients.get(client_socket, 'Unknown')
    
    for sem_name, sem in semaphores.items():
        if sem['holder'] == client_socket:
            if sem['queue']:
                next_client = sem['queue'].pop(0)
                sem['holder'] = next_client
                sem['acquired_time'] = time.time()
                try:
                    next_client.sendall(f"LOCK_GRANTED {sem_name}\n".encode())
                    logging.info(f"Semaphore {sem_name} transferred to next client in queue")
                except:
                    sem['holder'] = None
                    logging.warning(f"Next client in queue for {sem_name} was also disconnected")
            else:
                sem['holder'] = None
                logging.info(f"Semaphore {sem_name} released due to client disconnect")
        
        if client_socket in sem['queue']:
            sem['queue'].remove(client_socket)
            logging.info(f"Removed {username} from queue for semaphore {sem_name}")
    
    if client_socket in clients:
        del clients[client_socket]
    if client_socket in client_last_ping:
        del client_last_ping[client_socket]
    
    stats['active_connections'] -= 1

def get_semaphore_info(sem_name):
    """Get detailed information about a semaphore"""
    if sem_name not in semaphores:
        return f"Semaphore '{sem_name}' does not exist"
    
    sem = semaphores[sem_name]
    holder_name = clients.get(sem['holder'], 'Unknown') if sem['holder'] else 'None'
    queue_size = len(sem['queue'])
    
    info = f"Semaphore '{sem_name}':\n"
    info += f"  Holder: {holder_name}\n"
    info += f"  Queue size: {queue_size}\n"
    
    if sem['holder']:
        held_time = int(time.time() - sem.get('acquired_time', time.time()))
        info += f"  Hold time: {held_time} seconds\n"
    
    if sem['queue']:
        queue_names = [clients.get(client, 'Unknown') for client in sem['queue']]
        info += f"  Queue: {', '.join(queue_names)}\n"
    
    return info

def list_all_semaphores():
    """List all semaphores with basic info"""
    if not semaphores:
        return "No semaphores exist"
    
    result = "All semaphores:\n"
    for name, sem in semaphores.items():
        holder_name = clients.get(sem['holder'], 'Unknown') if sem['holder'] else 'Free'
        queue_size = len(sem['queue'])
        result += f"  {name}: {holder_name} (queue: {queue_size})\n"
    
    return result

def get_server_stats():
    """Get server statistics"""
    uptime = int(time.time() - stats['server_start_time'])
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    result = "Server Statistics:\n"
    result += f"  Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
    result += f"  Active connections: {stats['active_connections']}\n"
    result += f"  Total requests: {stats['total_requests']}\n"
    result += f"  Semaphores created: {stats['semaphores_created']}\n"
    result += f"  Active semaphores: {len(semaphores)}\n"
    
    return result

def handle_client(client_socket, address):
    logging.info(f"New client connected from {address}")
    
    try:
        username_data = client_socket.recv(1024).decode()
        if not username_data.startswith("USERNAME "):
            client_socket.sendall(b"ERROR Trebuie trimis USERNAME la inceput.\n")
            client_socket.close()
            return

        username = username_data.strip().split(" ", 1)[1]
        clients[client_socket] = username
        client_last_ping[client_socket] = time.time()
        stats['active_connections'] += 1
        
        logging.info(f"Client registered: {username} from {address}")
        print(f"[+] Client conectat: {username} ({address})")
        
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break 
            
            data = data.strip()
            if data == "PONG":
                client_last_ping[client_socket] = time.time()
                continue
            
            logging.info(f"Command from {username}: {data}")
            print(f"[{address}] Mesaj primit: {data}")
            
            stats['total_requests'] += 1
            parts = data.split()
            
            if len(parts) == 0:
                client_socket.sendall(b"ERROR Comanda goala\n")
                continue
            
            command = parts[0].upper()
            
            if command == "LIST":
                response = list_all_semaphores()
                client_socket.sendall(f"LIST_RESPONSE\n{response}\n".encode())
                continue
            
            elif command == "STATS":
                response = get_server_stats()
                client_socket.sendall(f"STATS_RESPONSE\n{response}\n".encode())
                continue
            
            elif command == "HELP":
                help_text = """Available commands:
                            LOCK <semaphore_name> - Request exclusive access to semaphore
                            RELEASE <semaphore_name> - Release semaphore
                            INFO <semaphore_name> - Get detailed info about semaphore
                            LIST - List all semaphores
                            STATS - Show server statistics
                            HELP - Show this help message
                            EXIT - Disconnect from server"""
                client_socket.sendall(f"HELP_RESPONSE\n{help_text}\n".encode())
                continue
            
            if len(parts) != 2:
                client_socket.sendall(b"ERROR Comanda invalida. Foloseste HELP pentru ajutor.\n")
                continue

            sem_name = parts[1]

            with lock:
                if command == "INFO":
                    response = get_semaphore_info(sem_name)
                    client_socket.sendall(f"INFO_RESPONSE\n{response}\n".encode())
                    continue
                
                if sem_name not in semaphores:
                    semaphores[sem_name] = {
                        'holder': None, 
                        'queue': [], 
                        'acquired_time': None
                    }
                    stats['semaphores_created'] += 1
                    logging.info(f"Created new semaphore: {sem_name}")

                sem = semaphores[sem_name]

                if command == "LOCK":
                    if sem['holder'] is None:
                        sem['holder'] = client_socket
                        sem['acquired_time'] = time.time()
                        client_socket.sendall(f"LOCK_GRANTED {sem_name}\n".encode())
                        logging.info(f"Lock granted for semaphore {sem_name} to {username}")
                        print(f"[{sem_name}] Acces acordat clientului {username}")
                    else:
                        sem['queue'].append(client_socket)
                        position = len(sem['queue'])
                        client_socket.sendall(f"LOCK_DENIED {sem_name} (Position in queue: {position})\n".encode())
                        logging.info(f"Lock denied for semaphore {sem_name} to {username}, added to queue (position {position})")
                        print(f"[{sem_name}] Clientul {username} adaugat in coada (pozitia {position})")

                elif command == "RELEASE":
                    if sem['holder'] == client_socket:
                        hold_time = int(time.time() - sem.get('acquired_time', time.time()))
                        
                        if sem['queue']:
                            next_client = sem['queue'].pop(0)
                            sem['holder'] = next_client
                            sem['acquired_time'] = time.time()
                            try:
                                next_client.sendall(f"LOCK_GRANTED {sem_name}\n".encode())
                                next_username = clients.get(next_client, 'Unknown')
                                logging.info(f"Semaphore {sem_name} transferred from {username} to {next_username} (held for {hold_time}s)")
                            except:
                                sem['holder'] = None
                                sem['acquired_time'] = None
                                logging.warning(f"Next client for semaphore {sem_name} was disconnected")
                        else:
                            sem['holder'] = None
                            sem['acquired_time'] = None
                            logging.info(f"Semaphore {sem_name} released by {username} (held for {hold_time}s)")
                        
                        client_socket.sendall(f"RELEASE_OK {sem_name}\n".encode())
                        print(f"[{sem_name}] S-a eliberat semaforul de catre {username}")
                    else:
                        client_socket.sendall(f"RELEASE_DENIED {sem_name} (You don't hold this semaphore)\n".encode())
                        logging.warning(f"Invalid release attempt for semaphore {sem_name} by {username}")
                
                else:
                    client_socket.sendall(b"ERROR Comanda necunoscuta. Foloseste HELP pentru ajutor.\n")

    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
        print(f"[!] Eroare cu clientul {address}: {e}")
    finally:
        with lock:
            cleanup_client(client_socket)
        
        try:
            client_socket.close()
        except:
            pass
        
        logging.info(f"Client disconnected: {address}")
        print(f"[-] Conexiune închisă: {address}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
    server.bind((HOST, PORT))
    server.listen()

    logging.info(f"Semaphore server started on {HOST}:{PORT}")
    print(f"[SERVER] Ascult pe {HOST}:{PORT}...")
    
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

    try:
        while True:
            client_socket, address = server.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, address), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        logging.info("Server shutdown requested")
        print("\n[SERVER] Shutting down...")
    except Exception as e:
        logging.error(f"Server error: {e}")
        print(f"[SERVER] Error: {e}")
    finally:
        server.close()
        logging.info("Server stopped")


if __name__ == "__main__":
    start_server()