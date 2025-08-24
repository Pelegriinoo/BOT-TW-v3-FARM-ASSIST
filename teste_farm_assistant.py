#!/usr/bin/env python3
"""
Teste rápido do Farm Assistant
Execute este script na pasta do TWB para testar o Farm Assistant
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'TWB_Library'))

# Teste de import
print("🔍 Testando imports...")

try:
    from game.farm_assistant import FarmAssistantManager
    print("✅ FarmAssistantManager importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar FarmAssistantManager: {e}")
    exit(1)

try:
    import statistics
    print("✅ statistics module disponível")
except ImportError as e:
    print(f"❌ Erro ao importar statistics: {e}")
    exit(1)

try:
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup4 disponível")
except ImportError as e:
    print(f"❌ Erro ao importar BeautifulSoup4: {e}")
    print("💡 Instale com: pip install beautifulsoup4")
    exit(1)

try:
    from game.attack import AttackManager
    print("✅ AttackManager disponível")
except ImportError as e:
    print(f"❌ Erro ao importar AttackManager: {e}")
    exit(1)

print()
print("🎉 TODOS OS IMPORTS FUNCIONARAM!")
print()
print("📋 PRÓXIMOS PASSOS:")
print("1. Inicie o bot normalmente")
print("2. Verifique se aparecem as mensagens de debug do Farm Assistant")
print("3. Se não funcionar, verifique se tem premium ativo no jogo")
print("4. Configure templates A/B no assistente do jogo")
