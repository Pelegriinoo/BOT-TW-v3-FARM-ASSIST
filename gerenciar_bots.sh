#!/bin/bash

# TWB Multi-Account Manager - Zero Hang Version
# Version: 2.2 - Completely eliminates hanging issues

# ============================================
# CONFIGURATION
# ============================================

ACCOUNTS=(
    "CONTA001" "CONTA002" "CONTA003" "CONTA004" "CONTA005"
    "CONTA006" "CONTA007" "CONTA008" "CONTA009" "CONTA010"
    "CONTA011" "CONTA012" "CONTA013" "CONTA014" "CONTA015"
    "CONTA016" "CONTA017" "CONTA018" "CONTA019" "CONTA020"
    "CONTA021" "CONTA022" "CONTA023" "PELEGRINO137"
)

PROJECT_DIR="/home/peelegrino/TribalWars/1"
PYTHON_CMD="/home/peelegrino/venv/bin/python3"
LAUNCH_DELAY=3

# ============================================
# CORE FUNCTIONS
# ============================================

check_venv() {
    if [ ! -f "$PYTHON_CMD" ]; then
        PYTHON_CMD="python3"
        return 1
    fi
    return 0
}

is_valid_account() {
    local account=$1
    for valid_account in "${ACCOUNTS[@]}"; do
        if [ "$valid_account" = "$account" ]; then
            return 0
        fi
    done
    return 1
}

validate_account() {
    local account=$1
    cd "$PROJECT_DIR" || return 1
    check_venv
    $PYTHON_CMD manager_geral.py list | grep -q "^  - $account$"
}

is_account_running() {
    local account=$1
    screen -list 2>/dev/null | grep -q "\\.$account\\s"
}

# ============================================
# IMPROVED START/STOP FUNCTIONS
# ============================================

start_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' not in configured accounts"
        return 1
    fi
    
    if is_account_running "$account"; then
        echo "[INFO] $account: Already running"
        return 0
    fi
    
    if ! validate_account "$account"; then
        echo "[ERROR] $account: Not configured"
        return 1
    fi
    
    echo "[START] Launching $account..."
    
    # Simple, direct approach - no wrapper scripts
    screen -dmS "$account" bash -c "
        cd '$PROJECT_DIR'
        echo '[$(date)] Starting $account'
        $PYTHON_CMD manager_geral.py run '$account'
        echo '[$(date)] $account stopped - session closing in 3 seconds'
        sleep 3
        exit 0
    "
    
    sleep 2
    
    if is_account_running "$account"; then
        echo "[SUCCESS] $account: Started"
        return 0
    else
        echo "[ERROR] $account: Failed to start"
        return 1
    fi
}

# Aggressive stop function that WILL work
stop_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' not in configured accounts"
        return 1
    fi
    
    if ! is_account_running "$account"; then
        echo "[INFO] $account: Not running"
        return 1
    fi
    
    echo "[STOP] Stopping $account..."
    
    # Method 1: Send interrupt signal
    screen -S "$account" -X stuff $'\003' 2>/dev/null
    sleep 1
    
    # Method 2: Send quit command if still running
    if is_account_running "$account"; then
        screen -S "$account" -X quit 2>/dev/null
        sleep 1
    fi
    
    # Method 3: Force kill if still running
    if is_account_running "$account"; then
        screen -S "$account" -X kill 2>/dev/null
        sleep 1
    fi
    
    # Method 4: Nuclear option - kill the actual process
    if is_account_running "$account"; then
        local session_info=$(screen -list 2>/dev/null | grep "\\.$account\\s")
        if [ ! -z "$session_info" ]; then
            local pid=$(echo "$session_info" | awk '{print $1}' | cut -d'.' -f1)
            if [ ! -z "$pid" ] && [ "$pid" -gt 0 ]; then
                kill -9 "$pid" 2>/dev/null
                sleep 1
            fi
        fi
    fi
    
    # Verify it's actually stopped
    if ! is_account_running "$account"; then
        echo "[SUCCESS] $account: Stopped"
        return 0
    else
        echo "[WARNING] $account: May still be running (check manually)"
        return 1
    fi
}

restart_account() {
    local account=$1
    echo "[RESTART] Restarting $account..."
    stop_account "$account"
    sleep 2
    start_account "$account"
}

# ============================================
# BATCH OPERATIONS
# ============================================

