#!/bin/bash
# Simple management script for the embedding processor

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESSOR="$SCRIPT_DIR/embedding_processor_robust.py"
WATCHDOG="$SCRIPT_DIR/embedding_watchdog.py"
PID_FILE="/tmp/kg_rag_processor_robust.pid"

show_help() {
    echo "KG RAG Embedding Processor Management"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|watchdog-start|watchdog-stop}"
    echo ""
    echo "Commands:"
    echo "  start          - Start the processor"
    echo "  stop           - Stop the processor"
    echo "  restart        - Restart the processor"
    echo "  status         - Check processor status"
    echo "  logs           - Show processor logs (tail -f)"
    echo "  stats          - Show embedding statistics"
    echo "  watchdog-start - Start watchdog daemon"
    echo "  watchdog-stop  - Stop watchdog daemon"
    echo "  check          - Run health check"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs"
    echo "  $0 status"
}

case "${1:-}" in
    start)
        echo "Starting embedding processor..."
        nohup python3 "$PROCESSOR" > /tmp/kg_rag_processor.out 2>&1 &
        sleep 2
        $0 status
        ;;
    
    stop)
        echo "Stopping embedding processor..."
        python3 "$PROCESSOR" --stop
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        python3 "$PROCESSOR" --status
        ;;
    
    logs)
        echo "Showing logs (Ctrl+C to exit)..."
        tail -f /tmp/kg_rag_processor_robust.log
        ;;
    
    stats)
        echo "Fetching embedding statistics..."
        cd "$SCRIPT_DIR" && python3 monitor_embeddings.py 2>/dev/null || echo "monitor_embeddings.py not found"
        ;;
    
    watchdog-start)
        echo "Starting watchdog daemon..."
        nohup python3 "$WATCHDOG" --daemon > /tmp/kg_rag_watchdog.log 2>&1 &
        echo "Watchdog started"
        ;;
    
    watchdog-stop)
        echo "Stopping watchdog daemon..."
        pkill -f "embedding_watchdog.py --daemon" 2>/dev/null || echo "Watchdog not running"
        ;;
    
    check)
        echo "Running health check..."
        python3 "$WATCHDOG"
        ;;
    
    *)
        show_help
        exit 1
        ;;
esac
