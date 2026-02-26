import socket
import threading
import yaml
import os
import logging

# Funzione per caricare un file yaml in modo sicuro
def leggi_file_yaml(percorso):
    try: 
        with open(percorso, "r", encoding="utf-8") as file:
            configurazione = yaml.safe_load(file)
            return configurazione
    except FileNotFoundError:
        logging.error(f"Errore: File '{percorso}' non trovato.")
    except Exception as e:
        logging.error(f"Errore durante la lettura dello YAML: {e}")
    return None

# Funzione per validare il file YAML
def valida_file_yaml(configurazione):
    if not configurazione:
        return False
    # Se il file esiste verifico che i campi obbligatori siano presenti
    campi_richiesti = ["server", "static_dir", "mime_types"]
    for campo in campi_richiesti:
        if campo not in configurazione:
            logging.error(f"Campo mancante nel file di configurazione: {campo}")
            return False
    return True

# Funzione per gestire la ricezione e l'invio di dati al client
def risposta_server(client_socket, client_address, configurazione):
    try:
        data = client_socket.recv(4096).decode("utf-8")
        if not data:
            return
        
        static_dir = configurazione.get("static_dir", "./public")
        prima_riga = data.split("\n")[0]
        percorso_richiesto = prima_riga.split()[1]
        
        logging.info(f"Richiesta da {client_address}: {percorso_richiesto}")

        mappa = configurazione.get("routes", [])
        nome_file = None

        for route in mappa:
            if route["path"] == percorso_richiesto:
                nome_file = route["file"]
                break

        if nome_file:
            percorso_completo = os.path.join(static_dir, nome_file)
            if os.path.exists(percorso_completo):
                status_line = "HTTP/1.1 200 OK\r\n"
                estensione = os.path.splitext(nome_file)[1]
                
                # Metto dei mime type di default
                tipo_mime = configurazione.get("mime_types", {}).get(estensione, "application/octet-stream")
                
                headers = f"Content-Type: {tipo_mime}; charset=utf-8\r\n"
                with open(percorso_completo, "rb") as f:
                    body = f.read()
            else:
                # Se non trovo il percorso del file chiamo l'eccezione 
                raise FileNotFoundError
        else:
            status_line = "HTTP/1.1 404 Not Found\r\n"
            body = b"<h1>404 - Pagina non trovata</h1>"
            headers = "Content-Type: text/html; charset=utf-8\r\n"

        headers += f"Content-Length: {len(body)}\r\n"
        headers += "Connection: close\r\n\r\n"
        client_socket.sendall(status_line.encode("utf-8") + headers.encode("utf-8") + body)

    except Exception as e:
        logging.error(f"Errore durante la gestione della richiesta: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    # Configurazione iniziale del logging con valori di default.
    # Questo permette di loggare errori anche se il file YAML non viene trovato.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    config = leggi_file_yaml("server_config.yaml")
    
    if valida_file_yaml(config):
        # Sovrascrivo la configurazione del logging con i dati del file YAML
        log_section = config.get("logging", {})
        log_file = log_section.get("file", "server.log")
        log_level = log_section.get("level", "INFO").upper()

        # Aggiornamento logger (rimuove i vecchi handler e ne mette di nuovi)
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            filename=log_file,
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        host = config["server"]["host"]
        porta = config["server"]["port"]
        max_conn = config["server"]["max_connections"]

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, porta))
        server_socket.listen(max_conn)

        logging.info(f"Server avviato correttamente su http://{host}:{porta}")

        while True:
            client_sock, addr = server_socket.accept()
            t = threading.Thread(target=risposta_server, args=(client_sock, addr, config))
            t.daemon = True # Il thread si chiude se il main si chiude
            t.start()
    else:
        logging.critical("Impossibile avviare il server: configurazione non valida o mancante.")