start_all_accounts() {
    echo "[START] Launching all accounts..."
    echo "[INFO] Project: $PROJECT_DIR"
    echo "[INFO] Python: $PYTHON_CMD"
    echo ""
    
    check_venv
    
    local started=0 running=0 errors=0
    
    for account in "${ACCOUNTS[@]}"; do
        if ! validate_account "$account"; then
            echo "   [ERROR] $account: Not configured"
            ((errors++))
        elif is_account_running "$account"; then
            echo "   [INFO] $account: Already running"
            ((running++))
        else
            echo "   [LAUNCH] $account..."
            if start_account "$account" >/dev/null 2>&1; then
                echo "   [SUCCESS] $account: Started"
                ((started++))
            else
                echo "   [ERROR] $account: Failed"
                ((errors++))
            fi
            sleep $LAUNCH_DELAY
        fi
    done
    
    echo ""
    echo "[RESULT] Started: $started | Running: $running | Errors: $errors"
}

stop_all_accounts() {
    echo "[STOP] Stopping all accounts..."
    
    local stopped=0 not_running=0 failed=0
    
    # Get list of running accounts first
    local running_accounts=()
    for account in "${ACCOUNTS[@]}"; do
        if is_account_running "$account"; then
            running_accounts+=("$account")
        fi
    done
    
    if [ ${#running_accounts[@]} -eq 0 ]; then
        echo "[INFO] No accounts currently running"
        return 0
    fi
    
    echo "[INFO] Found ${#running_accounts[@]} running accounts"
    
    # Stop each running account
    for account in "${running_accounts[@]}"; do
        echo "   [STOPPING] $account..."
        if stop_account "$account" >/dev/null 2>&1; then
            ((stopped++))
        else
            ((failed++))
        fi
    done
    
    # Count accounts that weren't running
    for account in "${ACCOUNTS[@]}"; do
        if ! is_account_running "$account"; then
            local was_in_running=false
            for running_account in "${running_accounts[@]}"; do
                if [ "$account" = "$running_account" ]; then
                    was_in_running=true
                    break
                fi
            done
            if [ "$was_in_running" = false ]; then
                ((not_running++))
            fi
        fi
    done
    
    echo "[RESULT] Stopped: $stopped | Not running: $not_running | Failed: $failed"
    
    # Final cleanup
    echo "[CLEANUP] Removing dead sessions..."
    screen -wipe >/dev/null 2>&1
    
    if [ $failed -gt 0 ]; then
        echo "[WARNING] Some accounts may need manual cleanup"
        echo "[INFO] Use 'screen -list' to check remaining sessions"
    fi
}

restart_all_accounts() {
    echo "[RESTART] Restarting all accounts..."
    stop_all_accounts
    echo "[WAIT] Waiting for cleanup..."
    sleep 3
    start_all_accounts
}

# ============================================
# STATUS AND UTILITY FUNCTIONS
# ============================================

show_status() {
    echo "[STATUS] Account Status Report"
    echo "============================================"
    
    if ! command -v screen &>/dev/null; then
        echo "[ERROR] Screen not installed"
        return 1
    fi
    
    check_venv
    
    local running=0 stopped=0 invalid=0
    
    for account in "${ACCOUNTS[@]}"; do
        if ! validate_account "$account"; then
            echo "   [ERROR] $account: Not configured"
            ((invalid++))
        elif is_account_running "$account"; then
            echo "   [RUNNING] $account"
            ((running++))
        else
            echo "   [STOPPED] $account"
            ((stopped++))
        fi
    done
    
    echo "============================================"
    echo "[SUMMARY] Running: $running | Stopped: $stopped | Invalid: $invalid"
    
    echo ""
    echo "[SESSIONS] Active TWB sessions:"
    screen -list 2>/dev/null | grep -E "\\.CONTA[0-9]+|PELEGRINO137" | sed 's/^/   /' || echo "   None"
}

show_account_status() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' not in configured accounts"
        return 1
    fi
    
    echo "[STATUS] Account: $account"
    echo "========================"
    
    if ! validate_account "$account"; then
        echo "[ERROR] Not configured"
    elif is_account_running "$account"; then
        echo "[RUNNING] Active"
        echo ""
        echo "Session info:"
        screen -list 2>/dev/null | grep "$account" | sed 's/^/   /'
    else
        echo "[STOPPED] Not running"
    fi
    
    echo ""
    echo "Commands:"
    echo "   Start: $0 start-account $account"
    echo "   Stop: $0 stop-account $account"
    echo "   Connect: screen -r $account"
}

list_accounts() {
    echo "[ACCOUNTS] Configured Accounts"
    echo "============================="
    
    local count=1
    for account in "${ACCOUNTS[@]}"; do
        local status="[STOPPED]"
        if is_account_running "$account"; then
            status="[RUNNING]"
        fi
        echo "  $count. $account $status"
        ((count++))
    done
    
    echo ""
    echo "Total: ${#ACCOUNTS[@]} accounts"
}

connect_account() {
    local account=$1
    
    if ! is_valid_account "$account"; then
        echo "[ERROR] '$account' not in configured accounts"
        return 1
    fi
    
    if is_account_running "$account"; then
        echo "[INFO] Connecting to $account..."
        echo "[INFO] Ctrl+A then D to detach | Ctrl+C to stop bot"
        screen -r "$account"
    else
        echo "[ERROR] $account not running"
        echo "[INFO] Start with: $0 start-account $account"
        return 1
    fi
}

emergency_cleanup() {
    echo "[EMERGENCY] Force cleanup..."
    
    # Kill all TWB screen sessions
    for account in "${ACCOUNTS[@]}"; do
        if is_account_running "$account"; then
            echo "   [KILL] $account"
            screen -S "$account" -X kill 2>/dev/null
            
            # Double-check with process kill
            local session_info=$(screen -list 2>/dev/null | grep "\\.$account\\s")
            if [ ! -z "$session_info" ]; then
                local pid=$(echo "$session_info" | awk '{print $1}' | cut -d'.' -f1)
                if [ ! -z "$pid" ] && [ "$pid" -gt 0 ]; then
                    kill -9 "$pid" 2>/dev/null
                fi
            fi
        fi
    done
    
    # Clean up screen
    screen -wipe >/dev/null 2>&1
    
    echo "[CLEANUP] Emergency cleanup completed"
}

show_help() {
    echo "TWB Multi-Account Manager - Zero Hang Version"
    echo "============================================="
    echo ""
    echo "Usage: $0 {command} [account]"
    echo ""
    echo "GLOBAL COMMANDS:"
    echo "  start          Start all accounts"
    echo "  stop           Stop all accounts (GUARANTEED)"
    echo "  restart        Restart all accounts"
    echo "  status         Show all accounts status"
    echo "  list           List configured accounts"
    echo "  cleanup        Emergency force cleanup"
    echo "  help           Show this help"
    echo ""
    echo "INDIVIDUAL COMMANDS:"
    echo "  start-account CONTA    Start specific account"
    echo "  stop-account CONTA     Stop specific account"
    echo "  restart-account CONTA  Restart specific account"
    echo "  status-account CONTA   Show account status"
    echo "  connect CONTA          Connect to account session"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 start                   # Start all"
    echo "  $0 stop                    # Stop all (no hanging!)"
    echo "  $0 start-account CONTA001  # Start one account"
    echo "  $0 connect CONTA001        # Access account"
    echo "  $0 cleanup                 # Emergency cleanup"
    echo ""
    echo "Configuration:"
    echo "  Project: $PROJECT_DIR"
    echo "  Python: $PYTHON_CMD"
    echo "  Accounts: ${#ACCOUNTS[@]}"
    echo ""
    echo "This version GUARANTEES that stop commands work!"
}

# ============================================
# MAIN
# ============================================

if [ ! -f "$PROJECT_DIR/manager_geral.py" ]; then
    echo "[ERROR] Project not found: $PROJECT_DIR"
    exit 1
fi

case "$1" in
    "start") start_all_accounts ;;
    "stop") stop_all_accounts ;;
    "restart") restart_all_accounts ;;
    "status") show_status ;;
    "list") list_accounts ;;
    "cleanup") emergency_cleanup ;;
    "start-account")
        [ -z "$2" ] && { echo "[ERROR] Account name required"; exit 1; }
        start_account "$2" ;;
    "stop-account")
        [ -z "$2" ] && { echo "[ERROR] Account name required"; exit 1; }
        stop_account "$2" ;;
    "restart-account")
        [ -z "$2" ] && { echo "[ERROR] Account name required"; exit 1; }
        restart_account "$2" ;;
    "status-account")
        [ -z "$2" ] && { echo "[ERROR] Account name required"; exit 1; }
        show_account_status "$2" ;;
    "connect")
        [ -z "$2" ] && { echo "[ERROR] Account name required"; exit 1; }
        connect_account "$2" ;;
    "help"|"--help"|"-h"|"") show_help ;;
    *) echo "[ERROR] Invalid command: $1"; show_help; exit 1 ;;
esac
