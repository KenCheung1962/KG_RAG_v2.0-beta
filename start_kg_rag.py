#!/usr/bin/env python3
"""
KG RAG System v2.0-beta - Initialization & Startup Script (Python)
Uses kgrag_config.yaml for configuration
"""

import os
import sys
import time
import signal
import subprocess
import requests
import argparse
from pathlib import Path
from typing import Optional, List, Dict
import yaml

#==============================================================================
# Configuration Loading
#==============================================================================

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'

class KGRAGConfig:
    """Configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.script_dir = Path(__file__).parent.absolute()
        self.config_path = Path(config_path) if config_path else self.script_dir / "kgrag_config.yaml"
        self.config = self._load_config()
        self._apply_env_overrides()
        
    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            print(f"{Colors.YELLOW}⚠ Config file not found: {self.config_path}{Colors.NC}")
            return self._default_config()
            
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Error loading config: {e}{Colors.NC}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        return {
            'services': {
                'backend': {'enabled': True, 'port': 8002, 'host': '127.0.0.1',
                           'script': 'pgvector_api.py', 'directory': 'backend',
                           'startup_timeout': 30},
                'frontend': {'enabled': True, 'port': 8081, 'host': True,
                            'directory': 'frontend', 'startup_timeout': 15},
                'db_management_api': {'enabled': True, 'port': 8013,
                                     'script': 'scripts/db-management-api.cjs',
                                     'directory': 'frontend', 'startup_timeout': 10}
            },
            'ollama': {'enabled': True, 'host': 'http://localhost', 'port': 11434,
                      'required_models': ['nomic-embed-text']},
            'database_health': {'min_entities': 1000, 'min_relationships': 1000,
                               'min_chunks': 1000, 'min_documents': 10},
            'logging': {'level': 'INFO'},
            'security': {'api_key': os.getenv('KGRAG_API_KEY', 'dev-only-key')}
        }
    
    def _apply_env_overrides(self):
        env_mappings = {
            'KGRAG_BACKEND_PORT': ['services', 'backend', 'port'],
            'KGRAG_FRONTEND_PORT': ['services', 'frontend', 'port'],
            'KGRAG_DB_API_PORT': ['services', 'db_management_api', 'port'],
            'KGRAG_API_KEY': ['security', 'api_key'],
        }
        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                try:
                    value = int(value) if 'port' in path else value
                    self._set_nested_value(self.config, path, value)
                except ValueError:
                    pass
    
    def _set_nested_value(self, config: Dict, path: list, value):
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, *path, default=None):
        current = self.config
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

#==============================================================================
# Service Manager
#==============================================================================

class ServiceManager:
    def __init__(self, config: KGRAGConfig):
        self.config = config
        self.script_dir = Path(__file__).parent.absolute()
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\n{Colors.BLUE}[INFO] Received signal {signum}, shutting down...{Colors.NC}")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def log_info(self, msg: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")
    
    def log_success(self, msg: str):
        print(f"{Colors.GREEN}[✓]{Colors.NC} {msg}")
    
    def log_warn(self, msg: str):
        print(f"{Colors.YELLOW}[⚠]{Colors.NC} {msg}")
    
    def log_error(self, msg: str):
        print(f"{Colors.RED}[✗]{Colors.NC} {msg}")
    
    def check_port(self, port: int) -> bool:
        """Check if port is available"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running and required models are available"""
        self.log_info("Checking Ollama availability...")
        
        ollama_url = self.config.get('ollama', 'host', default='http://localhost')
        ollama_port = self.config.get('ollama', 'port', default=11434)
        required_models = self.config.get('ollama', 'required_models', default=['nomic-embed-text'])
        url = f"{ollama_url}:{ollama_port}/api/tags"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                self.log_success(f"Ollama is running at {ollama_url}:{ollama_port}")
                
                # Check required models
                if required_models:
                    data = response.json()
                    available_models = [m.get('name', '') for m in data.get('models', [])]
                    
                    missing_models = []
                    for model in required_models:
                        # Check if model or model:latest exists
                        if model not in available_models and f"{model}:latest" not in available_models:
                            missing_models.append(model)
                    
                    if missing_models:
                        self.log_error(f"Required Ollama models not found: {', '.join(missing_models)}")
                        print(f"\n{Colors.YELLOW}To pull the required models, run:{Colors.NC}")
                        for model in missing_models:
                            print(f"  ollama pull {model}")
                        print()
                        return False
                    else:
                        self.log_success(f"Required models available: {', '.join(required_models)}")
                
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            self.log_warn(f"Error checking Ollama: {e}")
        
        self.log_error(f"Ollama is not running at {ollama_url}:{ollama_port}")
        print(f"\n{Colors.YELLOW}To start Ollama, run:{Colors.NC}")
        print("  ollama serve")
        print(f"\n{Colors.YELLOW}Or open the Ollama app from Applications.{Colors.NC}\n")
        return False
    
    def start_backend(self) -> bool:
        """Start the backend service"""
        if not self.config.get('services', 'backend', 'enabled', default=True):
            self.log_info("Backend is disabled in config")
            return True
        
        port = self.config.get('services', 'backend', 'port', default=8002)
        timeout = self.config.get('services', 'backend', 'startup_timeout', default=30)
        
        self.log_info(f"Starting backend on port {port}...")
        
        if not self.check_port(port):
            self.log_error(f"Port {port} is already in use!")
            return False
        
        backend_dir = self.script_dir / self.config.get('services', 'backend', 'directory', default='backend')
        script = self.config.get('services', 'backend', 'script', default='pgvector_api.py')
        
        # Activate virtualenv if exists
        env = os.environ.copy()
        venv_paths = [
            self.script_dir / 'venv' / 'bin',
            backend_dir / 'venv' / 'bin',
        ]
        for venv_path in venv_paths:
            if venv_path.exists():
                env['PATH'] = str(venv_path) + ':' + env.get('PATH', '')
                break
        
        try:
            proc = subprocess.Popen(
                ['python3', script],
                cwd=backend_dir,
                env=env,
                stdout=open('backend.log', 'w'),
                stderr=subprocess.STDOUT
            )
            self.processes['backend'] = proc
            self.log_info(f"Backend PID: {proc.pid}")
            
            # Wait for startup
            for i in range(timeout):
                if proc.poll() is not None:
                    self.log_error("Backend process exited unexpectedly!")
                    return False
                try:
                    response = requests.get(f"http://localhost:{port}/health", timeout=1)
                    if response.status_code == 200:
                        self.log_success(f"Backend is running at http://localhost:{port}")
                        return True
                except:
                    pass
                time.sleep(1)
                print(".", end='', flush=True)
            
            print()
            self.log_error(f"Backend failed to start within {timeout} seconds")
            return False
            
        except Exception as e:
            self.log_error(f"Failed to start backend: {e}")
            return False
    
    def _validate_node_modules(self, frontend_dir: Path) -> bool:
        """Validate that node_modules is not corrupted"""
        node_modules = frontend_dir / 'node_modules'
        if not node_modules.exists():
            return False
        
        # Check for critical files that indicate a working Vite installation
        critical_files = [
            node_modules / '.bin' / 'vite',
            node_modules / '.bin' / 'tsc',
            node_modules / 'vite' / 'package.json',
            node_modules / 'typescript' / 'package.json',
        ]
        
        # Also check for the file that was missing in the corruption
        vite_cli = node_modules / 'vite' / 'dist' / 'node' / 'cli.js'
        
        missing = [f for f in critical_files + [vite_cli] if not f.exists()]
        if missing:
            self.log_warn(f"Corrupted node_modules detected, missing: {[f.name for f in missing[:3]]}...")
            return False
        return True
    
    def _install_dependencies(self, frontend_dir: Path, clean: bool = False) -> bool:
        """Install npm dependencies, optionally cleaning first"""
        if clean:
            self.log_info("Cleaning node_modules and package-lock.json...")
            import shutil
            node_modules = frontend_dir / 'node_modules'
            pkg_lock = frontend_dir / 'package-lock.json'
            if node_modules.exists():
                shutil.rmtree(node_modules)
            if pkg_lock.exists():
                pkg_lock.unlink()
        
        self.log_info("Installing npm dependencies...")
        try:
            result = subprocess.run(
                ['npm', 'install'], 
                cwd=frontend_dir, 
                capture_output=True,
                text=True,
                check=True
            )
            self.log_success("Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"npm install failed: {e.stderr[:200]}")
            return False
        except Exception as e:
            self.log_error(f"Failed to install dependencies: {e}")
            return False

    def start_frontend(self) -> bool:
        """Start the frontend service"""
        if not self.config.get('services', 'frontend', 'enabled', default=True):
            self.log_info("Frontend is disabled in config")
            return True
        
        port = self.config.get('services', 'frontend', 'port', default=8081)
        timeout = self.config.get('services', 'frontend', 'startup_timeout', default=15)
        
        self.log_info(f"Starting frontend on port {port}...")
        
        if not self.check_port(port):
            self.log_error(f"Port {port} is already in use!")
            return False
        
        frontend_dir = self.script_dir / self.config.get('services', 'frontend', 'directory', default='frontend')
        
        # Check and validate node_modules
        if not self._validate_node_modules(frontend_dir):
            if not self._install_dependencies(frontend_dir, clean=True):
                return False
        
        try:
            proc = subprocess.Popen(
                ['npm', 'run', 'dev'],
                cwd=frontend_dir,
                stdout=open('frontend.log', 'w'),
                stderr=subprocess.STDOUT
            )
            self.processes['frontend'] = proc
            self.log_info(f"Frontend PID: {proc.pid}")
            
            # Wait for startup
            for i in range(timeout):
                if proc.poll() is not None:
                    self.log_error("Frontend process exited unexpectedly!")
                    return False
                try:
                    response = requests.get(f"http://localhost:{port}", timeout=1)
                    if response.status_code == 200:
                        self.log_success(f"Frontend is running at http://localhost:{port}")
                        return True
                except:
                    pass
                time.sleep(1)
                print(".", end='', flush=True)
            
            print()
            self.log_error(f"Frontend failed to start within {timeout} seconds")
            return False
            
        except Exception as e:
            self.log_error(f"Failed to start frontend: {e}")
            return False
    
    def start_db_api(self) -> bool:
        """Start the database management API with retry logic"""
        if not self.config.get('services', 'db_management_api', 'enabled', default=True):
            self.log_info("DB Management API is disabled in config")
            return True
        
        port = self.config.get('services', 'db_management_api', 'port', default=8013)
        timeout = self.config.get('services', 'db_management_api', 'startup_timeout', default=10)
        max_retries = 2
        
        self.log_info(f"Starting DB Management API on port {port}...")
        
        # Check if already running
        if not self.check_port(port):
            self.log_warn(f"Port {port} is already in use, DB API may already be running")
            return True
        
        frontend_dir = self.script_dir / self.config.get('services', 'db_management_api', 'directory', default='frontend')
        script = self.config.get('services', 'db_management_api', 'script', default='scripts/db-management-api.cjs')
        script_path = frontend_dir / script
        
        # Verify script exists
        if not script_path.exists():
            self.log_error(f"DB API script not found: {script_path}")
            # Try to find alternative script names
            alternative_names = ['scripts/db_management_api.cjs', 'scripts/db-management-api.js', 'db-management-api.cjs']
            for alt in alternative_names:
                alt_path = frontend_dir / alt
                if alt_path.exists():
                    self.log_info(f"Found alternative script: {alt}")
                    script = alt
                    script_path = alt_path
                    break
            else:
                self.log_error("Could not find DB API script. Database Management will not be available.")
                return True  # Don't fail startup, just warn
        
        for attempt in range(max_retries):
            if attempt > 0:
                self.log_info(f"Retrying DB API startup (attempt {attempt + 1}/{max_retries})...")
                time.sleep(2)
            
            try:
                # Clear old log file
                log_file = Path('db-api.log')
                if log_file.exists():
                    log_file.unlink()
                
                proc = subprocess.Popen(
                    ['node', str(script)],
                    cwd=frontend_dir,
                    stdout=open('db-api.log', 'w'),
                    stderr=subprocess.STDOUT
                )
                self.processes['db_api'] = proc
                self.log_info(f"DB API PID: {proc.pid}")
                
                # Wait for startup
                started = False
                for i in range(timeout):
                    if proc.poll() is not None:
                        self.log_error(f"DB API process exited unexpectedly (code: {proc.poll()})!")
                        # Show log content for debugging
                        if log_file.exists():
                            log_content = log_file.read_text()[-500:]  # Last 500 chars
                            self.log_error(f"Log output: {log_content}")
                        break
                    try:
                        response = requests.get(f"http://localhost:{port}/health", timeout=1)
                        if response.status_code == 200:
                            self.log_success(f"DB Management API is running at http://localhost:{port}")
                            started = True
                            return True
                    except:
                        pass
                    time.sleep(1)
                    print(".", end='', flush=True)
                
                if started:
                    return True
                    
                print()
                # If we get here, the process didn't exit but also didn't respond to health check
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=3)
                
            except Exception as e:
                self.log_error(f"Failed to start DB API: {e}")
        
        self.log_warn(f"DB API failed to start after {max_retries} attempts. Database Management will not be available.")
        return True  # Don't fail startup, just warn
    
    def check_database_health(self) -> bool:
        """Check database health"""
        port = self.config.get('services', 'backend', 'port', default=8002)
        
        self.log_info("Checking database health...")
        
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                entities = data.get('entities_count', 0)
                relationships = data.get('relationships_count', 0)
                chunks = data.get('chunks_count', 0)
                documents = data.get('documents_count', 0)
                
                print(f"\n{Colors.CYAN}Database Statistics:{Colors.NC}")
                print(f"  Entities:      {entities}")
                print(f"  Relationships: {relationships}")
                print(f"  Chunks:        {chunks}")
                print(f"  Documents:     {documents}")
                
                # Check thresholds
                min_entities = self.config.get('database_health', 'min_entities', default=1000)
                min_relationships = self.config.get('database_health', 'min_relationships', default=1000)
                min_chunks = self.config.get('database_health', 'min_chunks', default=1000)
                min_documents = self.config.get('database_health', 'min_documents', default=10)
                
                healthy = True
                if entities < min_entities:
                    self.log_warn(f"Entity count below threshold ({min_entities})")
                    healthy = False
                if relationships < min_relationships:
                    self.log_warn(f"Relationship count below threshold ({min_relationships})")
                    healthy = False
                if chunks < min_chunks:
                    self.log_warn(f"Chunk count below threshold ({min_chunks})")
                    healthy = False
                if documents < min_documents:
                    self.log_warn(f"Document count below threshold ({min_documents})")
                    healthy = False
                
                if healthy:
                    self.log_success("Database has sizable datasets and is ready")
                else:
                    self.log_warn("Database has limited data")
                
                return True
        except Exception as e:
            self.log_error(f"Failed to check database health: {e}")
            return False
    
    def print_summary(self):
        """Print startup summary"""
        print(f"\n{Colors.GREEN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║          KG RAG System v2.0-beta - Running                     ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.NC}")
        
        backend_port = self.config.get('services', 'backend', 'port', default=8002)
        frontend_port = self.config.get('services', 'frontend', 'port', default=8081)
        db_api_port = self.config.get('services', 'db_management_api', 'port', default=8013)
        ollama_port = self.config.get('ollama', 'port', default=11434)
        
        print(f"{Colors.GREEN}Services:{Colors.NC}")
        print(f"  🌐 Frontend WebUI:  http://localhost:{frontend_port}")
        print(f"  ⚙️  Backend API:     http://localhost:{backend_port}")
        print(f"  📊 DB Management:   http://localhost:{db_api_port}")
        print(f"  🤖 Ollama:          http://localhost:{ollama_port}")
        print()
        print(f"{Colors.CYAN}Logs:{Colors.NC}")
        print(f"  Backend:  backend.log")
        print(f"  Frontend: frontend.log")
        print(f"  DB API:   db-api.log")
        print()
        print(f"{Colors.YELLOW}Press Ctrl+C to stop all services{Colors.NC}\n")
    
    def stop_all(self):
        """Stop all services"""
        for name, proc in self.processes.items():
            if proc.poll() is None:  # Process is still running
                self.log_info(f"Stopping {name} (PID: {proc.pid})...")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    self.log_success(f"{name} stopped")
                except:
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                    except:
                        pass
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}KG RAG system shut down.{Colors.NC}\n")
    
    def monitor(self):
        """Monitor running services with auto-restart for DB API"""
        self.log_info("Monitoring services... (Press Ctrl+C to stop)")
        
        backend_port = self.config.get('services', 'backend', 'port', default=8002)
        db_api_port = self.config.get('services', 'db_management_api', 'port', default=8013)
        db_api_check_interval = 30  # Check DB API every 30 seconds
        db_api_last_check = 0
        
        while self.running:
            # Check if processes are still running
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    self.log_error(f"{name} has stopped unexpectedly!")
                    return
            
            # Periodic health check for backend
            try:
                requests.get(f"http://localhost:{backend_port}/health", timeout=2)
            except:
                self.log_warn("Backend health check failed")
            
            # Check and auto-restart DB API if needed (every 30 seconds)
            current_time = time.time()
            if current_time - db_api_last_check >= db_api_check_interval:
                db_api_last_check = current_time
                try:
                    response = requests.get(f"http://localhost:{db_api_port}/health", timeout=2)
                    if response.status_code != 200:
                        self.log_warn("DB API health check failed, attempting restart...")
                        self._restart_db_api()
                except:
                    # DB API not responding, try to restart
                    self.log_warn("DB API not responding, attempting restart...")
                    self._restart_db_api()
            
            time.sleep(5)
    
    def _restart_db_api(self):
        """Restart the database management API"""
        port = self.config.get('services', 'db_management_api', 'port', default=8013)
        timeout = self.config.get('services', 'db_management_api', 'startup_timeout', default=10)
        
        # Stop existing process if any
        if 'db_api' in self.processes:
            proc = self.processes['db_api']
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except:
                    try:
                        proc.kill()
                        proc.wait(timeout=1)
                    except:
                        pass
        
        # Check if port is free now
        if not self.check_port(port):
            self.log_warn(f"Port {port} still in use, cannot restart DB API")
            return
        
        frontend_dir = self.script_dir / self.config.get('services', 'db_management_api', 'directory', default='frontend')
        script = self.config.get('services', 'db_management_api', 'script', default='scripts/db-management-api.cjs')
        
        try:
            proc = subprocess.Popen(
                ['node', str(script)],
                cwd=frontend_dir,
                stdout=open('db-api.log', 'a'),
                stderr=subprocess.STDOUT
            )
            self.processes['db_api'] = proc
            self.log_info(f"DB API restarted (PID: {proc.pid})")
            
            # Wait for startup
            for i in range(timeout):
                if proc.poll() is not None:
                    self.log_error("DB API restart failed - process exited")
                    return
                try:
                    response = requests.get(f"http://localhost:{port}/health", timeout=1)
                    if response.status_code == 200:
                        self.log_success(f"DB API is back online at http://localhost:{port}")
                        return
                except:
                    pass
                time.sleep(1)
            
            self.log_warn("DB API restart timeout - may not be fully ready")
            
        except Exception as e:
            self.log_error(f"Failed to restart DB API: {e}")
    
    def run(self):
        """Main run loop"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║          KG RAG System v2.0-beta - Startup Script              ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.NC}\n")
        
        # Check Ollama
        if not self.check_ollama():
            return False
        
        # Start Backend
        if not self.start_backend():
            return False
        
        # Check database health
        self.check_database_health()
        
        # Start DB API
        self.start_db_api()
        
        # Start Frontend
        if not self.start_frontend():
            return False
        
        # Print summary
        self.print_summary()
        
        # Monitor services
        self.monitor()
        
        return True


def main():
    parser = argparse.ArgumentParser(description='KG RAG System Startup')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--skip-ollama', action='store_true', help='Skip Ollama check')
    parser.add_argument('--backend-only', action='store_true', help='Start only backend')
    parser.add_argument('--frontend-only', action='store_true', help='Start only frontend')
    parser.add_argument('--fresh', '-f', action='store_true', help='Fresh install: clean and reinstall npm dependencies')
    args = parser.parse_args()
    
    # Load configuration
    config = KGRAGConfig(args.config)
    
    # Create service manager
    manager = ServiceManager(config)
    
    # Handle fresh install flag
    if args.fresh:
        frontend_dir = manager.script_dir / config.get('services', 'frontend', 'directory', default='frontend')
        if not manager._install_dependencies(frontend_dir, clean=True):
            sys.exit(1)
    
    try:
        success = manager.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.BLUE}Shutting down...{Colors.NC}")
        manager.stop_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
