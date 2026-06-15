"""Skill Picker: vector-similarity skill selection for coding agents, backed by vLLM.

Selection ranks skills by embedding similarity over lightweight matching metadata and
loads full descriptions lazily — only for selected skills (Constitution II).
"""

__version__ = "0.1.0"
