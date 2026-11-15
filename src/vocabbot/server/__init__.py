"""VocabBot as a remote MCP server with accounts, for Claude and ChatGPT on the web and the phone.

The engine runs here for many learners: one folder per account, the same
commands as the `vocabbot` program, the same JSON as the plugin's skills read.
The server signs learners in with OAuth 2.1 (dynamic client registration,
PKCE, refresh tokens), so a chat application connects with the server's
address alone. Its dependencies come with `pip install "vocabbot[server]"`;
the engine itself still needs none.
"""
