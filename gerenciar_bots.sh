#!/bin/bash

# TWB Multi-Account Manager
# Professional launcher script for BOT-TW-v2
# Author: System Administrator
# Version: 2.0 - Enhanced with individual account control

# ============================================
# CONFIGURATION
# ============================================

# Account list - modify as needed
ACCOUNTS=(
    "CONTA001"
    "CONTA002"
    "CONTA003"
    "CONTA004"
    #"CONTA005"
    "CONTA006"
    "CONTA007"
    "CONTA008"
    "CONTA009"
    "CONTA010"
    "CONTA011"
    "CONTA012"
    "CONTA013"
    "CONTA014"
    "CONTA015"
    "CONTA016"
    "CONTA017"
    "CONTA018"
    "CONTA019"
)

# Project directory
PROJECT_DIR="/home/peelegrino/TribalWars/BOT-TW-v2"

# Python command - AJUSTADO PARA USAR AMBIENTE VIRTUAL
PYTHON_CMD="$PROJECT_DIR/venv/bin/python"

# Delay between account launches (seconds)
LAUNCH_DELAY=3

# ============================================
# FUNCTIONS
# ============================================

# Check if virtual environment exists
check_venv() {
    if [ ! -f "$PYTHON_CMD" ]; then
        echo "[ERROR] Virtual environment not found at: $PYTHON_CMD"
        echo "[INFO] Use 'python3' instead or run setup command"
        PYTHON_CMD="python3"
        return 1
    fi
    return 0
}

# Check if account exists in the accounts list
is_valid_account() {
    local account=$1
    for valid_account in "${ACCOUNTS[@]}"; do
        if [ "$valid_account" = "$account" ]; then
            return 0
        fi
    done
    return 1
}

# Check if account exists and is configured
validate_account() {
    local account=$1
    cd "$PROJECT_DIR" || return 1
    
    check_venv
    
    if $PYTHON_CMD manager_geral.py list | grep -q "^  - $account$"; then
        return 0
    else
        return 1
    fi
}

# Check if account is already running
is_account_running() {
    local account=$1
    screen -list | grep -q "\\.$account\\s"
}

# Start a single account
start_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' is not in the configured accounts list"
        return 1
    fi
    
    if is_account_running "$account"; then
        echo "[INFO] $account: Already running"
        return 0
    fi
    
    if ! validate_account "$account"; then
        echo "[ERROR] $account: Not found or misconfigured"
        return 1
    fi
    
    echo "[START] Launching $account..."
    
    screen -dmS "$account" bash -c "
        cd '$PROJECT_DIR' || exit 1
        echo '[$(date)] Starting account: $account'
        echo '[$(date)] Project directory: $PROJECT_DIR'
        echo '[$(date)] Using Python: $PYTHON_CMD'
        
        $PYTHON_CMD manager_geral.py run '$account'
        
        # Keep session open if bot stops
        echo ''
        echo '[$(date)] Bot process for $account has stopped'
        echo 'Possible reasons:'
        echo '  - CAPTCHA detection required'
        echo '  - Session expired'
        echo '  - Network connection issues'
        echo '  - Configuration error'
        echo '  - Missing dependencies'
        echo ''
        echo 'Press Enter to close this session...'
        read
    "
    
    sleep 2
    
    # Verify if account started successfully
    if is_account_running "$account"; then
        echo "[SUCCESS] $account: Started successfully"
        return 0
    else
        echo "[ERROR] $account: Failed to start"
        return 1
    fi
}

# Stop a single account
stop_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' is not in the configured accounts list"
        return 1
    fi
    
    if is_account_running "$account"; then
        screen -S "$account" -X quit 2>/dev/null
        echo "[SUCCESS] $account: Stopped"
        return 0
    else
        echo "[INFO] $account: Not running"
        return 1
    fi
}

# Restart a single account
restart_account() {
    local account=$1
    
    echo "[RESTART] Restarting $account..."
    stop_account "$account"
    sleep 3
    start_account "$account"
}

