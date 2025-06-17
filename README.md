# StateAgent: A Stateful-First AI Agent Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

StateAgent is an opinionated, stateful-first framework for building conversational AI agents. Its core purpose is to solve the biggest problem in human-AI interaction: **continuity and context.** Unlike stateless chat endpoints, StateAgent is architected from the ground up to give an AI a persistent "self," a memory of its own identity, and a memory of who it's talking to and what they've discussed before.

## Core Philosophy

StateAgent is designed to be a transparent and focused alternative to large, general-purpose toolkits.

*   **Stateful-First Architecture:** State is not an add-on; it's the central concept. The entire request pipeline revolves around user identity and memory.
*   **User-Centric Memory:** The architecture is designed to solve complex context problems, like differentiating between two users talking about the same subject (the "Two Sarahs Problem"). Memory is filtered by *who is asking* before a vector search is performed.
*   **Transparent & Opinionated Pipeline:** The agent's logic is a clear, 8-step process for every message. This transparency makes it easy to understand, debug, and extend.
*   **Local-First & Private:** It is built to interface with locally-hosted LLMs via a `llama.cpp` server, ensuring your conversations remain private.

## Key Features

*   **Stateful User Dossiers:** Maintains a separate "dossier" for each user, tracking conversation history and settings.
*   **Intelligent, Contextual Memory:** Remembers key facts from conversations and can differentiate information from different users.
*   **Dynamic On-the-Fly Configuration:** Use simple `//commands` to instantly change the agent's persona, abilities, and conversational style.
*   **Multimodal Support:** Capable of processing both text and images when connected to a compatible multimodal LLM.
*   **OpenAI-Compatible Endpoint:** Can be used as a backend for many existing front-ends (e.g., SillyTavern).
*   **Simple Web UI & CLI:** Includes a command-line client and a basic web interface with image upload support.

---

## Setup and Configuration

StateAgent acts as a smart middleware orchestrator, meaning it sits between a user frontend and your AI model backend. This guide assumes you are using `llama.cpp` as your backend.

### Step 1: Configure and Run `llama.cpp`

The `llama.cpp` server must be running *before* you start StateAgent. It needs to be launched with specific flags to be compatible with StateAgent's memory and chat features.

**1. Example Command:**
Here is a complete, working example command. You will need to change the file paths to match your system.

```bash
# Example for PowerShell
./llama-server.exe --model A:\Models\Your-Model.gguf --host 127.0.0.1 --port 8001 --ctx-size 16384 --pooling mean --chat-template qwen2

# Add --mmproj for multimodal models like Qwen2.5-Omni
./llama-server.exe --model A:\Models\Qwen2.5-Omni.gguf --mmproj A:\Models\mmproj-Qwen2.5.gguf --host 127.0.0.1 --port 8001 --ctx-size 16384 --pooling mean --chat-template qwen2
```

**2. Breakdown of Required Flags:**
These settings are **not optional** and are required for full functionality.

*   `--model`: Path to your GGUF model file.
*   `--host` and `--port`: Must match the `host` and `llama_cpp_port` in your `config.ini` file.
*   `--ctx-size 16384`: **Minimum 8192.** StateAgent sends a lot of context (persona, memories, history). A small context window will fail. 16k or 32k is recommended.
*   `--pooling mean`: **This is critical.** StateAgent's memory system sends requests in a format that requires the `llama.cpp` server to be in pooling mode. Using `--embedding` by itself is **not compatible** and will cause errors. This flag implicitly enables the required `/v1/embeddings` endpoint in the correct mode.
*   `--chat-template <template>`: **Solves `501 Not Implemented` errors.** This tells the server how to format prompts for your specific model.
    *   Use `qwen2` for Qwen 2 models.
    *   Use `llama3` for Llama 3 models.
    *   Use `chatml` for models that use the ChatML format.

### Step 2: Configure and Run StateAgent

Once the backend is running, you can set up and launch the agent itself.

**1. Clone the repository and install dependencies:**
```bash
git clone https://github.com/your-username/StateAgent.git
cd StateAgent
pip install -r requirements.txt
```

**2. Edit the `config.ini` file:**
This file tells StateAgent where to find the `llama.cpp` server and sets default behaviors. Make sure it matches your setup.

```ini
[server_settings]
# This must match the host and port from your llama-server command
host = 127.0.0.1
llama_cpp_port = 8001

# The port StateAgent will listen on for clients
port = 8000

[agent_defaults]
# The default "mind" for a new user
persona = AA
ability = 00
engine = F0
initial_user = agent_memory
```

**3. Launch the StateAgent Server:**
```bash
python server.py
```
This starts the orchestrator. You will see it initialize the agent core and start monitoring for models.

### Step 3: Interact with Your Agent

With both backend and orchestrator running, you can now connect.

**1. Using the Command-Line Client:**
For simple, direct interaction.
```bash
python serverchat.py
```

**2. Using the Web Interface:**
The project includes `index.html`. You must serve it via a local web server. The easiest method is Python's built-in module:
```bash
python -m http.server 8080
```
Now, open `http://localhost:8080` in your browser.

**3. Using a Third-Party Frontend (e.g., SillyTavern):**
StateAgent exposes an OpenAI-compatible API endpoint. You can point any compatible client to this URL:
*   `http://127.0.0.1:8000/v1/chat/completions` (using default config)

Point your frontend's API endpoint to that address, and it will work with StateAgent as its backend.

---

## Agent Usage

Use the following commands in any client to control the agent's state:

*   `//user <name>` - Switch the active user dossier (creates one if it doesn't exist).
*   `//persona <id>` - Change the current user's persona (e.g., `//persona AA`).
*   `//ability <id>` - Change the current user's abilities (e.g., `//ability 01`).
*   `//engine <id>` - Change the current user's thinking style (e.g., `//engine F0`).
*   `//loadout <id>` - Apply a preset mind from `config.ini` (e.g., `//loadout TEST99`).
*   `//mem <text>` - Manually save a piece of text to the agent's long-term memory.
*   `//recall <query>` - Search the agent's memory for relevant information.
*   `//enroll` - Creates a voice signature of the current user based on conversation history.

---

## Contributing

Contributions are welcome! If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.
