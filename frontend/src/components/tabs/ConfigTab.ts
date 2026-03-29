/**
 * Configuration Tab Component
 */

import { testConnection as testApiConnection, clearDatabase as clearApiDatabase } from '@/api';
import { updateStats } from '@/components/StatsCard';
import { getElement, setVisible, setHTML } from '@/utils/dom';
import { cancelActiveQuery } from '@/stores/appStore';

// LLM Provider Configuration Types
type LLMProvider = 'deepseek' | 'minimax' | 'auto';

interface LLMFunctionConfig {
  primary: LLMProvider;
  fallback: LLMProvider | null;
}

interface LLMConfig {
  entityExtraction: LLMFunctionConfig;
  responseGeneration: LLMFunctionConfig;
  responseGenerationWithFile: LLMFunctionConfig;
  llmKnowledgeFallback: LLMFunctionConfig;
}

// Default configuration
const DEFAULT_LLM_CONFIG: LLMConfig = {
  entityExtraction: { primary: 'deepseek', fallback: 'minimax' },
  responseGeneration: { primary: 'deepseek', fallback: 'minimax' },
  responseGenerationWithFile: { primary: 'deepseek', fallback: 'minimax' },
  llmKnowledgeFallback: { primary: 'deepseek', fallback: null }
};

// Storage key
const LLM_CONFIG_KEY = 'kg_rag_llm_config';

/**
 * Get stored LLM configuration
 */
export function getLLMConfig(): LLMConfig {
  try {
    const stored = localStorage.getItem(LLM_CONFIG_KEY);
    if (stored) {
      return { ...DEFAULT_LLM_CONFIG, ...JSON.parse(stored) };
    }
  } catch {
    // Ignore parse errors
  }
  return { ...DEFAULT_LLM_CONFIG };
}

/**
 * Save LLM configuration
 */
function saveLLMConfig(config: LLMConfig): void {
  localStorage.setItem(LLM_CONFIG_KEY, JSON.stringify(config));
}

/**
 * Initialize config tab
 */
export function initConfigTab(): void {
  getElement('testConnectionBtn')?.addEventListener('click', handleTestConnection);
  getElement('refreshConnectionBtn')?.addEventListener('click', handleRefreshConnection);
  getElement('clearDatabaseBtn')?.addEventListener('click', handleClearDatabase);
  getElement('showSystemInfoBtn')?.addEventListener('click', handleShowSystemInfo);
  
  // Initialize LLM provider settings
  initLLMProviderSettings();
}

/**
 * Handle test connection
 */
async function handleTestConnection(): Promise<void> {
  const statusEl = getElement('configStatus');
  
  if (statusEl) {
    statusEl.textContent = 'Testing...';
  }
  
  try {
    const data = await testApiConnection();
    
    // Format connection info
    const connectionInfo = `
      <div class="success">✅ Connected!</div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--text-secondary);">
        <div>Entities: ${data.entities_count?.toLocaleString() || 'N/A'}</div>
        <div>Relationships: ${data.relationships_count?.toLocaleString() || 'N/A'}</div>
        <div>Chunks: ${data.chunks_count?.toLocaleString() || 'N/A'}</div>
        <div>Documents: ${data.documents_count?.toLocaleString() || 'N/A'}</div>
      </div>
    `;
    
    setHTML('configStatus', connectionInfo);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    setHTML('configStatus', `<span class="error">❌ Connection failed: ${message}</span>`);
  }
}

/**
 * Handle show system information
 */
function handleShowSystemInfo(): void {
  const systemInfoEl = getElement('systemInfoDisplay');
  if (!systemInfoEl) return;
  
  // System configuration
  const systemInfo = {
    'Frontend': {
      'Port': '8081',
      'URL': 'http://localhost:8081'
    },
    'Backend API': {
      'Port': '8002',
      'URL': 'http://localhost:8002'
    },
    'KG RAG Process Endpoints': {
      'pgvector API': 'http://localhost:8002',
      'Database': 'PostgreSQL with pgvector extension',
      'Connection Pool': 'PgBouncer (localhost:5432)'
    },
    'Embedding Models': {
      'Embeddings (File Upload)': 'Ollama nomic-embed-text (768d)',
      'Embeddings (Query)': 'Ollama nomic-embed-text (768d)',
      'Ollama Host': 'http://127.0.0.1:11434'
    },
    'LLM Providers': {
      'DeepSeek API': 'https://api.deepseek.com',
      'MiniMax API': 'https://api.minimax.chat/v1'
    }
  };
  
  // Format as HTML
  let html = '<h4 style="margin-top: 0; color: var(--accent-primary);">System Configuration</h4>';
  
  for (const [category, items] of Object.entries(systemInfo)) {
    html += `<div style="margin-bottom: 15px;">`;
    html += `<strong style="color: var(--text-primary); display: block; margin-bottom: 5px;">${category}</strong>`;
    html += `<div style="padding-left: 15px; font-size: 13px;">`;
    for (const [key, value] of Object.entries(items)) {
      html += `<div style="margin-bottom: 3px;"><span style="color: var(--text-secondary);">${key}:</span> <span style="color: var(--text-primary);">${value}</span></div>`;
    }
    html += `</div></div>`;
  }
  
  systemInfoEl.innerHTML = html;
  setVisible('systemInfoDisplay', true);
}