# Show status of a single account
show_account_status() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' is not in the configured accounts list"
        return 1
    fi
    
    echo "[STATUS] Account: $account"
    echo "=================================="
    
    if ! validate_account "$account"; then
        echo "[ERROR] Not configured or not found"
        return 1
    elif is_account_running "$account"; then
        echo "[RUNNING] Account is active"
        echo ""
        echo "Screen session info:"
        screen -list | grep "$account" || echo "  Session not found in screen list"
    else
        echo "[STOPPED] Account is not running"
    fi
    
    echo ""
    echo "To access this account: screen -r $account"
    echo "To kill this account: screen -S $account -X quit"
}

# Stop all configured accounts
stop_all_accounts() {
    echo "[STOP] Stopping all configured accounts..."
    
    local stopped_count=0
    local not_running_count=0
    
    for account in "${ACCOUNTS[@]}"; do
        if is_account_running "$account"; then
            screen -S "$account" -X quit 2>/dev/null
            echo "   [STOP] $account: Terminated"
            ((stopped_count++))
        else
            echo "   [INFO] $account: Not running"
            ((not_running_count++))
        fi
    done
    
    echo "[RESULT] Stopped: $stopped_count | Already stopped: $not_running_count"
}

# Display account status
show_status() {
    echo "[STATUS] Account status report"
    echo "=========================================="
    
    if ! command -v screen &> /dev/null; then
        echo "[ERROR] Screen utility not installed"
        echo "       Install with: sudo apt install screen"
        return 1
    fi
    
    check_venv
    
    local running_count=0
    local stopped_count=0
    local invalid_count=0
    local total_accounts=${#ACCOUNTS[@]}
    
    for account in "${ACCOUNTS[@]}"; do
        if ! validate_account "$account"; then
            echo "   [ERROR] $account: Not configured"
            ((invalid_count++))
        elif is_account_running "$account"; then
            echo "   [RUNNING] $account"
            ((running_count++))
        else
            echo "   [STOPPED] $account"
            ((stopped_count++))
        fi
    done
    
    echo "=========================================="
    echo "[SUMMARY] Total: $total_accounts | Running: $running_count | Stopped: $stopped_count | Invalid: $invalid_count"
    
    # Show all active screen sessions
    echo ""
    echo "[SCREEN] Active sessions:"
    screen -list 2>/dev/null || echo "   No active sessions"
}

# Start all configured accounts
start_all_accounts() {
    echo "[START] Launching all configured accounts..."
    echo "[INFO] Project directory: $PROJECT_DIR"
    echo "[INFO] Python command: $PYTHON_CMD"
    echo ""
    
    check_venv
    
    local started_count=0
    local already_running_count=0
    local error_count=0
    
    for account in "${ACCOUNTS[@]}"; do
        if ! validate_account "$account"; then
            echo "   [ERROR] $account: Not found or misconfigured"
            ((error_count++))
        elif is_account_running "$account"; then
            echo "   [INFO] $account: Already running"
            ((already_running_count++))
        else
            echo "   [LAUNCHING] $account..."
            if start_account "$account" > /dev/null 2>&1; then
                echo "   [SUCCESS] $account: Started"
                ((started_count++))
            else
                echo "   [ERROR] $account: Failed to start"
                ((error_count++))
            fi
            sleep $LAUNCH_DELAY
        fi
    done
    
    echo ""
    echo "[COMPLETED] Launch process finished"
    echo "[RESULT] Started: $started_count | Already running: $already_running_count | Errors: $error_count"
    echo ""
    echo "[INFO] Use './$(basename $0) status' to monitor accounts"
    echo "[INFO] Use 'screen -r ACCOUNT_NAME' to access specific account"
}

# Restart all accounts
restart_all_accounts() {
    echo "[RESTART] Restarting all accounts..."
    stop_all_accounts
    echo "[WAIT] Waiting 5 seconds for cleanup..."
    sleep 5
    echo ""
    start_all_accounts
}

# List all configured accounts
list_accounts() {
    echo "[ACCOUNTS] Configured accounts:"
    echo "=============================="
    
    local count=1
    for account in "${ACCOUNTS[@]}"; do
        if is_account_running "$account"; then
            status="[RUNNING]"
        else
            status="[STOPPED]"
        fi
        echo "  $count. $account $status"
        ((count++))
    done
    
    echo ""
    echo "Total accounts: ${#ACCOUNTS[@]}"
}

# Connect to an account screen session
connect_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' is not in the configured accounts list"
        return 1
    fi
    
    if is_account_running "$account"; then
        echo "[INFO] Connecting to $account..."
        echo "[INFO] Press Ctrl+A then D to detach from session"
        screen -r "$account"
    else
        echo "[ERROR] $account is not running"
        echo "[INFO] Start it first with: $0 start-account $account"
        return 1
    fi
}

