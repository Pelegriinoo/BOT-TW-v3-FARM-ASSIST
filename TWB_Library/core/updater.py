"""
Update checking logic
CORRIGIDO - Sistema de update desabilitado para evitar erros
"""

import json
import os.path
import time
import requests
import logging


def check_update():
    """
    CORRIGIDO - Desabilitado por padrão para sistema multi-contas
    Se habilitado no config, verifica se há atualizações disponíveis
    """
    # Verifica se o arquivo de config existe e se check_update está habilitado
    try:
        from core.context import AccountContext
        config_path = AccountContext.get_config_path()
    except ImportError:
        # Fallback para sistema legado
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config.json"
        )
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as running_cf:
            try:
                parsed = json.load(fp=running_cf)
                if not parsed.get("bot", {}).get("check_update", False):
                    # Check update desabilitado no config
                    return
            except (json.JSONDecodeError, KeyError):
                # Se houver erro ao ler config, não fazer update check
                return
    else:
        # Se não existe config, não fazer update check
        return
    
    # Se chegou aqui, check_update está habilitado
    try:
        get_local_config_template_version = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config.example.json"
        )
        
        if not os.path.exists(get_local_config_template_version):
            logging.debug("config.example.json not found, skipping update check")
            return
            
        with open(get_local_config_template_version, "r", encoding="utf-8") as local_cf:
            parsed = json.load(fp=local_cf)
            
            # CONFIGURADO: URL atualizada para seu repositório
            logging.info("Verificando atualizações...")
            logging.info(f"Versão atual: {parsed['build']['version']}")
            
            # Update check reabilitado com seu repositório
            try:
                get_remote_version = requests.get(
                    "https://raw.githubusercontent.com/Pelegriinoo/BOT-TW-v2/main/TWB_Library/config.example.json",
                    timeout=10
                ).json()
                
                if parsed["build"]["version"] != get_remote_version["build"]["version"]:
                    logging.warning(
                        "Nova versão disponível do bot! \n"
                        "Baixe a versão mais recente em: \n"
                        "https://github.com/Pelegriinoo/BOT-TW-v2"
                    )
                    time.sleep(5)
                else:
                    logging.info("Bot está atualizado")
            except Exception as e:
                logging.debug(f"Falha ao verificar atualização: {e}")
                logging.info(f"Versão atual: {parsed['build']['version']}")
    
    except Exception as e:
        logging.debug(f"Update check failed: {e}")
        # Não interromper o bot por causa de erro no update check
        pass