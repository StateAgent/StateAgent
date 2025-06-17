import threading, prompt, serverconfig, requests, tiktoken, traceback
import re
# ### DELETED ###
# The faulty import statement has been removed from here.

# --- HELPER FUNCTION (Unchanged) ---
def _sanitize_for_filename(text):
    """Converts any string into a safe, lowercase, underscore-separated filename."""
    if not isinstance(text, str):
        return ""
    s = text.lower().replace(' ', '_').replace('-', '_')
    s = re.sub(r'[^a-z0-9_]', '', s); s = re.sub(r'_+', '_', s)
    return s.strip('_')

# --- COMMAND HANDLERS (Now the single source of truth) ---
def execute_command(context, command_line):
    user_dossier = context.get('user_dossier')
    if not user_dossier:
        return {"final_response": "ACK_ERROR: No active user session.", "continue_pipeline": False}

    print(f"[CMD_BUS] Executing: '{command_line}' for user '{user_dossier.user_id}'")
    parts = command_line.strip().split(" ", 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handlers = {
        "//user": _handle_user_command,
        "//persona": _handle_persona_command,
        "//ability": _handle_ability_command,
        "//engine": _handle_engine_command,
        "//loadout": _handle_loadout_command,
        "//mem": _handle_mem_command,
        "//recall": _handle_recall_command,
        "//enroll": _handle_enroll_command,
    }
    handler = handlers.get(command)
    if handler:
        return handler(context, args)
    else:
        return {"final_response": f"ACK_ERROR: Unknown command '{command}'.", "continue_pipeline": False}

def _handle_user_command(context, args):
    user_id_raw = args.strip()
    if not user_id_raw: return {"final_response": "ACK_ERROR: '//user' command requires a name.", "continue_pipeline": False}
    user_id = _sanitize_for_filename(user_id_raw)
    if not user_id: return {"final_response": f"ACK_ERROR: Invalid user name provided: '{user_id_raw}'.", "continue_pipeline": False}
    context['agent'].switch_active_dossier(user_id)
    return {"final_response": f"ACK: Active user switched to '{user_id}'.", "continue_pipeline": False}

def _handle_persona_command(context, args):
    dossier = context['user_dossier']
    persona_id = args.strip().upper()
    if persona_id in prompt.PERSONA_CARDS:
        dossier.persona_id = persona_id; return {"final_response": f"ACK: Persona set to '{persona_id}'.", "continue_pipeline": False}
    return {"final_response": f"ACK_ERROR: Persona '{persona_id}' not found.", "continue_pipeline": False}

def _handle_ability_command(context, args):
    dossier = context['user_dossier']
    ability_id = args.strip()
    if ability_id in prompt.ABILITY_CARDS:
        dossier.ability_id = ability_id; return {"final_response": f"ACK: Abilities set to '{ability_id}'.", "continue_pipeline": False}
    return {"final_response": f"ACK_ERROR: Ability '{ability_id}' not found.", "continue_pipeline": False}
    
def _handle_engine_command(context, args):
    dossier = context['user_dossier']
    engine_id = args.strip().upper()
    if engine_id in prompt.ENGINE_CARDS:
        dossier.engine_id = engine_id; return {"final_response": f"ACK: Engine set to '{engine_id}'.", "continue_pipeline": False}
    return {"final_response": f"ACK_ERROR: Engine '{engine_id}' not found.", "continue_pipeline": False}

def _handle_loadout_command(context, args):
    dossier = context['user_dossier']
    loadout_id = args.strip().upper()
    if loadout_id in serverconfig.LOADOUTS:
        p, a, e = serverconfig.LOADOUTS[loadout_id]; dossier.persona_id, dossier.ability_id, dossier.engine_id = p.upper(), a, e.upper()
        return {"final_response": f"ACK: Loadout '{loadout_id}' applied.", "continue_pipeline": False}
    return {"final_response": f"ACK_ERROR: Loadout '{loadout_id}' not found.", "continue_pipeline": False}

def _handle_mem_command(context, args):
    text_to_remember = args.strip()
    if not text_to_remember: return {"final_response": "ACK_ERROR: //mem requires text.", "continue_pipeline": False}

    print("[CMD_BUS] //mem triggering smart memory routing.")
    ### MODIFIED: Use the correct class name directly ###
    gatekeeper_node = MemoryGatekeeperNode() # We use the class directly since it's in this file
    mem_context = context.copy()
    mem_context['text_prompt'] = text_to_remember # Provide the text from the command
    
    # Run the smart memory saving process in a background thread
    threading.Thread(target=gatekeeper_node._enrich_and_route, args=(mem_context,)).start()
    return {"final_response": "ACK: Manual memory storage initiated (using intelligent routing).", "continue_pipeline": False}

def _handle_recall_command(context, args):
    query = args.strip()
    if not query: return {"final_response": "ACK_ERROR: '//recall' requires a search query.", "continue_pipeline": False}
    memory_system = context['memory_system']
    user_dossier = context['user_dossier']
    
    recalled_memories = memory_system.intelligent_recall(user_dossier.user_id, query)
    
    if not recalled_memories:
        response_text = "I searched my memory for that, but found nothing relevant in our current context."
    else:
        formatted_list = "\n- ".join(recalled_memories)
        response_text = f"I recalled the following from memory:\n- {formatted_list}"
    return {"final_response": response_text, "continue_pipeline": False}

def _handle_enroll_command(context, args):
    user_dossier = context['user_dossier']; user_id_raw = args.strip()
    if not user_id_raw: return {"final_response": "ACK_ERROR: //enroll requires a user name.", "continue_pipeline": False}
    user_id_to_enroll = _sanitize_for_filename(user_id_raw)
    if user_id_to_enroll != user_dossier.user_id: return {"final_response": f"ACK_ERROR: You must be switched to the user to enroll them. Use `//user {user_id_raw}` first.", "continue_pipeline": False}
    memory_system = context['memory_system']; conversation_history = user_dossier.get_history()
    if len(conversation_history) < 2: return {"final_response": "ACK_WARN: Please chat once more before enrolling so I have a good sample.", "continue_pipeline": False}
    threading.Thread(target=memory_system.enroll_user, args=(user_id_to_enroll, conversation_history)).start()
    return {"final_response": f"ACK: Enrollment process initiated for user '{user_id_to_enroll}'.", "continue_pipeline": False}

# --- NODE DEFINITIONS ---
ENCODER = tiktoken.get_encoding("cl100k_base")
class Node:
    def __init__(self, a=None): self.agent = a
    def process(self, c): raise NotImplementedError

class InputParserNode(Node):
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        request_data = context.get('request_data', {}); raw_content = request_data.get('messages', [{}])[-1].get('content', '')
        text_prompt = ""
        if isinstance(raw_content, str): text_prompt = raw_content
        elif isinstance(raw_content, list):
            for part in raw_content:
                if isinstance(part, dict) and part.get('type') == 'text': text_prompt = part.get('text', ''); break
        context['text_prompt'] = text_prompt; context['raw_content'] = raw_content

        intro_patterns = [r"my name is (?P<name>\w+)", r"i am (?P<name>\w+)", r"i'm (?P<name>\w+)"]
        for pattern in intro_patterns:
            if match := re.search(pattern, text_prompt, re.IGNORECASE):
                user_id_raw = match.group("name")
                if user_id := _sanitize_for_filename(user_id_raw):
                    print(f"[NODE_NLP] Detected user introduction: '{user_id_raw}'. Switching dossier.")
                    self.agent.switch_active_dossier(user_id)
                    context['final_response'] = f"ACK: Hello {user_id_raw}! I've loaded your dossier."
                    context['continue_pipeline'] = False
                    return context

        if text_prompt.lstrip().startswith("//"):
            context.update(execute_command(context, text_prompt.lstrip().split('\n', 1)[0]))
        return context

class AuthenticationNode(Node):
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        user_dossier = context['user_dossier']; text_prompt = context.get('text_prompt', "")
        if user_dossier.user_id == serverconfig.INITIAL_USER_ID and not text_prompt.lstrip().startswith("//"):
            memory_system = context['memory_system']
            if identified_user := memory_system.identify_user(text_prompt):
                self.agent.switch_active_dossier(identified_user)
                context['user_dossier'] = self.agent.dossiers[identified_user]
            else:
                history = user_dossier.get_history()
                if history and "who I'm speaking with" in history[-1].get('content', ''):
                     context['final_response'] = "I'm sorry, I still didn't understand. To set your active profile, please say 'my name is' followed by your name, or use the command: `//user YourName`"
                else: context['final_response'] = "Hello! To get started and so I can remember our conversation, could you please tell me who I'm speaking with today? (e.g., `//user Scott` or `My name is Scott`)"
                context['continue_pipeline'] = False
        return context

class MemoryRecallNode(Node):
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        text_prompt = context.get('text_prompt', ""); recalled_memories = []
        if not text_prompt.lstrip().startswith("//") and (memory_system := context.get('memory_system')):
             recalled_memories = memory_system.intelligent_recall(context['user_dossier'].user_id, text_prompt)
        context['recalled_memories'] = recalled_memories
        return context

class PromptFormatterNode(Node):
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        dossier = context.get('user_dossier')
        if not dossier: context['final_response'] = "Error: No dossier in context."; context['continue_pipeline'] = False; return context
        p_card = prompt.PERSONA_CARDS.get(dossier.persona_id, {}); a_card = prompt.ABILITY_CARDS.get(dossier.ability_id, {})
        e_card = prompt.ENGINE_CARDS.get(dossier.engine_id, {}); persona_text = p_card.get('persona', 'You are a helpful AI.')
        abilities_text = a_card.get('abilities', 'You have no special abilities.'); engine_text = e_card.get('engine', 'You should respond directly.')
        system_prompt = f"{persona_text}\n\n--- ABILITIES ---\n{abilities_text}\n\n--- STYLE ---\n{engine_text}"
        messages = [{"role": "system", "content": system_prompt}]
        if recalled := context.get('recalled_memories', []): messages.append({"role": "system", "content": f"CONTEXT FROM MEMORY:\n- {'\n- '.join(recalled)}"})
        messages.extend(dossier.get_history()); messages.append({"role": "user", "content": context.get('raw_content', '')})
        context['llm_messages_payload'] = messages
        return context

class ContextMonitorNode(Node):
    CONTEXT_SIZE_LIMIT = 128 * 1024
    def _count_tokens(self, messages):
        count = 0;
        for message in messages:
            count += 4; content = message.get("content")
            if isinstance(content, str): count += len(ENCODER.encode(content))
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text": count += len(ENCODER.encode(part.get("text", "")))
                    elif part.get("type") == "image_url": count += 85
        return count
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        if not (messages := context.get('llm_messages_payload')): return context
        
        token_count = self._count_tokens(messages)
        ### MODIFIED: Fixed the typo from 'token_token_count' to 'token_count' ###
        usage_percent = (token_count / self.CONTEXT_SIZE_LIMIT) * 100
        
        messages.insert(1, {"role": "system", "content": f"CONTEXT: {token_count:,} tokens ({usage_percent:.1f}% full)."}); context['llm_messages_payload'] = messages
        return context

class LLMCallNode(Node):
    def process(self, context):
        if context.get('continue_pipeline') == False: return context
        payload = {"model": context['model_id'], "messages": context.get('llm_messages_payload', [])}
        if not payload["messages"]: context['final_response'] = "Error: Prompt empty."; context['continue_pipeline'] = False; return context
        try:
            resp = requests.post(serverconfig.LLAMA_CPP_CHAT_URL, json=payload, timeout=180); resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].strip()
            context['llm_response_text'] = content; context['final_response'] = content
        except Exception as e: context.update({'final_response': f"Error: Could not contact model.", 'continue_pipeline': False})
        return context