# Display help information
show_help() {
    echo "TWB Multi-Account Manager"
    echo "========================="
    echo ""
    echo "Usage: $0 {command} [account_name]"
    echo ""
    echo "GLOBAL COMMANDS:"
    echo "  start              Launch all configured accounts"
    echo "  stop               Stop all running accounts"
    echo "  status             Display all accounts status"
    echo "  restart            Stop and restart all accounts"
    echo "  list               List all configured accounts"
    echo "  help               Show this help message"
    echo ""
    echo "INDIVIDUAL ACCOUNT COMMANDS:"
    echo "  start-account CONTA    Start specific account"
    echo "  stop-account CONTA     Stop specific account"
    echo "  restart-account CONTA  Restart specific account"
    echo "  status-account CONTA   Show specific account status"
    echo "  connect CONTA          Connect to account screen session"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 start                    # Start all accounts"
    echo "  $0 start-account CONTA001   # Start only CONTA001"
    echo "  $0 stop-account CONTA002    # Stop only CONTA002"
    echo "  $0 connect CONTA001         # Connect to CONTA001 session"
    echo "  $0 status-account CONTA003  # Show CONTA003 status"
    echo ""
    echo "Configuration:"
    echo "  Project directory: $PROJECT_DIR"
    echo "  Python command: $PYTHON_CMD"
    echo "  Launch delay: ${LAUNCH_DELAY}s"
    echo "  Total accounts: ${#ACCOUNTS[@]}"
    echo ""
    echo "Virtual Environment:"
    if [ -f "$PYTHON_CMD" ]; then
        echo "  [OK] Virtual environment found"
    else
        echo "  [WARNING] Using system Python: python3"
    fi
    echo ""
    echo "Screen commands:"
    echo "  screen -list                 List all sessions"
    echo "  screen -r ACCOUNT_NAME       Access specific account"
    echo "  Ctrl+A then D               Detach from session"
    echo "  screen -S ACCOUNT_NAME -X quit  Kill specific session"
}

# ============================================
# MAIN EXECUTION
# ============================================

# Check if we're in the correct directory
if [ ! -f "$PROJECT_DIR/manager_geral.py" ]; then
    echo "[ERROR] Project directory not found or invalid: $PROJECT_DIR"
    echo "[ERROR] Please verify the PROJECT_DIR variable in this script"
    exit 1
fi

# Process command line arguments
case "$1" in
    "start")
        start_all_accounts
        ;;
    "stop")
        stop_all_accounts
        ;;
    "status")
        show_status
        ;;
    "restart")
        restart_all_accounts
        ;;
    "list")
        list_accounts
        ;;
    "start-account")
        if [ -z "$2" ]; then
            echo "[ERROR] Account name required"
            echo "Usage: $0 start-account CONTA_NAME"
            echo "Example: $0 start-account CONTA001"
            exit 1
        fi
        start_account "$2"
        ;;
    "stop-account")
        if [ -z "$2" ]; then
            echo "[ERROR] Account name required"
            echo "Usage: $0 stop-account CONTA_NAME"
            echo "Example: $0 stop-account CONTA001"
            exit 1
        fi
        stop_account "$2"
        ;;
    "restart-account")
        if [ -z "$2" ]; then
            echo "[ERROR] Account name required"
            echo "Usage: $0 restart-account CONTA_NAME"
            echo "Example: $0 restart-account CONTA001"
            exit 1
        fi
        restart_account "$2"
        ;;
    "status-account")
        if [ -z "$2" ]; then
            echo "[ERROR] Account name required"
            echo "Usage: $0 status-account CONTA_NAME"
            echo "Example: $0 status-account CONTA001"
            exit 1
        fi
        show_account_status "$2"
        ;;
    "connect")
        if [ -z "$2" ]; then
            echo "[ERROR] Account name required"
            echo "Usage: $0 connect CONTA_NAME"
            echo "Example: $0 connect CONTA001"
            exit 1
        fi
        connect_account "$2"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        echo "[ERROR] Invalid command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac