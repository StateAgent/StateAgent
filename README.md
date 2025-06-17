# StateAgent: A Stateful-First AI Agent Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

StateAgent is an opinionated, stateful-first framework for building conversational AI agents. Its core purpose is to solve the biggest problem in human-AI interaction: **continuity and context.** Unlike stateless chat endpoints, StateAgent is architected from the ground up to give an AI a persistent "self," a memory of its own identity, and a memory of who it's talking to and what they've discussed before.

It provides a complete, working chassis for interactive AI, allowing you to focus on your agent's character and knowledge, not the complex plumbing of state management.

## Key Features

*   **Stateful User Dossiers:** Remembers individual users, their settings, and conversation history.
*   **Intelligent, Contextual Memory:** Can differentiate information from different users, preventing context "leaks."
*   **Dynamic On-the-Fly Configuration:** Use simple `//commands` to instantly change the agent's persona, abilities, and style.
*   **Multimodal Support:** Processes both text and images with compatible LLMs.
*   **OpenAI-Compatible Endpoint:** Works as a drop-in backend for many existing front-ends (like SillyTavern).
*   **Local-First & Private:** Designed to run with a local `llama.cpp` server.

---

## Installation Guide (3 Steps)

This guide will get you running. Follow these steps in order.

### Step 1: Run the `llama.cpp` Backend

**This is the most important step.** StateAgent connects to a `llama.cpp` server, so it must be running first with the correct settings.

**1. Example Command:**
Use this as a template. You **must** change the file paths to match your system.

```bash
# For a standard text model
./llama-server.exe --model C:\Models\Your-Model.gguf --host 127.0.0.1 --port 8001 --ctx-size 16384 --pooling mean --chat-template llama3

# For a multimodal model like Qwen2.5-Omni
./llama-server.exe --model C:\Models\Qwen2.5-Omni.gguf --mmproj C:\Models\mmproj-Qwen2.5.gguf --host 127.0.0.1 --port 8001 --ctx-size 16384 --pooling mean --chat-template qwen2
```

**2. Required Flags Explained:**
| Flag | Requirement | Why it's Important |
| :--- | :--- | :--- |
| `--model` | **Required** | The path to your GGUF model file. |
| `--port 8001`| **Required** | Must match `llama_cpp_port` in `config.ini`. |
| `--ctx-size 16384`| **Required** | Min: `8192`. StateAgent needs a large context. |
| `--pooling mean` | **CRITICAL** | Activates the server's embedding feature in a mode compatible with StateAgent. **Using `--embedding` alone will cause errors.** |
| `--chat-template` | **CRITICAL** | Prevents `501` errors by telling the server your model's chat format (e.g., `llama3`, `qwen2`, `chatml`). |

> 💡 **A Note on `--pooling mean`**
>
> You must use `--pooling mean` to enable embeddings. The default `--embedding` flag in `llama.cpp` is **not compatible** with the way StateAgent requests vectors, and using it will cause the memory system to fail. The `--pooling mean` flag enables a different, more robust server-side handler that works correctly with StateAgent.

### Step 2: Run the StateAgent Server

Now that the backend is ready, start the agent.

1.  **Clone the repository and install dependencies:**
    ```bash
    git clone https://github.com/StateAgent/StateAgent.git
    cd StateAgent
    pip install -r requirements.txt
    ```

2.  **Configure `config.ini`:**
    Make sure `llama_cpp_port` matches the port you used in Step 1.
    ```ini
    [server_settings]
    host = 127.0.0.1
    port = 8000
    llama_cpp_port = 8001 # Must match llama-server!
    ```

3.  **Launch the StateAgent Server:**
    ```bash
    python server.py
    ```

### Step 3: Connect and Chat!

Your agent is now running. Connect with a client.

*   **For the Command-Line Client:**
    ```bash
    python serverchat.py
    ```
*   **For the Web UI:**
    Run a simple web server in the project directory:
    ```bash
    python -m http.server 8080
    ```
    Then, open `http://localhost:8080` in your browser.
*   **For Third-Party Frontends (SillyTavern, etc.):**
    Point the client to StateAgent's OpenAI-compatible endpoint:
    `http://127.0.0.1:8000/v1/chat/completions`

---

## Agent Usage

Use the following commands in any client to control the agent's state:

*   `//user <name>` - Switch the active user dossier.
*   `//persona <id>` - Change the agent's persona.
*   `//ability <id>` - Change the agent's abilities.
*   `//engine <id>` - Change the agent's conversational style.
*   `//loadout <id>` - Apply a preset from `config.ini`.
*   `//mem <text>` - Manually save a memory.
*   `//recall <query>` - Search memory.
*   `//enroll` - Create a "voice signature" for the current user.

## License

Distributed under the MIT License. See `LICENSE` for more information.
