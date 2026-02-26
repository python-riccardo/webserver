import socket
import threading
import yaml
import os
import logging

# Carico il file YAML
def leggi_file_yaml(percorso):
    try: 
        with open(percorso, "r", encoding="utf-8") as file:
                configurazione = yaml.safe_load(file)
    except FileNotFoundError:
        logging.error("Errore!\nFile non trovato. Controllare il percorso inserito!")
        configurazione = None
    except Exception as e:
        logging.error(f"Errore: {e}")
        configurazione = None
    finally:
        return configurazione

# Validazione YAML
def valida_file_yaml(configurazione):
    

# Gestione del server
def risposta_server(client_socket, client_address, static_dir,configurazione):
    try:
        data = client_socket.recv(4096).decode("utf-8")
        if not data:
            return
        
        # Estraggo dalla richiesta HTTP la pagina desiderata
        prima_riga = data.split("\n")[0]
        percorso_richiesto = prima_riga.split()[1] # Es: "/" o "/chi-siamo"
        logging.info(f"Richiesta per: {percorso_richiesto}")

        # Leggo dal file YAML la mappa delle routes, se non c'è restituisce una lista vuota
        mappa = configurazione.get("routes", [])
        nome_file = None

        # Cerco il percorso nella lista dello YAML
        for route in mappa:
            if route["path"] == percorso_richiesto:
                nome_file = route["file"]
                break

        if nome_file:
            # Se il file esiste la status line è positiva
            status_line = "HTTP/1.1 200 OK\r\n"
            percorso_completo = os.path.join(static_dir, nome_file)
            
            # Trovo l'estensione
            estensione = os.path.splitext(nome_file)[1]
            
            mime_mappa = configurazione["mime_types"]
            tipo_mime = mime_mappa[estensione]
            
            headers = f"Content-Type: {tipo_mime}; charset=utf-8\r\n"
            
            with open(percorso_completo, "rb") as f:
                body = f.read()
        else:
            # Se il file non esiste la status line è negativa
            status_line = "HTTP/1.1 404 Not Found\r\n"
            body = b"<h1>404 - Pagina non trovata</h1>"
            headers = "Content-Type: text/html; charset=utf-8\r\n"

        headers += f"Content-Length: {len(body)}\r\n"
        headers += "Connection: close\r\n\r\n"

        risposta = status_line.encode("utf-8") + headers.encode("utf-8") + body
        client_socket.sendall(risposta)

    except Exception as e:
        print(f"Errore: {e}")
    finally:
        client_socket.close()

# Punto di ingresso del programma
if __name__ == "__main__":

    # Leggo il file YAML e lo carico in configurazione    
    configurazione = leggi_file_yaml("server_config.yaml")
    
    isValido = valida_file_yaml(configurazione)
    if isValido:
        # Subito dopo aver caricato la configurazione sistemo il logging
        log_config = configurazione.get("logging", {})
        logging.basicConfig(
                filename=log_config.get("file", "server.log"),
                level=log_config.get("level", "INFO").upper(),
                format='%(asctime)s - %(levelname)s - %(message)s'
            )

        if configurazione is not None:
            # Estraggo indirizzo IP, Porta e Massimo Connessioni dal file YAML
            host = configurazione["server"]["host"]
            porta = configurazione["server"]["port"]
            max_connections = configurazione["server"]["max_connections"]

            # Avvio socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_socket.bind((host, porta))
            server_socket.listen(max_connections)

            print(f"Server in esecuzione su http://{host}:{porta}")

            while True:
                client_socket, client_address = server_socket.accept()
                t = threading.Thread(target=risposta_server, args=(client_socket, client_address, configurazione["static_dir"], configurazione, ))
                t.start()
        else:
            print("Fine programma")
    else:
        logging.error("Il file non è valido")