/**
 * Handle refresh connection
 */
function handleRefreshConnection(): void {
  // Cancel any active requests
  cancelActiveQuery();
  
  // Reset UI
  const runBtn = getElement<HTMLButtonElement>('runQueryBtn');
  if (runBtn) {
    runBtn.disabled = false;
    runBtn.textContent = '🔍 Ask Question';
  }
  
  setHTML('configStatus', '<span class="success">✅ Connection state refreshed.</span>');
}

/**
 * Handle clear database
 */
async function handleClearDatabase(): Promise<void> {
  const statusEl = getElement('clearStatus');
  
  if (!confirm('Are you sure you want to clear ALL data? This cannot be undone!')) {
    return;
  }
  
  statusEl!.textContent = 'Clearing database...';
  
  try {
    await clearApiDatabase();
    await updateStats();
    setHTML('clearStatus', '<span class="success">✅ Database cleared!</span>');
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    setHTML('clearStatus', `<span class="error">❌ Error: ${message}</span>`);
  }
}

/**
 * Initialize LLM Provider Settings
 */
function initLLMProviderSettings(): void {
  const config = getLLMConfig();
  
  // Set initial values
  setSelectValue('llmEntityExtraction', config.entityExtraction.primary);
  setSelectValue('llmEntityExtractionFallback', config.entityExtraction.fallback || 'none');
  setSelectValue('llmResponseGen', config.responseGeneration.primary);
  setSelectValue('llmResponseGenFallback', config.responseGeneration.fallback || 'none');
  setSelectValue('llmResponseGenFile', config.responseGenerationWithFile.primary);
  setSelectValue('llmResponseGenFileFallback', config.responseGenerationWithFile.fallback || 'none');
  setSelectValue('llmKnowledgeFallback', config.llmKnowledgeFallback.primary);
  
  // Add event listeners
  getElement('saveLLMConfigBtn')?.addEventListener('click', handleSaveLLMConfig);
  getElement('resetLLMConfigBtn')?.addEventListener('click', handleResetLLMConfig);
}

/**
 * Set select element value
 */
function setSelectValue(id: string, value: string | null): void {
  const select = getElement<HTMLSelectElement>(id);
  if (select && value) {
    select.value = value;
  }
}

/**
 * Handle save LLM configuration
 */
function handleSaveLLMConfig(): void {
  const config: LLMConfig = {
    entityExtraction: {
      primary: (getElement<HTMLSelectElement>('llmEntityExtraction')?.value as LLMProvider) || 'deepseek',
      fallback: getElement<HTMLSelectElement>('llmEntityExtractionFallback')?.value as LLMProvider || null
    },
    responseGeneration: {
      primary: (getElement<HTMLSelectElement>('llmResponseGen')?.value as LLMProvider) || 'deepseek',
      fallback: getElement<HTMLSelectElement>('llmResponseGenFallback')?.value as LLMProvider || null
    },
    responseGenerationWithFile: {
      primary: (getElement<HTMLSelectElement>('llmResponseGenFile')?.value as LLMProvider) || 'deepseek',
      fallback: getElement<HTMLSelectElement>('llmResponseGenFileFallback')?.value as LLMProvider || null
    },
    llmKnowledgeFallback: {
      primary: (getElement<HTMLSelectElement>('llmKnowledgeFallback')?.value as LLMProvider) || 'deepseek',
      fallback: null
    }
  };
  
  // Convert 'none' to null for fallbacks
  if (config.entityExtraction.fallback === 'none') config.entityExtraction.fallback = null;
  if (config.responseGeneration.fallback === 'none') config.responseGeneration.fallback = null;
  if (config.responseGenerationWithFile.fallback === 'none') config.responseGenerationWithFile.fallback = null;
  
  saveLLMConfig(config);
  
  const statusEl = getElement('llmConfigStatus');
  if (statusEl) {
    statusEl.innerHTML = '<span class="success">✅ LLM configuration saved!</span>';
    setTimeout(() => {
      statusEl.innerHTML = '';
    }, 3000);
  }
}

/**
 * Handle reset LLM configuration
 */
function handleResetLLMConfig(): void {
  saveLLMConfig(DEFAULT_LLM_CONFIG);
  initLLMProviderSettings();
  
  const statusEl = getElement('llmConfigStatus');
  if (statusEl) {
    statusEl.innerHTML = '<span class="success">✅ LLM configuration reset to defaults!</span>';
    setTimeout(() => {
      statusEl.innerHTML = '';
    }, 3000);
  }
}

/**
 * Get tab HTML
 */
