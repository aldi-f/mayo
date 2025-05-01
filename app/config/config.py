BASE_SYSTEM_PROMPT = """
Your name is Mayo. 
You are sometimes sarcastic. 
You answer questions that people have but try to be funny sometimes. 
Do not write in style of 'as an AI, I cannot do x thing'. Try to be creative with the answers."
"""

BASE_MODEL = "google/gemini-2.0-flash-001"

# class ServerConfigurations:
#     _instance = None
#     _configurations = {}

#     def __new__(cls):
#         if not cls._instance:
#             cls._instance = super(ServerConfigurations, cls).__new__(cls)
#         return cls._instance

#     def get_configurations(self):
#         return self._configurations

#     def get_server_configurations(self, server_name):
#         return self._configurations.get(server_name, {})

#     def update_server_configurations(self, server_name, new_config):
#         if server_name not in self._configurations:
#             self._configurations[server_name] = {}
#         self._configurations[server_name].update(new_config)


# SERVER_CONFIGURATIONS = ServerConfigurations()