class WorkingMemoryUpdateNode(Node):
    def process(self, context):
        dossier = context['user_dossier']; raw_user_content = context.get('raw_content')
        llm_response = context.get('final_response', '')
        if raw_user_content: dossier.add_message("user", raw_user_content)
        if llm_response: dossier.add_message("assistant", llm_response)
        return context

class MemoryGatekeeperNode(Node):
    def _is_memorable(self, context):
        text_prompt = context.get('text_prompt', ""); return not text_prompt.startswith("//") and len(text_prompt.split()) > 3

    def _enrich_and_route(self, context):
        try:
            original_text = context.get('text_prompt'); dossier = context['user_dossier']
            speaker_id = dossier.user_id
            
            enrich_prompt = f"Rewrite the statement from '{speaker_id}' into a concise, self-contained, objective fact, resolving pronouns.\nStatement: \"{original_text}\"\nFactual Memory:"
            payload = {"model": context['model_id'], "messages": [{"role": "user", "content": enrich_prompt}], "temperature": 0.2, "n_predict": 128}
            resp = requests.post(serverconfig.LLAMA_CPP_CHAT_URL, json=payload, timeout=60); resp.raise_for_status()
            enriched_text = resp.json()['choices'][0]['message']['content'].strip()
            
            route_prompt = f"""
Analyze the following fact and determine the primary subject. The primary subject is the main person or topic the fact is about.
Think step-by-step:
1. Identify all people, places, or distinct topics mentioned.
2. Determine which one is the central focus of the statement.
3. Respond with ONLY the subject's name, and nothing else.

Fact: "{enriched_text}"

Subject:"""
            payload = {"model": context['model_id'], "messages": [{"role": "user", "content": route_prompt}], "temperature": 0.0, "n_predict": 32}
            resp = requests.post(serverconfig.LLAMA_CPP_CHAT_URL, json=payload, timeout=60); resp.raise_for_status()
            raw_entity_id = resp.json()['choices'][0]['message']['content'].strip()
            
            entity_id = _sanitize_for_filename(raw_entity_id) if raw_entity_id else speaker_id
            
            context['memory_system'].remember(speaker_id, entity_id, enriched_text)
        except Exception as e:
            traceback.print_exc()

    def process(self, context):
        if context.get('llm_response_text') and context.get('continue_pipeline') != False:
            if self._is_memorable(context):
                threading.Thread(target=self._enrich_and_route, args=(context.copy(),), daemon=True).start()
        return context
# --- end of nodes.py