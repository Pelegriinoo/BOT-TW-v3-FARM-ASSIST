#!/usr/bin/env python3
"""
Gerenciador principal do sistema TWB Multi-Contas
"""
import os
import sys
import json
import subprocess
from pathlib import Path

class TWBManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.accounts_dir = self.base_dir / "accounts" 
        self.library_dir = self.base_dir / "TWB_Library"
        
    def list_accounts(self):
        """Lista todas as contas configuradas"""
        if not self.accounts_dir.exists():
            print("ERRO: Pasta accounts não encontrada")
            return []
        
        accounts = []
        for item in self.accounts_dir.iterdir():
            if item.is_dir() and (item / "config.json").exists():
                accounts.append(item.name)
        
        return accounts
    
    def show_account_info(self, account_name):
        """Mostra informações de uma conta"""
        account_dir = self.accounts_dir / account_name
        config_file = account_dir / "config.json"
        
        if not config_file.exists():
            print(f"ERRO: Conta {account_name} não encontrada")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"\nInformações da conta: {account_name}")
            print("-" * 40)
            print(f"Servidor: {config.get('server', {}).get('server', 'N/A')}")
            print(f"Endpoint: {config.get('server', {}).get('endpoint', 'N/A')}")
            print(f"Horário ativo: {config.get('bot', {}).get('active_hours', 'N/A')}")
            
            # Verifica arquivos importantes
            files_to_check = ['attacks.json', 'run.py', 'start.bat']
            print(f"\nArquivos:")
            for file in files_to_check:
                file_path = account_dir / file
                status = "OK" if file_path.exists() else "FALTANDO"
                print(f"  {file}: {status}")
                
        except Exception as e:
            print(f"ERRO ao ler config: {e}")
    
    def run_account(self, account_name):
        """Executa uma conta específica"""
        account_dir = self.accounts_dir / account_name
        run_script = account_dir / "run.py"
        
        if not run_script.exists():
            print(f"ERRO: Script run.py não encontrado para {account_name}")
            return
        
        print(f"Executando conta: {account_name}")
        
        try:
            subprocess.run([sys.executable, str(run_script)], cwd=account_dir)
        except KeyboardInterrupt:
            print(f"\nExecução da conta {account_name} interrompida")
        except Exception as e:
            print(f"ERRO ao executar conta {account_name}: {e}")
    
    def create_account(self, account_name, base_config=None):
        """Cria uma nova conta"""
        from setup_account import setup_account
        setup_account(account_name, base_config)
    
    def menu(self):
        """Menu interativo"""
        while True:
            print("\n" + "-" * 50)
            print("TWB Multi-Contas Manager")
            print("-" * 50)
            
            accounts = self.list_accounts()
            
            if accounts:
                print("\nContas disponíveis:")
                for i, account in enumerate(accounts, 1):
                    print(f"  {i}. {account}")
            else:
                print("\nNenhuma conta configurada")
            
            print("\nOpções:")
            print("  [n] Nova conta")
            print("  [l] Listar contas") 
            print("  [i] Info de conta")
            print("  [r] Executar conta")
            print("  [q] Sair")
            
            choice = input("\nEscolha uma opção: ").lower().strip()
            
            if choice == 'q':
                break
            elif choice == 'n':
                name = input("Nome da nova conta: ").strip()
                if name:
                    self.create_account(name)
            elif choice == 'l':
                continue  # Já lista no início do loop
            elif choice == 'i':
                if accounts:
                    account = input("Nome da conta: ").strip()
                    if account in accounts:
                        self.show_account_info(account)
                else:
                    print("ERRO: Nenhuma conta disponível")
            elif choice == 'r':
                if accounts:
                    account = input("Nome da conta para executar: ").strip() 
                    if account in accounts:
                        self.run_account(account)
                else:
                    print("ERRO: Nenhuma conta disponível")
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(accounts):
                        self.run_account(accounts[idx])
                except ValueError:
                    print("ERRO: Opção inválida")

if __name__ == "__main__":
    manager = TWBManager()
    
    if len(sys.argv) > 1:
        # Modo linha de comando
        command = sys.argv[1]
        
        if command == "list":
            accounts = manager.list_accounts()
            if accounts:
                print("Contas disponíveis:")
                for account in accounts:
                    print(f"  - {account}")
            else:
                print("Nenhuma conta configurada")
                
        elif command == "run" and len(sys.argv) > 2:
            manager.run_account(sys.argv[2])
            
        elif command == "info" and len(sys.argv) > 2:
            manager.show_account_info(sys.argv[2])
            
        elif command == "create" and len(sys.argv) > 2:
            base_config = sys.argv[3] if len(sys.argv) > 3 else None
            manager.create_account(sys.argv[2], base_config)
            
        else:
            print("Uso:")
            print("  python manager_geral.py list")
            print("  python manager_geral.py run <conta>") 
            print("  python manager_geral.py info <conta>")
            print("  python manager_geral.py create <conta> [config_base]")
    else:
        # Modo interativo
        manager.menu()