export function getConfigTabHTML(): string {
  return `
    <div id="config" class="tab-content card" role="tabpanel" aria-labelledby="tab-config">
      <h2>⚙️ Configuration</h2>
      <p><strong>API URL:</strong> <span id="apiUrlDisplay">http://localhost:8002</span></p>
      
      <button id="testConnectionBtn" class="btn" aria-label="Test API connection">🔍 Test Connection</button>
      <button id="refreshConnectionBtn" class="btn" aria-label="Refresh connection state">🔄 Refresh Connection</button>
      <div id="configStatus" role="status" aria-live="polite"></div>
      
      <h3 style="margin-top: 30px;">🤖 LLM Provider Configuration</h3>
      <div class="llm-config-section" style="background: var(--bg-secondary); padding: 20px; border-radius: 8px; margin-top: 15px;">
        <p style="margin-bottom: 20px; color: var(--text-secondary);">
          Configure which LLM service providers to use for different functions. 
          Changes are saved locally and will be used for future queries.
        </p>
        
        <div class="llm-config-grid" style="display: grid; gap: 20px;">
          
          <!-- Entity Extraction -->
          <div class="llm-config-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; align-items: center; padding: 15px; background: var(--bg-tertiary); border-radius: 6px;">
            <div>
              <strong>Entity Extraction</strong>
              <div style="font-size: 12px; color: var(--text-secondary);">Extract entities from documents</div>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Primary</label>
              <select id="llmEntityExtraction" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="deepseek">DeepSeek (deepseek-chat)</option>
                <option value="minimax">MiniMax (M2.5)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Fallback</label>
              <select id="llmEntityExtractionFallback" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="none">— None —</option>
                <option value="deepseek">DeepSeek</option>
                <option value="minimax">MiniMax</option>
              </select>
            </div>
          </div>
          
          <!-- Response Generation (Query) -->
          <div class="llm-config-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; align-items: center; padding: 15px; background: var(--bg-tertiary); border-radius: 6px;">
            <div>
              <strong>Response Generation (Query)</strong>
              <div style="font-size: 12px; color: var(--text-secondary);">Generate answers from database</div>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Primary</label>
              <select id="llmResponseGen" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="deepseek">DeepSeek (deepseek-chat)</option>
                <option value="minimax">MiniMax (M2.1)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Fallback</label>
              <select id="llmResponseGenFallback" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="none">— None —</option>
                <option value="deepseek">DeepSeek</option>
                <option value="minimax">MiniMax</option>
              </select>
            </div>
          </div>
          
          <!-- Response Generation (Query + File) -->
          <div class="llm-config-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; align-items: center; padding: 15px; background: var(--bg-tertiary); border-radius: 6px;">
            <div>
              <strong>Response Generation (Query + File)</strong>
              <div style="font-size: 12px; color: var(--text-secondary);">Generate answers with uploaded files</div>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Primary</label>
              <select id="llmResponseGenFile" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="deepseek">DeepSeek (deepseek-chat)</option>
                <option value="minimax">MiniMax (M2.1)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Fallback</label>
              <select id="llmResponseGenFileFallback" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="none">— None —</option>
                <option value="deepseek">DeepSeek</option>
                <option value="minimax">MiniMax</option>
              </select>
            </div>
          </div>
          
          <!-- LLM Knowledge Fallback -->
          <div class="llm-config-row" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; align-items: center; padding: 15px; background: var(--bg-tertiary); border-radius: 6px;">
            <div>
              <strong>LLM Knowledge Fallback</strong>
              <div style="font-size: 12px; color: var(--text-secondary);">When no relevant documents found</div>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Primary</label>
              <select id="llmKnowledgeFallback" class="select-input" style="width: 100%; margin-top: 4px;">
                <option value="deepseek">DeepSeek (deepseek-chat)</option>
                <option value="minimax">MiniMax (M2.1)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 12px; color: var(--text-secondary);">Fallback</label>
              <div style="padding: 8px; color: var(--text-secondary); font-size: 13px;">— Not Applicable —</div>
            </div>
          </div>
          
        </div>
        
        <div style="margin-top: 20px; display: flex; gap: 10px;">
          <button id="saveLLMConfigBtn" class="btn" aria-label="Save LLM configuration">💾 Save Configuration</button>
          <button id="resetLLMConfigBtn" class="btn secondary" aria-label="Reset to defaults" style="background: var(--bg-tertiary);">🔄 Reset to Defaults</button>
        </div>
        <div id="llmConfigStatus" role="status" aria-live="polite" style="margin-top: 10px;"></div>
      </div>
      
      <h3 style="margin-top: 30px;">📊 System Information</h3>
      <button id="showSystemInfoBtn" class="btn" aria-label="Show system information">ℹ️ System Information</button>
      <div id="systemInfoDisplay" class="result-box" style="display: none; margin-top: 15px;" aria-label="System information"></div>
      
      <h3 style="margin-top: 30px;">🗑️ Database Management</h3>
      <button id="clearDatabaseBtn" class="btn danger" aria-label="Clear all database data">🗑️ Clear All Data</button>
      <div id="clearStatus" role="status" aria-live="polite"></div>
    </div>
  `;
}
