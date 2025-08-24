# TWB Multi-Account Commands Reference - Atualizado

## 🔧 Comandos do Script Principal

### Navegação e Ativação
```bash
# Navegar para o projeto (ATUALIZADO)
cd ~/TribalWars/1

# Ativar ambiente virtual (ATUALIZADO)
source venv/bin/activate
```

### Comandos do Gerenciador
```bash
# Ver ajuda completa
./gerenciar_bots.sh help

# Ver status de todas as contas
./gerenciar_bots.sh status

# Iniciar todas as contas configuradas
./gerenciar_bots.sh start

# Parar todas as contas
./gerenciar_bots.sh stop

# Reiniciar todas as contas
./gerenciar_bots.sh restart

# Listar contas configuradas
./gerenciar_bots.sh list
```

### 🆕 Comandos Individuais por Conta
```bash
# Iniciar uma conta específica
./gerenciar_bots.sh start-account CONTA001

# Parar uma conta específica
./gerenciar_bots.sh stop-account CONTA001

# Reiniciar uma conta específica
./gerenciar_bots.sh restart-account CONTA001

# Ver status de uma conta específica
./gerenciar_bots.sh status-account CONTA001

# Conectar a uma conta específica
./gerenciar_bots.sh connect CONTA001
```

## 🖥️ Comandos de Gerenciamento Screen

### Visualização e Acesso
```bash
# Ver todas as sessões ativas
screen -list

# Acessar uma conta específica
screen -r CONTA001

# Sair do screen (volta pro terminal principal)
# Pressione: Ctrl+A depois D
```

### Controle de Sessões
```bash
# Parar uma conta específica
screen -S CONTA001 -X quit

# Parar todas as sessões screen
killall screen
```

## ⚙️ Comandos de Configuração

### Gerenciamento de Contas
```bash
# Listar contas disponíveis
python3 manager_geral.py list
# ou com ambiente virtual ativo:
./venv/bin/python manager_geral.py list

# Configurar uma conta específica
python3 start.py config CONTA001

# Criar nova conta
python3 setup_account.py NOVA_CONTA

# Testar uma conta manualmente
python3 manager_geral.py run CONTA001
```

## 📊 Comandos de Monitoramento

### Monitoramento de Processos
```bash
# Ver processos Python rodando
ps aux | grep python | grep manager_geral

# Ver uso de recursos do sistema
htop
# ou
top

# Ver logs do sistema
tail -f /var/log/syslog
```

### Estatísticas
```bash
# Ver uso de memória por conta
ps aux | grep "manager_geral" | awk '{print $11, $4"%"}'

# Contar quantas contas estão rodando
screen -list | grep CONTA | wc -l
```

## 🔄 Comandos de Manutenção

### Dependências e Sistema
```bash
# Atualizar dependências (ATUALIZADO - sem TWB_Library)
pip install -r requirements.txt --upgrade

# Verificar dependências
python3 -c "import coloredlogs, selenium, requests; print('Dependências OK')"

# Backup de configurações
cp -r accounts/ backup_accounts_$(date +%Y%m%d)
```

### Informações do Sistema
```bash
# Ver espaço em disco
df -h

# Ver informações do servidor
uname -a
```

## 📝 Comandos de Edição

### Configuração do Script
```bash
# Editar script principal
nano gerenciar_bots.sh

# Editar lista de contas no script
nano gerenciar_bots.sh
# Procurar: ACCOUNTS=(
```

### Configuração de Contas
```bash
# Ver configuração de uma conta
cat accounts/CONTA001/config.json

# Editar configuração de uma conta
nano accounts/CONTA001/config.json
```

## 🚀 Sequência de Inicialização Completa

```bash
# 1. SSH no servidor
ssh peelegrino@178.156.187.40

# 2. Ir para o projeto (ATUALIZADO)
cd ~/TribalWars/1

# 3. Ativar ambiente virtual
source venv/bin/activate

# 4. Ver status
./gerenciar_bots.sh status

# 5. Iniciar todas as contas
./gerenciar_bots.sh start

# 6. Monitorar
./gerenciar_bots.sh status
```

## 🛑 Sequência de Parada Completa

```bash
# 1. Parar todas as contas
./gerenciar_bots.sh stop

# 2. Verificar se pararam
./gerenciar_bots.sh status

# 3. Limpeza se necessário
killall screen

# 4. Sair do SSH (opcional)
exit
```

## 🔍 Troubleshooting

### Problemas Comuns
```bash
# Se ambiente virtual não ativar (ATUALIZADO)
cd ~/TribalWars/1
python3 -m venv venv
source venv/bin/activate

# Se dependências estiverem faltando (ATUALIZADO)
pip install -r requirements.txt

# Se contas não iniciarem
python3 manager_geral.py run CONTA001  # teste manual

# Se screen não responder
killall screen  # força parada

# Se script não executar
chmod +x gerenciar_bots.sh  # dar permissão de execução
```

### Verificações de Saúde
```bash
# Verificar se projeto está correto
ls -la manager_geral.py

# Verificar se ambiente virtual está ativo
which python3  # deve mostrar caminho do venv quando ativo

# Verificar se script está executável
ls -la gerenciar_bots.sh  # deve ter 'x' nas permissões

# Verificar se ambiente virtual existe
ls -la venv/bin/python
```

## 📋 Comandos de Diagnóstico

### Sistema
```bash
# Ver memória disponível
free -h

# Ver CPU
cat /proc/cpuinfo | grep "model name" | head -1

# Ver uptime do servidor
uptime
```

### Rede
```bash
# Testar conexão internet
ping -c 4 google.com

# Ver conexões ativas
netstat -an | grep :80
```

## 🆕 Exemplos de Uso Individual

### Gerenciar Conta Específica
```bash
# Iniciar apenas CONTA001
./gerenciar_bots.sh start-account CONTA001

# Ver se CONTA001 está rodando
./gerenciar_bots.sh status-account CONTA001

# Conectar à sessão da CONTA001
./gerenciar_bots.sh connect CONTA001

# Parar apenas CONTA001
./gerenciar_bots.sh stop-account CONTA001

# Reiniciar CONTA001
./gerenciar_bots.sh restart-account CONTA001
```

### Cenários Comuns
```bash
# Iniciar algumas contas específicas
./gerenciar_bots.sh start-account CONTA001
./gerenciar_bots.sh start-account CONTA003
./gerenciar_bots.sh start-account CONTA005

# Ver status geral
./gerenciar_bots.sh status

# Parar uma conta problemática e reiniciar
./gerenciar_bots.sh stop-account CONTA002
./gerenciar_bots.sh start-account CONTA002
```

## 📍 Informações do Sistema Atual

### Configuração Atual
- **Diretório do projeto**: `/home/peelegrino/TribalWars/1`
- **Python**: Ambiente virtual em `./venv/bin/python`
- **Delay entre lançamentos**: 3 segundos
- **Contas configuradas**: CONTA001 até CONTA020 (CONTA005 comentada)

### Estrutura de Arquivos
```
~/TribalWars/1/
├── gerenciar_bots.sh          # Script principal
├── manager_geral.py           # Gerenciador Python
├── venv/                      # Ambiente virtual
├── accounts/                  # Configurações das contas
├── requirements.txt           # Dependências
└── ...
```

---

**Mantenha este arquivo atualizado conforme suas necessidades!**
