#!/usr/bin/env python3
"""
KG RAG Configuration Loader
Loads and validates the kgrag_config.yaml file
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class KGRAGConfig:
    """Configuration manager for KG RAG system"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.script_dir = Path(__file__).parent.absolute()
        self.config_path = Path(config_path) if config_path else self.script_dir / "kgrag_config.yaml"
        self.config = self._load_config()
        self._apply_env_overrides()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            print(f"⚠️  Config file not found: {self.config_path}")
            print("Using default configuration")
            return self._default_config()
            
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✓ Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            print(f"⚠️  Error loading config: {e}")
            print("Using default configuration")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'services': {
                'backend': {'enabled': True, 'port': 8002, 'host': '127.0.0.1'},
                'frontend': {'enabled': True, 'port': 8081, 'host': True},
                'db_management_api': {'enabled': True, 'port': 8013}
            },
            'ollama': {'enabled': True, 'host': 'http://localhost', 'port': 11434},
            'logging': {'level': 'INFO'}
        }
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        env_mappings = {
            'KGRAG_BACKEND_PORT': ['services', 'backend', 'port'],
            'KGRAG_FRONTEND_PORT': ['services', 'frontend', 'port'],
            'KGRAG_DB_API_PORT': ['services', 'db_management_api', 'port'],
            'KGRAG_OLLAMA_HOST': ['ollama', 'host'],
            'KGRAG_OLLAMA_PORT': ['ollama', 'port'],
            'KGRAG_LOG_LEVEL': ['logging', 'level'],
        }
        
        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                # Convert port numbers to int
                if 'port' in path:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                # Convert boolean strings
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                    
                self._set_nested_value(self.config, path, value)
                print(f"✓ Override from {env_var}")
    
    def _set_nested_value(self, config: Dict, path: list, value: Any):
        """Set a nested dictionary value"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, *path, default=None):
        """Get a configuration value by path"""
        current = self.config
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    # Convenience properties
    @property
    def backend_port(self) -> int:
        return self.get('services', 'backend', 'port', default=8002)
    
    @property
    def frontend_port(self) -> int:
        return self.get('services', 'frontend', 'port', default=8081)
    
    @property
    def db_api_port(self) -> int:
        return self.get('services', 'db_management_api', 'port', default=8013)
    
    @property
    def ollama_url(self) -> str:
        host = self.get('ollama', 'host', default='http://localhost')
        port = self.get('ollama', 'port', default=11434)
        return f"{host}:{port}"
    
    @property
    def log_level(self) -> str:
        return self.get('logging', 'level', default='INFO')
    
    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "="*60)
        print("KG RAG Configuration Summary")
        print("="*60)
        print(f"Backend Port:      {self.backend_port}")
        print(f"Frontend Port:     {self.frontend_port}")
        print(f"DB API Port:       {self.db_api_port}")
        print(f"Ollama URL:        {self.ollama_url}")
        print(f"Log Level:         {self.log_level}")
        print("="*60 + "\n")


# Singleton instance
_config_instance = None

def get_config(config_path: Optional[str] = None) -> KGRAGConfig:
    """Get or create configuration singleton"""
    global _config_instance
    if _config_instance is None:
        _config_instance = KGRAGConfig(config_path)
    return _config_instance


if __name__ == "__main__":
    # Test loading configuration
    config = get_config()
    config.print_summary()
