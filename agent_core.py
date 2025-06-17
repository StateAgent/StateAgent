# --- START OF FINAL agent_core.py ---

import threading, serverconfig, traceback
from statefulness import UserDossier, MemorySystem
from nodes import (
    InputParserNode, AuthenticationNode, MemoryRecallNode, PromptFormatterNode, 
    ContextMonitorNode, LLMCallNode, WorkingMemoryUpdateNode, MemoryGatekeeperNode
)

class StateAgent:
    def __init__(self, persona_id, ability_id, engine_id):
        print("Initializing State Agent Core...")
        self.memory_system = MemorySystem()
        self.dossiers = {}

        # These now correctly store the defaults passed from server.py at startup
        self.default_persona_id = persona_id
        self.default_ability_id = ability_id
        self.default_engine_id = engine_id
        
        # Bootstrap the main agent's dossier with the correct startup defaults
        initial_agent_id = serverconfig.INITIAL_USER_ID
        initial_dossier = UserDossier(initial_agent_id)
        initial_dossier.persona_id = self.default_persona_id
        initial_dossier.ability_id = self.default_ability_id
        initial_dossier.engine_id = self.default_engine_id
        self.dossiers[initial_agent_id] = initial_dossier
        
        self.active_session_id = initial_agent_id
        self.current_model_id = None
        self.lock = threading.Lock()
        
        self.pipeline = [
            InputParserNode(self), AuthenticationNode(self), MemoryRecallNode(self), 
            PromptFormatterNode(self), ContextMonitorNode(self), LLMCallNode(self), 
            WorkingMemoryUpdateNode(self), MemoryGatekeeperNode(self)
        ]
        print("State Agent Core Initialized (v0.3 - Implicit Intelligence).")

    def switch_active_dossier(self, user_id):
        with self.lock:
            if user_id not in self.dossiers:
                new_dossier = UserDossier(user_id)
                # New dossiers for users ALSO get the startup defaults.
                new_dossier.persona_id = self.default_persona_id
                new_dossier.ability_id = self.default_ability_id
                new_dossier.engine_id = self.default_engine_id
                self.dossiers[user_id] = new_dossier
            
            self.active_session_id = user_id
            active_dossier = self.dossiers[self.active_session_id]
            print(f"[DOSSIER_MGR] Active session switched to: {user_id} (Mind: P:{active_dossier.persona_id}/A:{active_dossier.ability_id}/E:{active_dossier.engine_id})")
            
    def handle_request(self, request_data, model_id_from_client):
        with self.lock:
            user_dossier = self.dossiers.get(self.active_session_id, self.dossiers[serverconfig.INITIAL_USER_ID])
            self.current_model_id = model_id_from_client

        try:
            context = {
                'agent': self, 'user_dossier': user_dossier, 'memory_system': self.memory_system,
                'request_data': request_data, 'model_id': self.current_model_id, 
                'continue_pipeline': True,
            }
            
            for node_instance in self.pipeline:
                if not context.get('continue_pipeline', True): break
                context = node_instance.process(context)
            
            return context.get('final_response', "Error: Agent pipeline produced no response.")
        
        except Exception as e:
            traceback.print_exc()
            return f"Fatal Server Error: {e}"

# --- END OF FINAL agent_core.py ---