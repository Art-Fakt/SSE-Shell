// Terminal output element
const output = document.getElementById('output');
const commandInput = document.getElementById('commandInput');
const sendCommandButton = document.getElementById('sendCommand');

// Function to append messages to the terminal
function appendToTerminal(message) {
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    output.appendChild(messageElement);
    output.scrollTop = output.scrollHeight; // Scroll to the bottom
}

// Send command to the server
sendCommandButton.addEventListener('click', () => {
    const command = commandInput.value.trim();
    if (command) {
        fetch('/send-command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command }),
        })
            .then((response) => response.json())
            .then((data) => {
                appendToTerminal(`RSSE> ${command}`); // Indique que la commande a été envoyée
                appendToTerminal(data.message); // Affiche la réponse du serveur
            })
            .catch((error) => {
                appendToTerminal(`Error: ${error.message}`);
            });
        commandInput.value = '';
    }
});

// Variable pour stocker les morceaux de réponse
let responseBuffer = "";

// Listen for server-sent events (SSE) for responses
const responseSource = new EventSource('/responses');
responseSource.onmessage = (event) => {
    const message = event.data.trim();

    // Ignore "keep-alive" messages
    if (message === "keep-alive") {
        return;
    }

    // Ajouter le morceau au buffer
    responseBuffer += message + "\n";

    // Afficher la réponse complète si elle est terminée
    appendToTerminal(`CLIENT> ${responseBuffer}`);
    responseBuffer = ""; // Réinitialiser le buffer après affichage
};