"""
Context Manager para Sistema Multi-Contas TWB
Gerencia os caminhos dos arquivos para cada conta isoladamente
"""
import os
import threading
from pathlib import Path

class AccountContext:
    """Contexto isolado para cada conta"""
    _local = threading.local()
    
    @classmethod
    def set_account_path(cls, account_path):
        """Define o diretório da conta atual"""
        cls._local.account_path = Path(account_path)
        
    @classmethod
    def get_account_path(cls):
        """Retorna o diretório da conta atual"""
        if hasattr(cls._local, 'account_path'):
            return cls._local.account_path
        # Fallback para compatibilidade com sistema antigo
        return Path(os.getcwd())
    
    @classmethod
    def get_config_path(cls):
        """Retorna o caminho para config.json da conta"""
        return cls.get_account_path() / "config.json"
    
    @classmethod
    def get_cache_path(cls, subdir=""):
        """Retorna o caminho para cache da conta"""
        if subdir:
            return cls.get_account_path() / "cache" / subdir
        return cls.get_account_path() / "cache"
    
    @classmethod
    def get_session_path(cls):
        """Retorna o caminho para session.json da conta"""
        return cls.get_cache_path() / "session.json"
    
    @classmethod
    def get_attacks_path(cls):
        """Retorna o caminho para attacks.json da conta"""
        return cls.get_account_path() / "attacks.json"
    
    @classmethod
    def is_multi_account_mode(cls):
        """Verifica se está rodando em modo multi-conta"""
        return hasattr(cls._local, 'account_path')
    
    @classmethod
    def ensure_cache_dirs(cls):
        """Garante que os diretórios de cache existam"""
        cache_dirs = [
            "attacks", "reports", "villages", "world", 
            "logs", "managed", "hunter"
        ]
        
        for cache_dir in cache_dirs:
            dir_path = cls.get_cache_path(cache_dir)
            dir_path.mkdir(parents=True, exist_ok=True)