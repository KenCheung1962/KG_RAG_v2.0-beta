(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))o(s);new MutationObserver(s=>{for(const i of s)if(i.type==="childList")for(const a of i.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&o(a)}).observe(document,{childList:!0,subtree:!0});function n(s){const i={};return s.integrity&&(i.integrity=s.integrity),s.referrerPolicy&&(i.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?i.credentials="include":s.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function o(s){if(s.ep)return;s.ep=!0;const i=n(s);fetch(s.href,i)}})();const X={},K=(X==null?void 0:X.VITE_API_URL)||"http://localhost:8002",Q=(X==null?void 0:X.VITE_API_KEY)||"static-internal-key",Et=1e4;function l(e){return document.getElementById(e)}function j(e,t){const n=l(e);n&&(n.textContent=t)}function ne(e,t){const n=l(e);n&&(n.innerHTML=t)}function V(e,t){const n=l(e);n&&(n.style.display=t?"block":"none")}function M(e,t){const n=l(e);n&&(n.disabled=t)}function Ft(e,t){var n,o;document.querySelectorAll(".tab").forEach(s=>s.classList.remove("active")),document.querySelectorAll(".tab-content").forEach(s=>s.classList.remove("active")),(n=document.querySelector(`[data-tab="${e}"]`))==null||n.classList.add("active"),(o=l(e))==null||o.classList.add("active")}const E={kgStats:null,docStats:null,lastStatsUpdate:null,selectedFiles:[],folderFiles:[],selectedQueryFiles:[],isUploading:!1,activeQueryController:null,isQuerying:!1,statsInterval:null},Xe=new Set;function q(){Xe.forEach(e=>e())}const de=()=>[...E.selectedFiles],Lt=()=>[...E.folderFiles],ke=()=>[...E.selectedQueryFiles],Ct=()=>E.isQuerying;function Tt(e){E.kgStats=e,E.lastStatsUpdate=Date.now(),q()}function At(e){E.docStats=e,q()}function Ye(e){E.selectedFiles.some(n=>n.name===e.name&&n.size===e.size)||(E.selectedFiles.push(e),q())}function Rt(e){E.selectedFiles.splice(e,1),q()}function Ze(){E.selectedFiles=[],q()}function qt(e){E.folderFiles=[...e],q()}function Bt(e){E.selectedQueryFiles.some(n=>n.name===e.name&&n.size===e.size)||(E.selectedQueryFiles.push(e),q())}function Mt(e){E.selectedQueryFiles.splice(e,1),q()}function Qe(){E.selectedQueryFiles=[],q()}function Y(e){E.isUploading=e,q()}function He(e){E.activeQueryController=e,q()}function Ae(){E.activeQueryController&&(E.activeQueryController.abort(),E.activeQueryController=null,E.isQuerying=!1,q())}function G(e){E.isQuerying=e,q()}function It(e){E.statsInterval&&clearInterval(E.statsInterval),E.statsInterval=e}function Pt(){E.statsInterval&&(clearInterval(E.statsInterval),E.statsInterval=null),Ae()}function Dt(){Pt(),Xe.clear()}const _t=`
  .skeleton {
    background: linear-gradient(90deg, 
      rgba(255,255,255,0.05) 25%, 
      rgba(255,255,255,0.1) 50%, 
      rgba(255,255,255,0.05) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
    border-radius: var(--border-radius-sm);
  }
  
  @keyframes skeleton-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  
  .skeleton-text {
    height: 16px;
    width: 60%;
    margin: 8px 0;
  }
  
  .skeleton-text-sm {
    height: 12px;
    width: 40%;
    margin: 6px 0;
  }
  
  .skeleton-number {
    height: 32px;
    width: 50px;
    margin: 0 auto 8px;
  }
  
  .skeleton-box {
    height: 80px;
    width: 100%;
  }
  
  .skeleton-btn {
    height: 40px;
    width: 120px;
    margin-top: 15px;
  }
  
  .loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(26, 26, 46, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }
  
  .loading-spinner {
    width: 50px;
    height: 50px;
    border: 4px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .loading-message {
    color: var(--text-primary);
    margin-top: 15px;
    font-size: 16px;
  }
`;function et(){if(document.getElementById("loading-styles"))return;const e=document.createElement("style");e.id="loading-styles",e.textContent=_t,document.head.appendChild(e)}function Ut(){et();const e=l("stats-container");e&&(e.innerHTML=`
    <div class="card">
      <h2>📊 Knowledge Graph Stats</h2>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn">🔄 Refresh Stats</button>
    </div>
  `)}const zt="http://localhost:8002",Qt="http://localhost:8012",ae={entities:45887,relationships:116305,chunks:368536,documents:1982};async function Ht(){try{const e=await fetch(`${zt}/health`,{signal:AbortSignal.timeout(3e4)});if(!e.ok)return null;const t=await e.json();return{kg:{entities:t.entities_count??0,relationships:t.relationships_count??0,chunks:t.chunks_count??0},docs:{total_documents:t.documents_count??0}}}catch(e){return console.log("Port 8002 API not available:",e instanceof Error?e.message:e),null}}async function Nt(){try{const e=await fetch(`${Qt}/stats`,{signal:AbortSignal.timeout(3e4)});if(!e.ok)return null;const t=await e.json();return{kg:{entities:t.entities??0,relationships:t.relationships??0,chunks:t.chunks??0},docs:{total_documents:t.documents??0}}}catch{return console.log("Port 8012 proxy not available"),null}}async function Ot(){const e=await Ht();if(e)return console.log("✅ Stats from port 8002:",{docs:e.docs.total_documents,entities:e.kg.entities,rels:e.kg.relationships,chunks:e.kg.chunks}),{...e,source:"pgvector-api:8002"};const t=await Nt();return t?(console.log("✅ Stats from port 8012:",{docs:t.docs.total_documents,entities:t.kg.entities,rels:t.kg.relationships,chunks:t.kg.chunks}),{...t,source:"proxy:8012"}):(console.warn("⚠️ Using fallback hardcoded stats - API may be down"),{kg:{entities:ae.entities,relationships:ae.relationships,chunks:ae.chunks},docs:{total_documents:ae.documents},source:"fallback"})}function Gt(){et(),Ut();const e=l("refreshStatsBtn");e==null||e.addEventListener("click",z),z()}async function z(){try{console.log("[Stats] Fetching pgvector stats...");const{kg:e,docs:t,source:n}=await Ot();console.log(`[Stats] From ${n}:`,{docs:(t==null?void 0:t.total_documents)??0,entities:(e==null?void 0:e.entities)??0,relations:(e==null?void 0:e.relationships)??0,chunks:(e==null?void 0:e.chunks)??0}),Tt(e),At(t),jt(e,t)}catch(e){console.error("[Stats] Failed to fetch:",e),j("statDocs","❌"),j("statEntities","❌"),j("statRelations","❌"),j("statChunks","❌")}}function jt(e,t){const n=(t==null?void 0:t.total_documents)??0,o=(e==null?void 0:e.entities)??(e==null?void 0:e.total_entities)??0,s=(e==null?void 0:e.relationships)??(e==null?void 0:e.total_relations)??0,i=(e==null?void 0:e.chunks)??0;console.log("Rendering stats:",{docs:n,entities:o,relations:s,chunks:i}),j("statDocs",String(n)),j("statEntities",String(o)),j("statRelations",String(s)),j("statChunks",String(i))}let oe={percent:0,status:"",isActive:!1};function Kt(e){const t=l(e);t&&(t.innerHTML=`
    <div class="progress-container" style="display: none;">
      <div class="progress-bar">
        <div class="progress-fill" style="width: 0%"></div>
      </div>
      <div class="progress-status"></div>
    </div>
  `)}function Re(e){const t=l(e),n=t==null?void 0:t.querySelector(".progress-container");n&&(n.style.display="block",oe.isActive=!0)}function ue(e,t,n){const o=l(e),s=o==null?void 0:o.querySelector(".progress-fill"),i=o==null?void 0:o.querySelector(".progress-status");s&&(s.style.width=`${t}%`),i&&n!==void 0&&(i.innerHTML=n),oe.percent=t,n!==void 0&&(oe.status=n)}function C(e,t,n=!0){const o=n?'<span class="spinner"></span>':"";ue(e,oe.percent,`${o}<span style="color: #00d4ff;">${t}</span>`)}function Wt(){return oe.isActive}const $e={entityExtraction:{primary:"deepseek",fallback:"minimax"},responseGeneration:{primary:"deepseek",fallback:"minimax"},responseGenerationWithFile:{primary:"deepseek",fallback:"minimax"},llmKnowledgeFallback:{primary:"deepseek",fallback:null}},tt="kg_rag_llm_config";function qe(){try{const e=localStorage.getItem(tt);if(e)return{...$e,...JSON.parse(e)}}catch{}return{...$e}}function nt(e){localStorage.setItem(tt,JSON.stringify(e))}function Jt(){var e,t,n,o;(e=l("testConnectionBtn"))==null||e.addEventListener("click",Vt),(t=l("refreshConnectionBtn"))==null||t.addEventListener("click",Yt),(n=l("clearDatabaseBtn"))==null||n.addEventListener("click",Zt),(o=l("showSystemInfoBtn"))==null||o.addEventListener("click",Xt),ot()}async function Vt(){var t,n,o,s;const e=l("configStatus");e&&(e.textContent="Testing...");try{const i=await ct(),a=`
      <div class="success">✅ Connected!</div>
      <div style="margin-top: 10px; font-size: 12px; color: var(--text-secondary);">
        <div>Entities: ${((t=i.entities_count)==null?void 0:t.toLocaleString())||"N/A"}</div>
        <div>Relationships: ${((n=i.relationships_count)==null?void 0:n.toLocaleString())||"N/A"}</div>
        <div>Chunks: ${((o=i.chunks_count)==null?void 0:o.toLocaleString())||"N/A"}</div>
        <div>Documents: ${((s=i.documents_count)==null?void 0:s.toLocaleString())||"N/A"}</div>
      </div>
    `;ne("configStatus",a)}catch(i){const a=i instanceof Error?i.message:"Unknown error";ne("configStatus",`<span class="error">❌ Connection failed: ${a}</span>`)}}function Xt(){const e=l("systemInfoDisplay");if(!e)return;const t={Frontend:{Port:"8081",URL:"http://localhost:8081"},"Backend API":{Port:"8002",URL:"http://localhost:8002"},"KG RAG Process Endpoints":{"pgvector API":"http://localhost:8002",Database:"PostgreSQL with pgvector extension","Connection Pool":"PgBouncer (localhost:5432)"},"Embedding Models":{"Embeddings (File Upload)":"Ollama nomic-embed-text (768d)","Embeddings (Query)":"Ollama nomic-embed-text (768d)","Ollama Host":"http://127.0.0.1:11434"},"LLM Providers":{"DeepSeek API":"https://api.deepseek.com","MiniMax API":"https://api.minimax.chat/v1"}};let n='<h4 style="margin-top: 0; color: var(--accent-primary);">System Configuration</h4>';for(const[o,s]of Object.entries(t)){n+='<div style="margin-bottom: 15px;">',n+=`<strong style="color: var(--text-primary); display: block; margin-bottom: 5px;">${o}</strong>`,n+='<div style="padding-left: 15px; font-size: 13px;">';for(const[i,a]of Object.entries(s))n+=`<div style="margin-bottom: 3px;"><span style="color: var(--text-secondary);">${i}:</span> <span style="color: var(--text-primary);">${a}</span></div>`;n+="</div></div>"}e.innerHTML=n,V("systemInfoDisplay",!0)}function Yt(){Ae();const e=l("runQueryBtn");e&&(e.disabled=!1,e.textContent="🔍 Ask Question"),ne("configStatus",'<span class="success">✅ Connection state refreshed.</span>')}async function Zt(){const e=l("clearStatus");if(confirm("Are you sure you want to clear ALL data? This cannot be undone!")){e.textContent="Clearing database...";try{await dt(),await z(),ne("clearStatus",'<span class="success">✅ Database cleared!</span>')}catch(t){const n=t instanceof Error?t.message:"Unknown error";ne("clearStatus",`<span class="error">❌ Error: ${n}</span>`)}}}function ot(){var t,n;const e=qe();W("llmEntityExtraction",e.entityExtraction.primary),W("llmEntityExtractionFallback",e.entityExtraction.fallback||"none"),W("llmResponseGen",e.responseGeneration.primary),W("llmResponseGenFallback",e.responseGeneration.fallback||"none"),W("llmResponseGenFile",e.responseGenerationWithFile.primary),W("llmResponseGenFileFallback",e.responseGenerationWithFile.fallback||"none"),W("llmKnowledgeFallback",e.llmKnowledgeFallback.primary),(t=l("saveLLMConfigBtn"))==null||t.addEventListener("click",en),(n=l("resetLLMConfigBtn"))==null||n.addEventListener("click",tn)}function W(e,t){const n=l(e);n&&t&&(n.value=t)}function en(){var n,o,s,i,a,r,d;const e={entityExtraction:{primary:((n=l("llmEntityExtraction"))==null?void 0:n.value)||"deepseek",fallback:((o=l("llmEntityExtractionFallback"))==null?void 0:o.value)||null},responseGeneration:{primary:((s=l("llmResponseGen"))==null?void 0:s.value)||"deepseek",fallback:((i=l("llmResponseGenFallback"))==null?void 0:i.value)||null},responseGenerationWithFile:{primary:((a=l("llmResponseGenFile"))==null?void 0:a.value)||"deepseek",fallback:((r=l("llmResponseGenFileFallback"))==null?void 0:r.value)||null},llmKnowledgeFallback:{primary:((d=l("llmKnowledgeFallback"))==null?void 0:d.value)||"deepseek",fallback:null}};e.entityExtraction.fallback==="none"&&(e.entityExtraction.fallback=null),e.responseGeneration.fallback==="none"&&(e.responseGeneration.fallback=null),e.responseGenerationWithFile.fallback==="none"&&(e.responseGenerationWithFile.fallback=null),nt(e);const t=l("llmConfigStatus");t&&(t.innerHTML='<span class="success">✅ LLM configuration saved!</span>',setTimeout(()=>{t.innerHTML=""},3e3))}function tn(){nt($e),ot();const e=l("llmConfigStatus");e&&(e.innerHTML='<span class="success">✅ LLM configuration reset to defaults!</span>',setTimeout(()=>{e.innerHTML=""},3e3))}function nn(){return`
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
  `}async function Be(){try{return(await fetch(`${K}/health`,{method:"GET",headers:{"X-API-Key":Q},signal:AbortSignal.timeout(5e3)})).ok}catch{return!1}}function on(e){return new Promise(t=>setTimeout(t,e))}async function H(e,t={},n=6e5,o=3){const s=new AbortController,i=setTimeout(()=>s.abort(),n);try{const a=await fetch(e,{...t,signal:s.signal});return clearTimeout(i),a}catch(a){if(clearTimeout(i),a instanceof Error&&a.name==="AbortError"){const r=new Error(`Request timeout after ${n/1e3}s`);throw r.name="TimeoutError",r}if(o>0&&a instanceof TypeError)return console.log(`Network error, retrying... (${o} attempts left)`),await on(1e3*(4-o)),H(e,t,n,o-1);throw a}}function st(e){const t=e.includes("?")?"&":"?";return`${K}${e}${t}_=${Date.now()}`}async function Me(e=1e3){const t=await H(`${K}/api/v1/documents?limit=${e}`,{headers:{"X-API-Key":Q}});if(!t.ok)throw new Error(`Failed to fetch documents: ${t.status}`);return t.json()}function sn(e){return new Promise((t,n)=>{const o=new FileReader;o.onload=()=>{const i=o.result.split(",")[1];t(i)},o.onerror=()=>{n(new Error(`Failed to read file: ${e.name}`))},o.readAsDataURL(e)})}async function fe(e){const t=await sn(e),n=e.type||"application/octet-stream",o=n.startsWith("text/")||e.name.match(/\.(txt|md|csv|json|html|xml|js|ts|py|css)$/i),s=await H(`${K}/api/v1/documents/upload/json`,{method:"POST",headers:{"Content-Type":"application/json","X-API-Key":Q},body:JSON.stringify({content:t,id:e.name,content_type:o?"text/plain":n})},12e4);if(!s.ok)throw new Error(`Upload failed: ${s.status}`);return s.json()}async function it(e){try{const t=await H(`${K}/api/v1/documents/${e}/status`,{headers:{"X-API-Key":Q}},1e4);return t.ok?t.json():null}catch{return null}}const rt=`You are a knowledgeable research assistant with access to a document database.

Your task is to provide comprehensive, detailed answers based on the retrieved context. Follow these guidelines:

1. **Be thorough**: Provide detailed explanations with specific examples, data points, and relationships found in the context.

2. **Structure your answer**: Use clear headings (# for main sections, ## for subsections) and organize information logically.

3. **Synthesize information**: Don't just list facts—connect ideas, explain relationships, and provide insights that demonstrate deep understanding.

4. **Include specifics**: Cite specific entities, metrics, dates, or technical details when available in the context.

5. **Explain relevance**: Briefly explain why the information matters or how concepts relate to each other.

6. **No unnecessary disclaimers**: If the context provides relevant information, answer confidently without apologizing for "limited context."

7. **Expand on concepts**: When discussing technical topics, explain underlying principles and mechanisms, not just surface-level facts.`;async function at(e,t){const n=e.ultra_comprehensive,o=n||e.detailed||e.message.toLowerCase().includes("explain")||e.message.toLowerCase().includes("detail")||e.message.toLowerCase().includes("comprehensive"),s=qe(),i={provider:s.responseGeneration.primary,fallback_provider:s.responseGeneration.fallback},a={...e,top_k:n?40:e.top_k??20,rerank:e.rerank??!0,rerank_method:e.rerank_method??"hybrid",system_prompt:e.system_prompt??rt,detailed:o,ultra_comprehensive:n,temperature:n?.4:e.temperature??.3,max_tokens:n||o?8192:4096,message:e.message,llm_config:i};let r;n?r=9e5:o?r=6e5:e.top_k&&e.top_k>=20?r=3e5:r=18e4;const d=await H(st("/api/v1/chat"),{method:"POST",headers:{"Content-Type":"application/json","X-API-Key":Q},body:JSON.stringify(a),signal:t},r);if(!d.ok)throw new Error(`Query failed: ${d.status}`);return d.json()}async function Ie(e,t){const n=e.ultra_comprehensive,o=e.detailed,s=qe(),i={provider:s.responseGenerationWithFile.primary,fallback_provider:s.responseGenerationWithFile.fallback},a={...e,top_k:e.top_k??20,system_prompt:n||o?rt:void 0,detailed:o,ultra_comprehensive:n,temperature:n?.4:.3,max_tokens:n||o?8192:4096,message:e.message,llm_config:i},r=n?9e5:o?6e5:18e4,d=await H(st("/api/v1/chat/with-doc"),{method:"POST",headers:{"Content-Type":"application/json","X-API-Key":Q},body:JSON.stringify(a),signal:t},r);if(!d.ok)throw new Error(`Query with files failed: ${d.status}`);return d.json()}async function lt(e){const t=await H(`${K}/api/v1/documents/upload/folder/json`,{method:"POST",headers:{"Content-Type":"application/json","X-API-Key":Q},body:JSON.stringify(e)},3e5);if(!t.ok)throw new Error(`Folder upload failed: ${t.status}`);return t.json()}async function ct(){const e=await H(`${K}/health`,{headers:{"X-API-Key":Q}},1e4);if(!e.ok)throw new Error(`Health check failed: ${e.status}`);return e.json()}async function dt(){const e=await H(`${K}/api/v1/clear`,{method:"DELETE",headers:{"X-API-Key":Q}},6e4);if(!e.ok)throw new Error(`Clear database failed: ${e.status}`)}const rn=Object.freeze(Object.defineProperty({__proto__:null,clearDatabase:dt,fetchDocuments:Me,getDocumentStatus:it,isBackendHealthy:Be,sendQuery:at,sendQueryWithFiles:Ie,testConnection:ct,uploadDocument:fe,uploadFolder:lt},Symbol.toStringTag,{value:"Module"}));function L(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}function an(e){return e<1024?`${e} B`:e<1024*1024?`${(e/1024).toFixed(1)} KB`:`${(e/(1024*1024)).toFixed(1)} MB`}function ln(e,t=1e3,n=5e3){return Math.min(t*Math.pow(1.5,e),n)}function me(e,t){const n=document.getElementById(t.containerId);if(!n)return;if(e.length===0){n.style.display="none";return}n.style.display="block";const o=e.map((s,i)=>`
    <div class="file-item" data-index="${i}">
      <span class="file-name">${L(s.name)}</span>
      <span class="file-size">${an(s.size)}</span>
      ${t.onRemove?`
        <button class="btn-remove" data-index="${i}" title="Remove">✕</button>
      `:""}
    </div>
  `).join("");n.innerHTML=`
    <strong>${t.emptyText||"Selected files:"}</strong>
    <div class="file-list-content">${o}</div>
  `,t.onRemove&&n.querySelectorAll(".btn-remove").forEach(s=>{s.addEventListener("click",i=>{var r;i.stopPropagation();const a=parseInt(s.dataset.index||"0",10);(r=t.onRemove)==null||r.call(t,a)})})}const ut="http://localhost:8013";async function te(e,t){try{const n=await fetch(`${ut}${e}`,{...t,headers:{"Content-Type":"application/json",...t==null?void 0:t.headers}});if(!n.ok){const o=await n.json().catch(()=>({error:`HTTP ${n.status}`}));throw new Error(o.error||`HTTP ${n.status}`)}return n.json()}catch(n){throw n instanceof Error&&n.name==="TypeError"?new Error("Database Management API not running. Start it with: npm run db:api"):n}}async function cn(){return te("/stats")}async function dn(){return(await te("/backups")).backups}async function le(){return te("/backup",{method:"POST"})}async function un(){return te("/cleanup",{method:"POST"})}async function pn(e){return te("/restore",{method:"POST",body:JSON.stringify({backupName:e})})}async function fn(e){return te("/backup",{method:"DELETE",body:JSON.stringify({backupName:e})})}async function mn(){const e=await fetch("http://localhost:8002/api/v1/upload-failures");if(!e.ok)throw new Error(`Failed to fetch upload failures: ${e.status}`);return e.json()}async function gn(){try{return(await fetch(`${ut}/health`,{method:"GET",signal:AbortSignal.timeout(2e3)})).ok}catch{return!1}}let O=null,J=[],U=!1,Z=null,Se=[],Ee=[];function hn(){wn(),bn(),yn(),vn()}async function bn(){U=await gn(),pt(),U&&(await ie(),await re(),await mt())}function pt(){const e=l("databasePanel"),t=l("dbApiWarning");e&&(e.style.opacity=U?"1":"0.5"),t&&(V("dbApiWarning",!U),U||(t.innerHTML=`
        <div class="warning-box">
          <strong>⚠️ Database Management API Not Running</strong><br>
          Start it with: <code>node scripts/db-management-api.cjs</code><br>
          Or: <code>npm run db:api</code>
        </div>
      `))}function yn(){var e,t,n,o;(e=l("btnCreateBackup"))==null||e.addEventListener("click",kn),(t=l("btnCleanupDB"))==null||t.addEventListener("click",$n),(n=l("btnRefreshDBStats"))==null||n.addEventListener("click",()=>{ie(),re()}),(o=l("btnRefreshUploadHistory"))==null||o.addEventListener("click",mt)}function vn(){Z&&clearInterval(Z),Z=window.setInterval(()=>{U&&ie()},3e4)}async function ie(){if(U)try{O=await cn(),xn()}catch(e){console.error("Failed to refresh stats:",e),U=!1,pt()}}async function re(){if(U)try{J=await dn(),ft()}catch(e){console.error("Failed to refresh backups:",e)}}function xn(){var n,o,s,i;if(!O)return;const e=`
    <div class="db-stats-grid">
      <div class="db-stat-item">
        <span class="db-stat-value">${((n=O.counts.documents)==null?void 0:n.toLocaleString())||0}</span>
        <span class="db-stat-label">Documents</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${((o=O.counts.chunks)==null?void 0:o.toLocaleString())||0}</span>
        <span class="db-stat-label">Chunks</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${((s=O.counts.entities)==null?void 0:s.toLocaleString())||0}</span>
        <span class="db-stat-label">Entities</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${((i=O.counts.relationships)==null?void 0:i.toLocaleString())||0}</span>
        <span class="db-stat-label">Relationships</span>
      </div>
    </div>
    <div class="db-size-info">
      <strong>Total Database Size:</strong> ${O.totalSizeFormatted}
      <span class="db-last-updated">Updated: ${new Date(O.timestamp).toLocaleTimeString()}</span>
    </div>
  `,t=l("dbStatsContainer");t&&(t.innerHTML=e)}function wn(){const e=l("dbBackupsContainer");e&&(e.removeEventListener("click",Ne),e.addEventListener("click",Ne))}function Ne(e){const t=e.target,n=t.closest(".btn-restore"),o=t.closest(".btn-delete");if(!n&&!o)return;const s=t.closest(".backup-item");if(!s)return;const i=s.getAttribute("data-backup-name");if(i){if(n){Sn(i);return}if(o){if(o.disabled)return;En(i,o)}}}function ft(){const e=l("dbBackupsContainer");if(!e)return;if(J.length===0){e.innerHTML='<p class="empty-text">No backups yet. Create your first backup below.</p>';return}const t=J.slice(0,5).map(n=>{var a,r;const o=new Date(n.created).toLocaleString(),s=((r=(a=n.metadata)==null?void 0:a.stats)==null?void 0:r.documents)||"?",i=s==="?"||n.size==="160 B";return`
      <div class="backup-item ${i?"backup-outdated":""}" data-backup-name="${L(n.name)}">
        <div class="backup-info">
          <div class="backup-name">${L(n.name)} ${i?'<span class="outdated-badge">outdated</span>':""}</div>
          <div class="backup-meta">
            ${o} • ${n.size} • ${s} docs
          </div>
        </div>
        <div class="backup-actions">
          <button class="btn-small btn-restore" title="Restore (metadata only)">
            ↩️ Restore
          </button>
          <button class="btn-small btn-delete" title="Delete this backup">
            🗑️ Delete
          </button>
        </div>
      </div>
    `}).join("");e.innerHTML=`
    <div class="backup-list">
      ${t}
    </div>
    ${J.length>5?`<p class="backup-more">+ ${J.length-5} more backups</p>`:""}
  `}async function kn(){const e=l("btnCreateBackup");if(!e)return;const t=e.innerHTML;e.innerHTML="⏳ Creating...",M("btnCreateBackup",!0);try{const n=await le();R(`✅ Backup created: ${n.result.backupPath}`,"success"),await re()}catch(n){R(`❌ Backup failed: ${n instanceof Error?n.message:"Unknown error"}`,"error")}finally{e.innerHTML=t,M("btnCreateBackup",!1)}}async function $n(){if(!confirm(`⚠️ WARNING: This will DELETE all data in the database!

Make sure you have created a backup first.

This action cannot be undone.

Are you sure you want to continue?`))return;const t=l("btnCleanupDB");if(!t)return;const n=t.innerHTML;t.innerHTML="⏳ Cleaning...",M("btnCleanupDB",!0);try{await un(),R("✅ Database cleaned successfully","success"),await ie(),await re(),localStorage.removeItem("lightrag_upload_tracker"),localStorage.removeItem("lightrag_uploaded_files"),R("📝 Upload tracker history cleared","info")}catch(o){R(`❌ Cleanup failed: ${o instanceof Error?o.message:"Unknown error"}`,"error")}finally{t.innerHTML=n,M("btnCleanupDB",!1)}}async function Sn(e){if(confirm(`⚠️ Restore from "${e}"?

This will OVERWRITE current database metadata.

Note: You will need to re-upload the original files to restore full content.

Continue?`))try{const n=await pn(e);R(`✅ ${n.message}`,"success"),await ie()}catch(n){R(`❌ Restore failed: ${n instanceof Error?n.message:"Unknown error"}`,"error")}}async function En(e,t){if(console.log("Delete requested for backup:",e),!confirm(`🗑️ Delete backup "${e}"?

This backup will be permanently removed.

This action cannot be undone!`))return;t&&(t.disabled=!0,t.textContent="⏳...");const o=document.querySelectorAll(".btn-delete");o.forEach(s=>{s!==t&&(s.disabled=!0)});try{console.log("Calling deleteBackup API for:",e);const s=await fn(e);console.log("Delete result:",s),R(`✅ ${s.message}`,"success"),J=J.filter(i=>i.name!==e),ft(),await re()}catch(s){console.error("Delete error:",s),R(`❌ Delete failed: ${s instanceof Error?s.message:"Unknown error"}`,"error"),o.forEach(i=>{i.disabled=!1,i===t&&(i.textContent="🗑️ Delete")})}}async function mt(){try{const e=await mn();Se=e.failures,Ee=e.successes,Fn()}catch(e){console.error("Failed to fetch upload history:",e);const t=l("uploadHistoryContainer");t&&(t.innerHTML='<p class="error-text">Failed to load upload history</p>')}}function Fn(){const e=l("uploadHistoryContainer");if(!e)return;const t=Se.length,n=Ee.length;let o="";t>0&&(o+='<div class="upload-failures-section">',o+=`<h4 class="upload-section-title error">❌ Recent Failures (${t})</h4>`,o+='<div class="upload-list">',Se.slice(-10).reverse().forEach(s=>{const i=s.error.length>60?s.error.substring(0,60)+"...":s.error;o+=`
        <div class="upload-item failure">
          <div class="upload-filename" title="${L(s.filename)}">${L(s.filename)}</div>
          <div class="upload-meta">
            <span class="upload-error">${L(i)}</span>
            <span class="upload-time">${new Date(s.timestamp).toLocaleString()}</span>
          </div>
        </div>
      `}),o+="</div></div>"),n>0&&(o+='<div class="upload-successes-section">',o+=`<h4 class="upload-section-title success">✅ Recent Successes (${n} total)</h4>`,o+='<div class="upload-list">',Ee.slice(-5).reverse().forEach(s=>{o+=`
        <div class="upload-item success">
          <div class="upload-filename" title="${L(s.filename)}">${L(s.filename)}</div>
          <div class="upload-meta">
            <span class="upload-chunks">${s.chunks} chunks</span>
            <span class="upload-time">${new Date(s.timestamp).toLocaleString()}</span>
          </div>
        </div>
      `}),o+="</div></div>"),t===0&&n===0&&(o='<p class="empty-text">No upload history available yet. Upload some files to see the history.</p>'),e.innerHTML=o}function R(e,t="info"){const n=l("dbNotification");if(!n)return;const o=t==="success"?"notification-success":t==="error"?"notification-error":"notification-info";n.innerHTML=`<div class="notification ${o}">${L(e)}</div>`,setTimeout(()=>{n.innerHTML=""},5e3)}function Ln(){return`
    <div id="databasePanel" class="database-panel card">
      <h2>🗄️ Database Management</h2>
      
      <div id="dbApiWarning"></div>
      
      <div class="db-section">
        <h3>📊 Current Statistics</h3>
        <div id="dbStatsContainer">
          <p class="loading-text">Loading stats...</p>
        </div>
      </div>
      
      <div class="db-section">
        <h3>💾 Backups</h3>
        <div id="dbBackupsContainer">
          <p class="loading-text">Loading backups...</p>
        </div>
        <div class="db-actions">
          <button id="btnCreateBackup" class="btn-primary">
            💾 Create Backup
          </button>
          <button id="btnRefreshDBStats" class="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>
      
      <div class="db-section">
        <h3>📋 Upload History</h3>
        <div id="uploadHistoryContainer">
          <p class="loading-text">Loading upload history...</p>
        </div>
        <div class="db-actions">
          <button id="btnRefreshUploadHistory" class="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>
      
      <div class="db-section db-danger-zone">
        <h3>⚠️ Danger Zone</h3>
        <p class="hint-text">
          Clean up the database to free space. <strong>Create a backup first!</strong>
        </p>
        <button id="btnCleanupDB" class="btn-danger">
          🗑️ Clean Database
        </button>
      </div>
      
      <div id="dbNotification"></div>
    </div>
  `}function Cn(){Z&&(clearInterval(Z),Z=null)}const Pe="lightrag_upload_tracker",gt="lightrag_uploaded_files";function Tn(){return`session_${Date.now()}_${Math.random().toString(36).substr(2,9)}`}function ge(){try{const e=localStorage.getItem(Pe);return e?JSON.parse(e):null}catch{return null}}function ee(e){try{localStorage.setItem(Pe,JSON.stringify(e))}catch(t){console.error("Failed to save upload session:",t)}}function ht(){localStorage.removeItem(Pe)}function An(e,t){const n={id:Tn(),folderPath:e,startedAt:Date.now(),lastUpdated:Date.now(),totalFiles:t,processedFiles:0,uploadedFileIds:[],status:"in_progress"};return ee(n),n}function Rn(e,t){const n=ge();n&&(n.uploadedFileIds.includes(e)||n.uploadedFileIds.push(e),n.processedFiles=n.uploadedFileIds.length,n.lastUpdated=Date.now(),ee(n),qn(e,t))}function he(){try{const e=localStorage.getItem(gt);return e?JSON.parse(e):[]}catch{return[]}}function qn(e,t){try{const o=he().filter(i=>i.filename!==e);o.push({filename:e,docId:t,uploadedAt:Date.now(),size:0});const s=o.slice(-1e4);localStorage.setItem(gt,JSON.stringify(s))}catch(n){console.error("Failed to save to uploaded files list:",n)}}function Bn(e){return he().some(n=>n.filename===e)}async function Mn(){const e=ge();if(!e)return{hasSession:!1};if(e.status==="completed")return ht(),{hasSession:!1};try{const t=await Me(1e4),n=new Set(t.map(i=>i.filename)),o=e.uploadedFileIds.filter(i=>n.has(i)),s=e.uploadedFileIds.filter(i=>!n.has(i));return s.length>0&&(console.warn(`${s.length} files from session not found on server`),e.uploadedFileIds=o,e.processedFiles=o.length,ee(e)),o.length>=e.totalFiles?(e.status="completed",ee(e),{hasSession:!0,session:e,message:`Previous upload completed (${o.length}/${e.totalFiles} files)`}):{hasSession:!0,session:e,message:`Found interrupted upload: ${o.length}/${e.totalFiles} files processed`}}catch{return{hasSession:!0,session:e,message:`Found previous upload session: ${e.processedFiles}/${e.totalFiles} files (server verification failed)`}}}function In(){const e=ge();e&&(e.status="completed",e.lastUpdated=Date.now(),ee(e))}function Pn(){const e=ge();e&&e.status!=="completed"&&(e.status="interrupted",e.lastUpdated=Date.now(),ee(e))}function bt(e){const t=he(),n=new Set(t.map(i=>i.filename)),o=[],s=[];for(const i of e)n.has(i.name)?s.push(i.name):o.push(i);return{newFiles:o,skippedFiles:s,count:{new:o.length,skipped:s.length}}}function Dn(){const e=he(),t=e.length>0?Math.max(...e.map(n=>n.uploadedAt)):null;return{totalUploaded:e.length,lastUpload:t}}let P=null;const yt="lightrag_auto_backup_enabled",Fe=10;function Le(){return localStorage.getItem(yt)==="true"}function Oe(e){localStorage.setItem(yt,String(e))}function _n(){var n,o,s,i,a,r,d,c,f,h,F;(n=l("btnMethodFiles"))==null||n.addEventListener("click",()=>Ge("files")),(o=l("btnMethodFolder"))==null||o.addEventListener("click",()=>Ge("folder")),(s=l("fileInput"))==null||s.addEventListener("change",Un),(i=l("clearFilesBtn"))==null||i.addEventListener("click",vt),(a=l("ingestFilesBtn"))==null||a.addEventListener("click",zn),(r=l("folderInput"))==null||r.addEventListener("change",Qn),(d=l("browseFolderBtn"))==null||d.addEventListener("click",()=>{var u;(u=l("folderInput"))==null||u.click()}),(c=l("ingestFolderBtn"))==null||c.addEventListener("click",Hn);const e=l("autoBackup"),t=l("autoBackupFiles");e==null||e.addEventListener("change",u=>{const w=u.target.checked;Oe(w),t&&(t.checked=w),console.log(`Auto-backup ${w?"enabled":"disabled"}`)}),t==null||t.addEventListener("change",u=>{const w=u.target.checked;Oe(w),e&&(e.checked=w),console.log(`Auto-backup ${w?"enabled":"disabled"}`)}),(f=l("resumeUploadBtn"))==null||f.addEventListener("click",jn),(h=l("discardSessionBtn"))==null||h.addEventListener("click",Kn),(F=l("clearUploadHistoryBtn"))==null||F.addEventListener("click",Wn),On(),wt(),hn()}function Ge(e){V("methodFiles",e==="files"),V("methodFolder",e==="folder");const t=l("btnMethodFiles"),n=l("btnMethodFolder");t==null||t.classList.toggle("active",e==="files"),t==null||t.classList.toggle("inactive",e!=="files"),t==null||t.setAttribute("aria-pressed",String(e==="files")),n==null||n.classList.toggle("active",e==="folder"),n==null||n.classList.toggle("inactive",e!=="folder"),n==null||n.setAttribute("aria-pressed",String(e==="folder"))}function Un(){var t;const e=l("fileInput");(t=e==null?void 0:e.files)!=null&&t.length&&(Array.from(e.files).forEach(n=>Ye(n)),me(de(),{containerId:"selectedFilesList",onRemove:De,emptyText:"Selected files:"}),e.value="")}function De(e){Rt(e),me(de(),{containerId:"selectedFilesList",onRemove:De,emptyText:"Selected files:"})}function vt(){Ze(),me([],{containerId:"selectedFilesList",onRemove:De}),l("fileInput").value=""}async function _e(e){const t=await Me(1e3),n=new Set(t.map(r=>r.filename)),o=new Map(t.map(r=>[r.filename,r.doc_id])),s=[],i=[];for(const r of e)n.has(r.name)?s.push(r.name):i.push(r);const a=new Map;for(const r of s){const d=o.get(r);d&&a.set(r,d)}return{duplicates:s,newFiles:i,duplicateDocIds:a}}function xt(e,t,n="files"){const o=e.slice(0,5).join(", ")+(e.length>5?"...":"");return t>0?confirm(`Found ${e.length} existing ${n}:
${o}

Click OK to upload all (overwrite duplicates), Cancel to skip duplicates.`):confirm(`All ${e.length} ${n} already exist. Click OK to overwrite all, Cancel to skip.`)}async function zn(){const e=de();if(e.length===0){alert("Please select files first");return}Y(!0),M("ingestFilesBtn",!0),Re("ingestProgress"),C("ingestProgress","Checking for existing files...");try{const{duplicates:t,newFiles:n}=await _e(e);if(t.length>0&&!xt(t,n.length,"file(s)")){if(n.length===0){C("ingestProgress","⏭️ All files already exist. Skipped.",!1),M("ingestFilesBtn",!1),Y(!1);return}Ze(),n.forEach(d=>Ye(d))}const o=de();let s=0,i=0;const a=[];for(let r=0;r<o.length;r++){const d=o[r],c=(r+1)/o.length*100;C("ingestProgress",`📄 Processing ${r+1}/${o.length}: <strong>${L(d.name)}</strong>`),ue("ingestProgress",c);try{await fe(d),s++,await z()}catch(f){console.error(`Failed to upload ${d.name}:`,f);const h=f instanceof Error?f.message:String(f),u=f instanceof Error&&(f.name==="TimeoutError"||h.includes("timeout")||h.includes("Abort"))?"Upload timeout - file too large or backend busy":h;a.push({file:d.name,error:u}),i++}}C("ingestProgress",`✅ Processed ${s} files${i>0?`, ${i} errors`:""}`,!1),i>0&&a.length>0&&Ce(a),vt(),await z()}catch(t){console.error("Ingest failed:",t),C("ingestProgress",`❌ Error: ${t instanceof Error?t.message:"Unknown error"}`,!1)}finally{M("ingestFilesBtn",!1),Y(!1)}}function Ce(e){const t=l("uploadErrorLog");if(!t)return;const n=new Map;e.forEach(({file:s,error:i})=>{const a=n.get(i)||[];a.push(s),n.set(i,a)});let o='<div class="error-log"><h4>⚠️ Error Details:</h4>';Array.from(n.entries()).slice(0,5).forEach(([s,i])=>{o+=`<div class="error-item"><strong>${i.length} files:</strong> ${L(s)}`,i.length<=3&&(o+=`<br><small>${i.map(L).join(", ")}</small>`),o+="</div>"}),n.size>5&&(o+=`<p><em>... and ${n.size-5} more error types</em></p>`),o+="</div>",t.innerHTML=o,t.style.display="block"}function Qn(){var i,a;const e=l("folderInput");if(!((i=e==null?void 0:e.files)!=null&&i.length))return;let t=Array.from(e.files);const o=((a=t[0].webkitRelativePath)==null?void 0:a.split("/")[0])||"/",s=bt(t);if(s.skippedFiles.length>0){console.log(`${s.skippedFiles.length} files already uploaded, skipping`);const r=l("duplicateNotification");r&&(r.innerHTML=`
        <div class="notification info">
          📋 <strong>${s.skippedFiles.length}</strong> files already uploaded (skipped)<br>
          <strong>${s.newFiles.length}</strong> new files to upload
        </div>
      `,r.style.display="block"),t=s.newFiles}qt(t),l("folderPath").value=o,l("folderFileCount").textContent=`${t.length} files selected`,V("folderFiles",!0)}async function Hn(){var i,a;const e=((i=l("folderPath"))==null?void 0:i.value)??"",t=((a=l("recursive"))==null?void 0:a.checked)??!0;let n=Lt();if(!e&&n.length===0){alert("Please select a folder first");return}const o=bt(n),s=o.skippedFiles.length;if(s>0&&(console.log(`📋 Pre-filtered ${s} already uploaded files`),R(`📋 ${s} files already uploaded, will be skipped`,"info")),n=o.newFiles,n.length===0){C("ingestProgress","✅ All files already uploaded! Nothing to upload.",!1);return}console.log(`📤 Starting upload of ${n.length} new files (${s} already uploaded)`),P=An(e,n.length),Y(!0),M("ingestFolderBtn",!0),Re("ingestProgress"),C("ingestProgress",`Starting upload of ${n.length} new files...`);try{if(n.length>0){const{duplicates:r,newFiles:d}=await _e(n);if(r.length>0){const c=xt(r,d.length,"file(s) in folder");if(!c&&d.length===0){C("ingestProgress","⏭️ All files already exist in database. Skipped.",!1),M("ingestFolderBtn",!1),Y(!1);return}await je(c?n:d)}else await je(n)}else{const r=await lt({folder_path:e,recursive:t});C("ingestProgress",`✅ Processed ${r.total_files} files`,!1),await z().catch(console.error)}}catch(r){console.error("Folder ingest failed:",r),C("ingestProgress",`❌ Error: ${r instanceof Error?r.message:"Unknown error"}`,!1)}finally{M("ingestFolderBtn",!1),Y(!1)}}let N=[];function ce(e){return new Promise(t=>setTimeout(t,e))}async function Nn(e=3,t=2e3){for(let n=0;n<e;n++){if(await Be())return!0;if(n<e-1){const s=t*Math.pow(2,n);console.log(`Health check failed, retrying in ${s}ms... (attempt ${n+1}/${e})`),await ce(s)}}return!1}async function je(e){let t=0,n=0,o=0,s=0,i=0;N=[];const a=5,r=300,d=2e3,c=5,f=5,h=Le(),F=Fe,u=e.filter(b=>b.size<50?(o++,!1):!0),w=Math.ceil(u.length/a);if(h&&u.length>F)try{C("ingestProgress","💾 Creating initial backup before upload...",!1),await le(),i=0,R("✅ Initial backup created","success")}catch(b){console.error("Initial backup failed:",b),R("⚠️ Initial backup failed, continuing anyway","error")}for(let b=0;b<w;b++){const m=b*a,g=u.slice(m,m+a),S=b===w-1;if(!await Nn(3,2e3)){console.error(`Backend health check failed before batch ${b+1} after retries`);const k=u.slice(m);k.forEach(p=>{N.push({file:p.name,error:"Backend unavailable - upload stopped"})}),n+=k.length,C("ingestProgress",`❌ Backend unavailable after ${t} files. ${k.length} files not processed.`,!1);break}for(let k=0;k<g.length;k++){const p=g[k],x=m+k+1,$=x/u.length*100;if(Bn(p.name)){console.log(`⏭️ Skipping already uploaded: ${p.name}`),o++,t++,C("ingestProgress",`⏭️ Skipping ${o} already uploaded... (${x}/${u.length})<br><strong>${L(p.name.substring(0,50))}${p.name.length>50?"...":""}</strong>`),ue("ingestProgress",$);continue}C("ingestProgress",`📂 Batch ${b+1}/${w}: ${k+1}/${g.length} (${x}/${u.length})<br><strong>${L(p.name.substring(0,50))}${p.name.length>50?"...":""}</strong>`),ue("ingestProgress",$);try{const v=await fe(p);t++,s=0,Rn(p.name,v.doc_id||p.name),P&&P.processedFiles++,t%f===0&&(console.log(`[Upload] Updating stats after ${t} files...`),z().catch(I=>console.error("[Upload] Stats update failed:",I))),k<g.length-1&&await ce(r)}catch(v){n++,s++;const I=v instanceof Error?v.message:String(v);if(v instanceof Error&&(v.name==="TimeoutError"||I.includes("timeout")||I.includes("Abort"))?(console.warn(`⏱️ Timeout uploading ${p.name}: ${I}`),N.push({file:p.name,error:"Upload timeout (file too large or backend busy)"})):N.push({file:p.name,error:I}),console.error(`Failed to upload ${p.name}:`,v),s>=c){if(console.warn(`Too many consecutive errors (${s}), checking backend health...`),!await Be()){const A=u.slice(x);A.forEach(D=>{N.push({file:D.name,error:"Backend crashed - upload stopped"})}),n+=A.length,C("ingestProgress",`❌ Backend crashed after ${t} files. Stopping upload.`,!1),Ce(N);return}s=0}await ce(r*2)}}if(h&&t-i>=F)try{console.log(`💾 Auto-creating backup after ${t} files...`),C("ingestProgress",`💾 Creating backup after ${t} files...`,!1),await le(),i=t,R(`✅ Backup created after ${t} files`,"success")}catch(k){console.error("Auto-backup failed:",k)}S||(C("ingestProgress",`⏳ Cooling down... (${b+1}/${w} batches complete)`,!1),await ce(d))}if(h&&t>0)try{console.log("💾 Creating final backup after upload..."),C("ingestProgress","💾 Creating final backup...",!1),await le(),R("✅ Final backup created","success")}catch(b){console.error("Final backup failed:",b)}const y=[`✅ Processed ${t} files`];o>0&&y.push(`skipped ${o} already uploaded`),n>0&&y.push(`${n} errors`),C("ingestProgress",y.join(", "),!1),n>0&&N.length>0&&Ce(N),console.log("[Upload] Final stats update..."),await z().catch(b=>console.error("[Upload] Final stats update failed:",b)),n===0&&t+o===e.length?(In(),C("ingestProgress",`✅ Upload completed! ${t} new files uploaded (${o} skipped).`,!1)):n>0&&Pn()}async function On(){const e=await Mn();e.hasSession&&e.session?(P=e.session,Gn(e.message||"Found previous upload session")):Ue()}function Gn(e){const t=l("resumeDialog"),n=l("resumeMessage");t&&n&&(n.textContent=e,t.style.display="block")}function Ue(){const e=l("resumeDialog");e&&(e.style.display="none")}async function jn(){if(!P){alert("No session to resume");return}Ue(),C("ingestProgress",`🔄 Resuming upload: ${P.processedFiles}/${P.totalFiles} files already processed`,!1),Re("ingestProgress"),alert(`Please select the same folder again to resume upload.

Already uploaded: ${P.processedFiles}/${P.totalFiles} files`)}function Kn(){confirm("Are you sure you want to discard the previous upload session?")&&(ht(),P=null,Ue(),C("ingestProgress","Previous session discarded. Ready to start new upload.",!1))}function wt(){const e=Dn(),t=l("uploadStats");if(t&&e.totalUploaded>0){const n=e.lastUpload?new Date(e.lastUpload).toLocaleDateString():"Unknown";t.innerHTML=`📊 Total files uploaded: <strong>${e.totalUploaded}</strong> (last: ${n})`,t.style.display="block"}}function Wn(){confirm(`⚠️ WARNING: This will clear ALL upload history!

Files already in the database will remain, but the system will not remember which files were uploaded.

Are you sure?`)&&(Jn(),wt(),alert("Upload history cleared."))}function Jn(){localStorage.removeItem("lightrag_upload_tracker"),localStorage.removeItem("lightrag_uploaded_files"),P=null}function Vn(){return`
    <div id="ingest" class="tab-content card active" role="tabpanel" aria-labelledby="tab-ingest">
      <h2>📥 Ingest Documents</h2>
      
      <!-- Resume Dialog -->
      <div id="resumeDialog" class="resume-dialog" style="display: none;">
        <div class="resume-content">
          <h3>🔄 Resume Previous Upload?</h3>
          <p id="resumeMessage">Found previous upload session</p>
          <div class="resume-actions">
            <button id="resumeUploadBtn" class="btn">🔄 Resume Upload</button>
            <button id="discardSessionBtn" class="btn danger">🗑️ Discard & Start New</button>
          </div>
        </div>
      </div>
      
      <!-- Upload Stats -->
      <div id="uploadStats" class="upload-stats" style="display: none;"></div>
      
      <!-- Duplicate Notification -->
      <div id="duplicateNotification" class="notification-container" style="display: none;"></div>
      
      <div class="method-toggle" role="group" aria-label="Upload method selection">
        <button class="active" id="btnMethodFiles" aria-pressed="true">📄 Upload Files</button>
        <button class="inactive" id="btnMethodFolder" aria-pressed="false">📂 Select Folder</button>
      </div>
      
      <div id="methodFiles">
        <h3>📄 Upload Files</h3>
        <label for="fileInput" class="sr-only">Select files to upload</label>
        <input type="file" id="fileInput" multiple accept=".txt,.md,.pdf,.doc,.docx,.csv,.json,.html,.xml" aria-describedby="fileInput-hint">
        <p id="fileInput-hint" class="hint">Select multiple files to upload to the knowledge base</p>
        <div id="selectedFilesList" class="file-list" style="display: none;"></div>
        
        <div class="checkbox-wrapper auto-backup-wrapper" style="margin: 15px 0; padding: 10px; background: rgba(0, 212, 255, 0.05); border-radius: 8px;">
          <input type="checkbox" id="autoBackupFiles" ${Le()?"checked":""}>
          <label for="autoBackupFiles" style="font-weight: 500;">
            💾 Auto-backup during upload
            <span style="display: block; font-size: 12px; font-weight: normal; color: var(--text-secondary); margin-top: 4px;">
              Creates backups every ${Fe} files and at completion
            </span>
          </label>
        </div>
        
        <button id="ingestFilesBtn" class="btn" aria-label="Start ingesting selected files">📥 Ingest Files</button>
        <button id="clearFilesBtn" class="btn danger" aria-label="Clear all selected files">🗑️ Clear All</button>
      </div>
      
      <div id="methodFolder" style="display: none;">
        <h3>📂 Select Folder</h3>
        <div class="folder-input-wrapper">
          <label for="folderPath" class="sr-only">Folder path</label>
          <input type="text" id="folderPath" placeholder="Select or enter folder path...">
          <button class="folder-btn" id="browseFolderBtn" aria-label="Browse for folder">📂 Browse</button>
          <input type="file" id="folderInput" webkitdirectory style="display: none;" aria-label="Select folder">
        </div>
        
        <div id="folderFiles" class="file-list" style="display: none;">
          <strong>Files to ingest:</strong>
          <div id="folderFileCount"></div>
        </div>
        
        <div class="checkbox-wrapper">
          <input type="checkbox" id="recursive" checked>
          <label for="recursive">Scan subfolders recursively</label>
        </div>
        
        <div class="checkbox-wrapper auto-backup-wrapper" style="margin-top: 10px; padding: 10px; background: rgba(0, 212, 255, 0.05); border-radius: 8px;">
          <input type="checkbox" id="autoBackup" ${Le()?"checked":""}>
          <label for="autoBackup" style="font-weight: 500;">
            💾 Auto-backup during upload
            <span style="display: block; font-size: 12px; font-weight: normal; color: var(--text-secondary); margin-top: 4px;">
              Creates backups every ${Fe} files and at completion
            </span>
          </label>
        </div>
        
        <button id="ingestFolderBtn" class="btn" aria-label="Start ingesting folder" style="margin-top: 15px;">📥 Ingest Folder</button>
      </div>
      
      <div id="ingestProgress"></div>
      <div id="uploadErrorLog" class="error-log-container" style="display: none;"></div>
      
      <!-- Management Actions -->
      <div class="management-actions" style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
        <button id="clearUploadHistoryBtn" class="btn" style="background: rgba(255,255,255,0.1); font-size: 12px;">
          🗑️ Clear Upload History
        </button>
        <p class="hint" style="margin-top: 5px;">This will reset the list of previously uploaded files</p>
      </div>
      
      <!-- Database Management Panel -->
      ${Ln()}
    </div>
  `}let Te="",_=[];function kt(e){const t=e.match(/[記體歷興員門車龍馬魚鳥學長東國會來時個們說開發問過這種處從當與麼灣]/g),n=e.match(/[记体历兴员门车龙马鱼鸟学长东国会来时个们说开发问过这种处从当与]/g),o=t?t.length:0,s=n?n.length:0;return o>0&&o>=s}function Xn(e){if(e==null||e.preventDefault(),e==null||e.stopPropagation(),!Te){alert("No answer to print. Please run a query first.");return}let t=Te;t=t.replace(/<query-h1>([\s\S]*?)<\/query-h1>/gi,"# $1"),t=t.replace(/<query-h2>([\s\S]*?)<\/query-h2>/gi,"## $1"),t=t.replace(/<query-h3>([\s\S]*?)<\/query-h3>/gi,"### $1"),t=t.replace(/<query-h4>([\s\S]*?)<\/query-h4>/gi,"#### $1"),t=t.replace(/<span[^>]*citation-ref[^>]*>\[(\d+)\]<\/span>/gi,"[$1]"),t=t.replace(/\(\s*Source\s+\d+(?:\s*,\s*Source\s+\d+)*\s*\)/gi,""),t=t.replace(/Source\s+\d+(?:\s*,\s*Source\s+\d+)*/gi,""),t=t.replace(/<\/?p>/gi,""),t=t.replace(/<div[^>]*class="reference-item"[^>]*>\s*<span[^>]*class="ref-number"[^>]*>(\d+\.?)<\/span>\s*(?:<span[^>]*class="ref-source"[^>]*>)?([^<]+)(?:<\/span>)?\s*<\/div>/gi,"[$1] $2<br>"),t=t.replace(/<\/?(div|span)[^>]*>/gi,"");let n=t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");const o=n.split(`
`),s=[];let i=0,a=0,r=!0,d=!1;for(const u of o){const w=u.match(/^#\s+(.+)$/),y=u.match(/^##\s+(.+)$/),b=u.match(/^###\s+(.+)$/);if(w||y||b){let m=(w||y||b)[1].trim();const g=w?1:y?2:3;if(m=m.replace(/^[一二三四五六七八九十]+[、.．]\s*/,""),m=m.replace(/^\d+\.\s*[一二三四五六七八九十]+[、.．]\s*/,""),m=m.replace(/^\d+\.\s*\d+\.\d+\s*/,""),m=m.replace(/^\d+\.\d+\.?\s*/,""),m=m.replace(/^\d+\.\s*/,""),m=m.replace(/^\d+\s+/,""),r){r=!1,d=!0,s.push(`<div class="print-document-title">${m}</div>`);continue}if(d){if(d=!1,/executive\s+summary|summary|摘要|引言|前言|概述|導言/i.test(m)){let T=m;/executive\s+summary/i.test(m)&&kt(t)&&(T="摘要"),s.push(`<div class="print-section-intro">${T}</div>`);continue}i=1,s.push(`<div class="print-section-title">${i}. ${m}</div>`);continue}if(/^references?$|參考文獻|参考文献/i.test(m)){s.push(`<div class="print-section-references">${m}</div>`);continue}g<=2?(i++,a=0,s.push(`<div class="print-section-title">${i}. ${m}</div>`)):(a++,s.push(`<div class="print-section-heading">${i}.${a} ${m}</div>`))}else s.push(u)}n=s.join(`
`),n=n.replace(/\n/g,"<br>");const c=`<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Query Result</title>
  <style>
    @page {
      margin: 2.0cm 1.2cm;
    }
    @media print {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 11pt;
        line-height: 1.6;
        margin: 0;
        color: #000;
      }
      h1 { font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 0.2cm; margin-top: 0.5cm; }
      h2 { font-size: 14pt; margin-top: 0.1cm; color: #333; }
      h3 { font-size: 12pt; margin-top: 0cm; color: #555; }
      .no-print { display: none; }
      .h1-bold { 
        font-size: 18pt; 
        font-weight: bold; 
        margin-top: 0.4cm; 
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      .h2-bold { 
        font-size: 15pt; 
        font-weight: bold; 
        margin-top: 0.2cm; 
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 13pt; 
        font-weight: bold; 
        margin-top: 0.15cm; 
        margin-bottom: 0.05cm;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.2cm;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.15cm;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 8px 12px;
        margin-top: 0.15cm;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format */
      query-h1 {
        display: block;
        font-size: 18pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      query-h2 {
        display: block;
        font-size: 15pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.15cm;
        margin-bottom: 0.05cm;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 0.3cm;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 0.3cm;
      }
      /* Clean print format styles */
      .print-document-title {
        font-size: 16pt;
        font-weight: bold;
        margin-top: 0;
        margin-bottom: 0.4cm;
        color: #000;
        border-bottom: 2px solid #000;
        padding-bottom: 0.15cm;
        text-align: center;
      }
      .print-section-intro {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
        font-style: italic;
      }
      .print-section-references {
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.5cm;
        margin-bottom: 0.2cm;
        color: #2e7d32;
        border-top: 1px solid #2e7d32;
        padding-top: 0.2cm;
      }
      .print-section-title {
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #000;
        border-bottom: 1px solid #333;
        padding-bottom: 0.1cm;
      }
      .print-section-heading {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
      }
      .print-section-subheading {
        font-size: 11pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #555;
      }
      .print-references-section {
        margin-top: 0.8cm;
        padding-top: 0.3cm;
        border-top: 1px solid #333;
      }
      .print-references-header {
        font-size: 13pt;
        font-weight: bold;
        margin-bottom: 0.2cm;
        color: #000;
      }
      .print-references-list {
        padding-left: 0.3cm;
      }
      .print-reference-item {
        margin-bottom: 0.15cm;
        font-size: 10pt;
      }
      .print-ref-number {
        font-weight: bold;
        margin-right: 0.2cm;
      }
    }
    @media screen {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        max-width: 800px;
        margin: 2cm auto;
        padding: 1cm;
        line-height: 1.6;
      }
      .print-button {
        display: block;
        margin: 1cm auto;
        padding: 10px 30px;
        font-size: 14pt;
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .print-button:hover { background: #45a049; }
      .h1-bold { 
        font-size: 20pt; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      .h2-bold { 
        font-size: 16pt; 
        font-weight: bold; 
        margin-top: 15px; 
        margin-bottom: 8px;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 14pt; 
        font-weight: bold; 
        margin-top: 12px; 
        margin-bottom: 6px;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 16px;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 12px;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 10px 14px;
        margin-top: 12px;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format - screen view */
      query-h1 {
        display: block;
        font-size: 20pt;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      query-h2 {
        display: block;
        font-size: 16pt;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 14pt;
        font-weight: bold;
        margin-top: 12px;
        margin-bottom: 6px;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 8px;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 8px;
      }
    }
  </style>
</head>
<body>
  <div class="answer">${n}</div>
</body>
</html>`,f=new Blob([c],{type:"text/html"}),h=URL.createObjectURL(f);if(!window.open(h,"_blank")){alert("Please allow popups to print the answer."),URL.revokeObjectURL(h);return}}function Yn(){var e,t,n,o,s,i;(e=l("runQueryBtn"))==null||e.addEventListener("click",be),(t=l("printQueryBtn"))==null||t.addEventListener("click",a=>Xn(a)),(n=l("queryText"))==null||n.addEventListener("input",()=>{const a=l("printQueryBtn");a&&(a.style.display="none")}),(o=l("testQueryCompanies"))==null||o.addEventListener("click",()=>we("What companies are mentioned?")),(s=l("testQueryRelations"))==null||s.addEventListener("click",()=>we("What relationships exist?")),(i=l("testQueryOverview"))==null||i.addEventListener("click",()=>we("Give me an overview"))}function we(e){const t=l("queryText");t&&(t.value=e),be()}function Zn(){const e=document.querySelector('input[name="queryMode"]:checked');return(e==null?void 0:e.value)||"hybrid"}function eo(){const e=document.querySelector('input[name="queryDetail"]:checked');switch((e==null?void 0:e.value)||"balanced"){case"quick":return{top_k:10,ultra_comprehensive:!1,detailed:!1,label:"Quick"};case"ultra":return{top_k:40,ultra_comprehensive:!0,detailed:!0,label:"Ultra Deep"};case"comprehensive":return{top_k:30,ultra_comprehensive:!1,detailed:!0,label:"Comprehensive"};case"balanced":default:return{top_k:20,ultra_comprehensive:!1,detailed:!1,label:"Balanced"}}}async function be(){var w;const e=(w=l("queryText"))==null?void 0:w.value.trim();if(!e){alert("Please enter a question");return}Ct()&&Ae();const t=Zn(),n=eo(),o=l("answerText"),s=l("sourcesText"),i=l("runQueryBtn"),a=l("printQueryBtn");G(!0),M("runQueryBtn",!0),a&&(a.style.display="none");const r=n.ultra_comprehensive,d=n.detailed&&!r,c=r?"10-15 min":d?"8-10 min":"3-5 min";i&&(i.textContent=`⏳ ${n.label} Mode (${c})...`),V("queryResult",!0);let f="";r?f="Retrieving 40 chunks + Generating ultra-extensive (3000+ words) answer...":d?f="Retrieving 30 chunks + Generating comprehensive (2000+ words) answer...":n.top_k===10?f="Retrieving 10 chunks + ~ 1000 words Generating standard answer...":f="Retrieving 20 chunks + ~1500 words Generating standard answer...",o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>${f}<br>Estimated time: ${c}<br><small>Please wait, do not close or refresh the page</small>`,s.textContent="";const h=new AbortController;He(h);let F;r?F=9e5:n.detailed?F=6e5:F=3e5;const u=setTimeout(()=>h.abort(),F);try{const y=await at({message:e,mode:t,top_k:n.top_k,ultra_comprehensive:n.ultra_comprehensive,detailed:n.detailed},h.signal);clearTimeout(u);const b=y.response||y.answer||JSON.stringify(y,null,2);console.log("[Query] Full result:",y),console.log("[Query] Result keys:",Object.keys(y));const m=y.sources||y.source_documents||y.source||y.chunks;console.log("[Query] Raw sources:",m),console.log("[Query] sources type:",typeof m),console.log("[Query] sources isArray:",Array.isArray(m)),typeof m=="number"&&console.warn("[Query] Backend returned source COUNT instead of source filenames. References cannot be displayed."),Array.isArray(m)?_=m.map(p=>typeof p=="string"?p:p&&typeof p=="object"?p.filename||p.doc_id||p.name||JSON.stringify(p):String(p)):_=[],console.log("[Query] Processed sources:",_);const g=new Set,S=b.match(/Source\s+(\d+)/gi);S&&S.forEach(p=>{const x=p.match(/\d+/);x&&g.add(parseInt(x[0],10))}),console.log("[Query] Sources cited in text:",Array.from(g));let T=b;if(g.size>0&&_.length>0){const p=Array.from(g).sort((x,$)=>x-$).map(x=>_[x-1]).filter(x=>x!==void 0);p.length>0&&(T+=`


## References

`,p.forEach((x,$)=>{T+=`${$+1}. ${x}
`}))}if(Te=T,a&&(a.style.display="inline-block"),b.startsWith("Found")&&b.includes("relevant chunks"))to(b,o);else{let p=b;if(g.size>0&&_.length>0){const x=Array.from(g).sort(($,v)=>$-v).map($=>_[$-1]).filter($=>$!==void 0);x.length>0&&(p+=`


## References

`+x.map(($,v)=>`${v+1}. ${$}`).join(`
`))}o.innerHTML=ye(p),setTimeout(()=>$t(o),100)}const k=y.sources||y.source_documents;if(_.length>0){let p="";if(g.size>0){const x=Array.from(g).sort(($,v)=>$-v).map($=>_[$-1]).filter($=>$!==void 0);x.length>0&&(p+='<div class="sources-section references-section">',p+='<div class="sources-header references-header">📚 References</div>',x.forEach(($,v)=>{p+=`<div class="source-item references-item">${v+1}. ${L($)}</div>`}),p+="</div>")}p+='<div class="sources-section verification-section">',p+='<div class="sources-header verification-header">🔍 Sources (for Verification)</div>',_.forEach((x,$)=>{p+=`<div class="source-item verification-item">${$+1}. ${L(x)}</div>`}),p+="</div>",s.innerHTML=p}else typeof k=="number"?s.innerHTML=`<div class="source-item">Found ${k} sources (filenames not available - backend config issue)</div>`:s.textContent="No sources available"}catch(y){clearTimeout(u),no(y,o)}finally{G(!1),He(null),M("runQueryBtn",!1),i&&(i.textContent="🔍 Ask Question")}}function ye(e){if(!e)return"";const t=/References?|參考文獻|参考文献/i.test(e),n=e.search(/References?|參考文獻|参考文献/i);console.log("[formatQueryResponse] Input length:",e.length,"Has References:",t,"Refs position:",n),n>0&&console.log("[formatQueryResponse] References preview:",e.substring(n,n+200));let o=e;o=o.replace(/<query-h1>([\s\S]*?)<\/query-h1>/gi,"# $1"),o=o.replace(/<query-h2>([\s\S]*?)<\/query-h2>/gi,"## $1"),o=o.replace(/<query-h3>([\s\S]*?)<\/query-h3>/gi,"### $1"),o=o.replace(/<query-h4>([\s\S]*?)<\/query-h4>/gi,"#### $1"),o=o.replace(/\(\s*Source\s+\d+(?:\s*,\s*Source\s+\d+)*\s*\)/gi,""),o=o.replace(/Source\s+\d+(?:\s*,\s*Source\s+\d+)*/gi,""),o=o.replace(/<span[^>]*citation-ref[^>]*>\[(\d+)\]<\/span>/gi,"[$1]"),o=o.replace(/<\/?p>/gi,"");const s=o;o=o.replace(/<div[^>]*class="reference-item"[^>]*>\s*<span[^>]*class="ref-number"[^>]*>(\d+\.)<\/span>\s*([^<]+)<\/div>/gi,"$1 $2"),o=o.replace(/<div[^>]*class="reference-item"[^>]*>\s*(\d+\.)\s*([^<]+)<\/div>/gi,"$1 $2"),o!==s&&console.log("[formatQueryResponse] Converted reference-item divs"),o=o.replace(/<\/?(div|span)[^>]*>/gi,""),o=o.replace(/the\s+literature/gi,"相關文獻"),o=o.replace(/Note on Context[\s\S]*?I will answer[^.]*\./gi,""),o=o.replace(/Context Note[\s\S]*?general knowledge[^.]*\./gi,""),o=o.replace(/The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi,""),o=o.replace(/The (?:provided |available |indexed )?context (?:does not contain|lacks|is (?:unrelated|irrelevant))[\s\S]*?\./gi,""),o=o.replace(/I will answer your question based on (?:general |my )?knowledge[^.]*\./gi,""),o=o.replace(/Based on (?:general |my )?knowledge,?[^.]*\./gi,""),o=o.replace(/\(Remove this[^)]*\)/gi,""),o=o.replace(/\[Remove this[^\]]*\]/gi,""),[/I couldn't find any information[^.]*\./gi,/Please try a different search term[^.]*\./gi,/The indexed data may contain formatting issues[^.]*\./gi,/Note: This response is based on[^.]*\./gi,/Disclaimer:[^.]*\./gi,/I apologize, but[^.]*\./gi,/I don't see any information[^.]*\./gi,/There is no information[^.]*\./gi,/The context provided (?:does not|doesn't) (?:contain|have|discuss)[^.]*\./gi].forEach(u=>{o=o.replace(u,"")});const a=o.split(`
`);let r=0,d=0,c=!0,f=!1;const h=[];for(const u of a){const w=u.match(/^#\s+(.+)$/),y=u.match(/^##\s+(.+)$/),b=u.match(/^###\s+(.+)$/),m=u.match(/^####\s+(.+)$/);if(w||y||b||m){let g=(w||y||b||m)[1].trim();const S=w?1:y?2:b?3:4;if(g=g.replace(/^[一二三四五六七八九十]+[、.．]\s*/,""),g=g.replace(/^\d+\.\s*[一二三四五六七八九十]+[、.．]\s*/,""),g=g.replace(/^\d+\.\s*\d+\.\d+\s*/,""),g=g.replace(/^\d+\.\d+\.?\s*/,""),g=g.replace(/^\d+\.\s*/,""),g=g.replace(/^\d+\s+/,""),c){c=!1,f=!0,h.push(`<strong class="document-title">${g}</strong>`);continue}if(f){if(f=!1,/executive\s+summary|summary|摘要|引言|前言|概述|導言|執行摘要/i.test(g)){let k=g;/executive\s+summary/i.test(g)&&kt(o)&&(k="摘要"),h.push(`<strong class="section-intro">${k}</strong>`);continue}r=1,d=0,h.push(`<strong class="section-title">${r}. ${g}</strong>`);continue}if(/^references?$|參考文獻|参考文献/i.test(g)){h.push(`<strong class="section-references">${g}</strong>`);continue}S<=2?(r++,d=0,h.push(`<strong class="section-title">${r}. ${g}</strong>`)):S===3?r===0?(r=1,h.push(`<strong class="section-title">${r}. ${g}</strong>`)):(d++,h.push(`<strong class="section-heading">${r}.${d} ${g}</strong>`)):(d++,h.push(`<strong class="section-heading">${r}.${d} ${g}</strong>`))}else h.push(u)}o=h.join(`
`),o=o.replace(/\n{3,}/g,`

`),o=o.replace(/^\s*\([^)]+\)\s*$/gmi,""),o=o.replace(/([A-Za-z])(\t+|\s{2,})([|⟨⟩])/g,"$1 $3"),o=o.replace(/(\))\t+|\s{2,}([|⟨⟩])/g,"$1 $2"),o=o.replace(/([|⟨⟩][^|⟨⟩]*?)(\t+|\s{2,})(?=\))/g,"$1"),o=o.replace(/\t+/g," "),o=o.replace(/\s{3,}/g," "),o=o.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>"),o=o.replace(/\*([^*]+)\*/g,"<em>$1</em>"),o=o.replace(/^- (.+)$/gm,"• $1"),o=o.replace(/^\* (.+)$/gm,"• $1"),o=o.replace(/\n/g,"<br>"),o=o.replace(/(<br>){3,}/g,"<br><br>"),o=o.replace(/(<\/strong>)([A-Za-z\u4e00-\u9fff])/g,"$1<br><br>$2");const F=/References?|參考文獻|参考文献/i.test(o);return console.log("[formatQueryResponse] Output length:",o.length,"Has References:",F),o}function $t(e){if(window.katex&&window.renderMathInElement)try{window.renderMathInElement(e,{delimiters:[{left:"$$",right:"$$",display:!0},{left:"$",right:"$",display:!1},{left:"\\[",right:"\\]",display:!0},{left:"\\(",right:"\\)",display:!1},{left:"\\begin{equation}",right:"\\end{equation}",display:!0},{left:"\\begin{align}",right:"\\end{align}",display:!0},{left:"\\begin{matrix}",right:"\\end{matrix}",display:!0}],throwOnError:!1,errorColor:"#cc0000",macros:{"\\RR":"\\mathbb{R}","\\NN":"\\mathbb{N}","\\ZZ":"\\mathbb{Z}"}})}catch(t){console.error("KaTeX rendering error:",t)}else setTimeout(()=>$t(e),500)}function to(e,t){var a;const n=e.match(/Found (\d+) relevant chunks/),o=n?n[1]:"some";let s="<h3>⚠️ LLM Processing Timed Out</h3>";s+=`<p>The AI processing timed out after 25 seconds. Showing ${o} raw text chunks instead:</p><hr>`;const i=e.indexOf(`

`);i>0?e.substring(i+2).split(`

`).forEach((c,f)=>{c.trim()&&(s+=`<h4>Chunk ${f+1}</h4><pre>${L(c)}</pre><hr>`)}):s+=`<pre>${L(e)}</pre>`,s+='<button id="retryQueryBtn" class="btn">🔄 Retry with Simpler Query</button>',t.innerHTML=s,(a=l("retryQueryBtn"))==null||a.addEventListener("click",()=>{var c;const r=((c=l("queryText"))==null?void 0:c.value)||"",d=r.replace(/explain|in detail|with examples|comprehensive|detailed/gi,"").trim();d&&d!==r?(l("queryText").value=d,be()):alert('Try a simpler, more specific query. Example: "What is Bayesian probability?"')})}function no(e,t){var n;console.error("Query error:",e),e instanceof Error?e.name==="AbortError"?t.textContent="⏰ Query was cancelled or timed out after 5 minutes.":e.message.includes("network")||e.message.includes("fetch")?(t.innerHTML='❌ Network error. <button id="retryErrorBtn" class="btn">Retry</button>',(n=l("retryErrorBtn"))==null||n.addEventListener("click",be)):t.textContent=`❌ Error: ${e.message}`:t.textContent="❌ Unknown error occurred"}function oo(){return`
    <div id="query" class="tab-content card" role="tabpanel" aria-labelledby="tab-query">
      <h2>🔍 Query Knowledge Graph</h2>
      
      
      <h3 id="queryModeLabel">Query Mode</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryModeLabel">
        <label class="radio-option">
          <input type="radio" name="queryMode" value="hybrid" checked> Hybrid
        </label>
        <label class="radio-option">
          <input type="radio" name="queryMode" value="local"> Local
        </label>
        <label class="radio-option">
          <input type="radio" name="queryMode" value="global"> Global
        </label>
      </div>
      
      <h3 id="queryDetailLabel">Answer Detail Level</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryDetailLabel">
        <label class="radio-option" title="Quick answer using 10 chunks">
          <input type="radio" name="queryDetail" value="quick"> ⚡ Quick
        </label>
        <label class="radio-option" title="Balanced answer using 20 chunks">
          <input type="radio" name="queryDetail" value="balanced" checked> 📊 Balanced
        </label>
        <label class="radio-option" title="Comprehensive answer (2000+ words)">
          <input type="radio" name="queryDetail" value="comprehensive"> 📚 Comprehensive
        </label>
        <label class="radio-option" title="Ultra comprehensive (3000-4000 words) - Extended wait">
          <input type="radio" name="queryDetail" value="ultra"> 🎓 Ultra Deep
        </label>
      </div>
      
      <label for="queryText" class="sr-only">Enter your question</label>
      <textarea id="queryText" placeholder="Ask a question about your knowledge graph...&#10;Example: What do you know about Alibaba?&#10;&#10;Tip: For complex queries, the AI may time out after 25 seconds.&#10;Try simpler, more specific questions for better results." rows="6" aria-describedby="queryText-hint"></textarea>
      <p id="queryText-hint" class="hint">Type your question about the knowledge graph</p>
      
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <button id="runQueryBtn" class="btn" aria-label="Submit query">🔍 Ask Question</button>
        <button type="button" id="printQueryBtn" class="btn" style="padding: 6px 12px; font-size: 13px; display: none;" aria-label="Print answer">🖨️ Print</button>
      </div>
      
      <div id="queryResult" style="display: none;" aria-live="polite">

        <div id="answerText" class="result-box query-answer"></div>
        
        <h3>Sources:</h3>
        <div id="sourcesText" class="sources-box"></div>
      </div>
      
      <!-- KaTeX for math rendering -->
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"><\/script>
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"><\/script>
      
      <style>
        /* Query Response Formatting */
        .query-answer {
          line-height: 1.8;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
        
        /* Keep math equations on single line */
        .query-answer .math-inline {
          white-space: nowrap;
          display: inline-block;
        }
        
        /* H1 - Title (Cyan, biggest, boldest) */
        .query-answer .query-h1 {
          display: block;
          font-size: 1.8em;
          font-weight: 800;
          color: #00BCD4;
          margin-top: 18px;
          margin-bottom: 16px;
          padding-bottom: 10px;
          border-bottom: 3px solid #00BCD4;
        }
        
        /* H2 - Executive Summary (Green, bold) */
        .query-answer .query-h2 {
          display: block;
          font-size: 1.5em;
          font-weight: 700;
          color: #4CAF50;
          margin-top: 14px;
          margin-bottom: 10px;
          padding-left: 12px;
          border-left: 4px solid #4CAF50;
        }
        
        /* H3 - Section headings with blue border */
        .query-answer .query-h3 {
          display: block;
          font-size: 1.3em;
          font-weight: 600;
          color: #64b5f6;
          margin-top: 12px;
          margin-bottom: 8px;
          border-left: 3px solid #64b5f6;
          padding-left: 10px;
        }
        
        /* H4 - Subsection headings */
        .query-answer .query-h4 {
          display: block;
          font-size: 1.2em;
          font-weight: 600;
          color: #e0e0e0;
          margin-top: 10px;
          margin-bottom: 6px;
        }
        
        /* References section (Green) */
        .query-answer .references-section,
        .query-answer .query-references {
          background: rgba(76, 175, 80, 0.1);
          border: 1px solid rgba(76, 175, 80, 0.3);
          border-radius: 8px;
          padding: 12px 16px;
          margin-top: 20px;
          color: #4CAF50;
          font-weight: 600;
        }
        
        /* Sources for Verification section (Orange) */
        .query-answer .sources-section,
        .query-answer .sources-verification {
          background: rgba(255, 152, 0, 0.1);
          border: 1px dashed rgba(255, 152, 0, 0.5);
          border-radius: 8px;
          padding: 12px 16px;
          margin-top: 16px;
          color: #FF9800;
          font-weight: 600;
          font-family: monospace;
        }
        
        /* Conclusion styling */
        .query-answer .conclusion,
        .query-answer .query-conclusion {
          background: rgba(156, 39, 176, 0.1);
          border-left: 4px solid #9C27B0;
          padding: 12px 16px;
          margin-top: 16px;
          font-style: italic;
        }
        
        .query-answer br + br {
          content: "";
          display: block;
          margin-top: 8px;
        }
        
        /* Academic Citations [X] */
        .query-answer .citation-ref,
        .query-answer [class*="citation"] {
          color: #64b5f6;
          font-weight: 600;
          font-size: 0.85em;
          vertical-align: super;
          margin: 0 1px;
        }
        
        /* Inline citation numbers [1], [2,3] */
        .query-answer {
          /* Match bracketed numbers and style them as citations */
        }
        
        /* Bold text **text** */
        .query-answer strong {
          font-weight: 600;
          color: var(--text-primary, #e0e0e0);
        }
        
        /* Table Styling */
        .query-table-container {
          overflow-x: auto;
          margin: 16px 0;
          border-radius: 8px;
          border: 1px solid var(--border-color, #333);
        }
        
        .query-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9em;
        }
        
        .query-table th,
        .query-table td {
          padding: 10px 12px;
          text-align: left;
          border-bottom: 1px solid var(--border-color, #333);
        }
        
        .query-table th {
          background: rgba(76, 175, 80, 0.15);
          font-weight: 600;
          color: var(--primary-color, #4CAF50);
        }
        
        .query-table tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }
        
        .query-table tr:last-child td {
          border-bottom: none;
        }
        
        .query-table-container + br {
          display: none;
        }
        
        /* Math Formula Styling */
        .query-answer .katex {
          font-size: 1.1em;
          color: var(--text-primary, #e0e0e0);
        }
        
        .query-answer .katex-display {
          margin: 1.5em 0;
          overflow-x: auto;
          overflow-y: hidden;
          padding: 1em;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 8px;
          border-left: 3px solid var(--primary-color, #4CAF50);
        }
        
        .query-answer .katex-display .katex {
          font-size: 1.2em;
        }
        
        /* Inline math */
        .query-answer .katex-inline {
          padding: 0 0.2em;
        }
        
        /* Math error coloring */
        .query-answer .katex-error {
          color: #ff6b6b;
          border-bottom: 1px dashed #ff6b6b;
        }
        
        /* Clean Academic Format Styles */
        .query-answer .document-title {
          display: block;
          font-size: 1.6em;
          font-weight: 800;
          color: #00d4ff;
          margin-top: 0;
          margin-bottom: 20px;
          padding-bottom: 10px;
          border-bottom: 3px solid #00d4ff;
          text-align: center;
        }
        
        .query-answer .section-intro {
          display: block;
          font-size: 1.2em;
          font-weight: 600;
          color: #c0c0c0;
          margin-top: 20px;
          margin-bottom: 12px;
          font-style: italic;
        }
        
        .query-answer .section-references {
          display: block;
          font-size: 1.4em;
          font-weight: 700;
          color: #4CAF50;
          margin-top: 30px;
          margin-bottom: 15px;
          padding-top: 15px;
          border-top: 2px solid #4CAF50;
        }
        
        .query-answer .section-title {
          display: block;
          font-size: 1.3em;
          font-weight: 700;
          color: #e0e0e0;
          margin-top: 24px;
          margin-bottom: 12px;
          padding-bottom: 6px;
          border-bottom: 2px solid #4CAF50;
        }
        
        .query-answer .section-heading {
          display: block;
          font-size: 1.1em;
          font-weight: 600;
          color: #b0b0b0;
          margin-top: 16px;
          margin-bottom: 8px;
        }
        
        /* Clean References Section */
        .query-answer .clean-references-section {
          margin-top: 32px;
          padding-top: 16px;
          border-top: 2px solid #4CAF50;
        }
        
        .query-answer .clean-references-header {
          font-size: 1.3em;
          font-weight: 700;
          color: #4CAF50;
          margin-bottom: 12px;
        }
        
        .query-answer .clean-references-list {
          background: rgba(76, 175, 80, 0.05);
          border-radius: 8px;
          padding: 12px 16px;
        }
        
        .query-answer .clean-reference-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 6px 0;
          font-size: 0.95em;
          color: #c0c0c0;
          border-bottom: 1px dotted rgba(255, 255, 255, 0.1);
        }
        
        .query-answer .clean-reference-item:last-child {
          border-bottom: none;
        }
        
        .query-answer .clean-ref-number {
          font-weight: 600;
          color: #4CAF50;
          min-width: 24px;
          flex-shrink: 0;
        }
        
        /* Verification Sources Section */
        .query-answer .verification-sources-section {
          margin-top: 24px;
          padding-top: 12px;
          border-top: 1px dashed #FF9800;
        }
        
        .query-answer .verification-sources-header {
          font-size: 1.1em;
          font-weight: 600;
          color: #FF9800;
          margin-bottom: 10px;
        }
        
        .query-answer .verification-source-item {
          font-family: 'Courier New', monospace;
          font-size: 0.85em;
          color: #aaa;
          padding: 4px 0;
          word-break: break-all;
        }
      </style>
      
      <h3>Test Queries</h3>
      <button id="testQueryCompanies" class="btn" aria-label="Run test query for companies">Companies</button>
      <button id="testQueryRelations" class="btn" aria-label="Run test query for relationships">Relationships</button>
      <button id="testQueryOverview" class="btn" aria-label="Run test query for overview">Overview</button>
    </div>
  `}const so="modulepreload",io=function(e,t){return new URL(e,t).href},Ke={},ro=function(t,n,o){let s=Promise.resolve();if(n&&n.length>0){const a=document.getElementsByTagName("link"),r=document.querySelector("meta[property=csp-nonce]"),d=(r==null?void 0:r.nonce)||(r==null?void 0:r.getAttribute("nonce"));s=Promise.allSettled(n.map(c=>{if(c=io(c,o),c in Ke)return;Ke[c]=!0;const f=c.endsWith(".css"),h=f?'[rel="stylesheet"]':"";if(!!o)for(let w=a.length-1;w>=0;w--){const y=a[w];if(y.href===c&&(!f||y.rel==="stylesheet"))return}else if(document.querySelector(`link[href="${c}"]${h}`))return;const u=document.createElement("link");if(u.rel=f?"stylesheet":so,f||(u.as="script"),u.crossOrigin="",u.href=c,d&&u.setAttribute("nonce",d),document.head.appendChild(u),f)return new Promise((w,y)=>{u.addEventListener("load",w),u.addEventListener("error",()=>y(new Error(`Unable to preload CSS for ${c}`)))})}))}function i(a){const r=new Event("vite:preloadError",{cancelable:!0});if(r.payload=a,window.dispatchEvent(r),!r.defaultPrevented)throw a}return s.then(a=>{for(const r of a||[])r.status==="rejected"&&i(r.reason);return t().catch(i)})};let se="";function ao(e){const t=e.match(/[記體歷興員門車龍馬魚鳥學長東國會來時個們說開發問過這種處從當與麼灣]/g),n=e.match(/[记体历兴员门车龙马鱼鸟学长东国会来时个们说开发问过这种处从当与]/g),o=t?t.length:0,s=n?n.length:0;return o>0&&o>=s}let B=[];function ze(){const e=document.querySelector('input[name="queryFileDetail"]:checked');switch((e==null?void 0:e.value)||"balanced"){case"quick":return{top_k:10,ultra_comprehensive:!1,detailed:!1,label:"Quick"};case"ultra":return{top_k:40,ultra_comprehensive:!0,detailed:!0,label:"Ultra Deep"};case"comprehensive":return{top_k:30,ultra_comprehensive:!1,detailed:!0,label:"Comprehensive"};case"balanced":default:return{top_k:20,ultra_comprehensive:!1,detailed:!1,label:"Balanced"}}}function lo(e){if(e==null||e.preventDefault(),e==null||e.stopPropagation(),!se){alert("No answer to print. Please run a query first.");return}let t=se;t=t.replace(/<query-h1>([\s\S]*?)<\/query-h1>/gi,"# $1"),t=t.replace(/<query-h2>([\s\S]*?)<\/query-h2>/gi,"## $1"),t=t.replace(/<query-h3>([\s\S]*?)<\/query-h3>/gi,"### $1"),t=t.replace(/<query-h4>([\s\S]*?)<\/query-h4>/gi,"#### $1"),t=t.replace(/\(\s*Source\s+\d+(?:\s*,\s*Source\s+\d+)*\s*\)/gi,""),t=t.replace(/Source\s+\d+(?:\s*,\s*Source\s+\d+)*/gi,""),t=t.replace(/\[\d+(?:\s*,\s*\d+)*\]/g,""),t=t.replace(/<span[^>]*citation-ref[^>]*>\[?\d*\]?<\/span>/gi,""),t=t.replace(/<\/?p>/gi,""),t=t.replace(/<\/?(div|span)[^>]*>/gi,"");let n="";const o=t.match(/(?:##?\s*)?(?:📚\s*)?(?:References?|參考文獻|参考文献)([\s\S]*)/i);if(o){const y=o[1].split(`
`).filter(b=>b.trim());n='<div class="print-references-section">',n+='<div class="print-references-header">References</div>',n+='<div class="print-references-list">',y.forEach(b=>{const m=b.match(/^\s*(\d+)\.\s+(.+)$/);m&&!/References?|參考文獻|参考文献/i.test(m[2])&&(n+=`<div class="print-reference-item"><span class="print-ref-number">${m[1]}.</span> ${m[2]}</div>`)}),n+="</div></div>",t=t.replace(/(?:##?\s*)?(?:📚\s*)?(?:References?|參考文獻|参考文献)[\s\S]*/i,"")}let s=t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");const i=s.split(`
`),a=[];let r=0,d=0,c=!0,f=!1;for(const y of i){const b=y.match(/^#\s+(.+)$/),m=y.match(/^##\s+(.+)$/),g=y.match(/^###\s+(.+)$/);if(b||m||g){let S=(b||m||g)[1].trim();const T=b?1:m?2:3;if(S=S.replace(/^[一二三四五六七八九十]+[、.．]\s*/,""),S=S.replace(/^\d+\.\s*[一二三四五六七八九十]+[、.．]\s*/,""),S=S.replace(/^\d+\.\s*\d+\.\d+\s*/,""),S=S.replace(/^\d+\.\d+\.?\s*/,""),S=S.replace(/^\d+\.\s*/,""),S=S.replace(/^\d+\s+/,""),c){c=!1,f=!0,a.push(`<div class="print-document-title">${S}</div>`);continue}if(f){if(f=!1,/executive\s+summary|summary|摘要|引言|前言|概述|導言/i.test(S)){let p=S;/executive\s+summary/i.test(S)&&ao(t)&&(p="摘要"),a.push(`<div class="print-section-intro">${p}</div>`);continue}r=1,a.push(`<div class="print-section-title">${r}. ${S}</div>`);continue}T<=2?(r++,d=0,a.push(`<div class="print-section-title">${r}. ${S}</div>`)):(d++,a.push(`<div class="print-section-heading">${r}.${d} ${S}</div>`))}else a.push(y)}s=a.join(`
`),s=s.replace(/\n/g,"<br>"),s+=n;const h=`<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Query Result</title>
  <style>
    @page {
      margin: 2.0cm 1.2cm;
    }
    @media print {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 11pt;
        line-height: 1.6;
        margin: 0;
        color: #000;
      }
      h1 { font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 0.2cm; margin-top: 0.5cm; }
      h2 { font-size: 14pt; margin-top: 0.1cm; color: #333; }
      h3 { font-size: 12pt; margin-top: 0cm; color: #555; }
      .no-print { display: none; }
      .h1-bold { 
        font-size: 18pt; 
        font-weight: bold; 
        margin-top: 0.4cm; 
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      .h2-bold { 
        font-size: 15pt; 
        font-weight: bold; 
        margin-top: 0.2cm; 
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 13pt; 
        font-weight: bold; 
        margin-top: 0.15cm; 
        margin-bottom: 0.05cm;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.2cm;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.15cm;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 8px 12px;
        margin-top: 0.15cm;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format */
      query-h1 {
        display: block;
        font-size: 18pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      query-h2 {
        display: block;
        font-size: 15pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.15cm;
        margin-bottom: 0.05cm;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 0.3cm;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 0.3cm;
      }
    }
    @media screen {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        max-width: 800px;
        margin: 2cm auto;
        padding: 1cm;
        line-height: 1.6;
      }
      .print-button {
        display: block;
        margin: 1cm auto;
        padding: 10px 30px;
        font-size: 14pt;
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .print-button:hover {
        background: #45a049;
      }
      .h1-bold { 
        font-size: 20pt; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      .h2-bold { 
        font-size: 16pt; 
        font-weight: bold; 
        margin-top: 15px; 
        margin-bottom: 8px;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 14pt; 
        font-weight: bold; 
        margin-top: 12px; 
        margin-bottom: 6px;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 16px;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 12px;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 10px 14px;
        margin-top: 12px;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format - screen view */
      query-h1 {
        display: block;
        font-size: 20pt;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      query-h2 {
        display: block;
        font-size: 16pt;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 14pt;
        font-weight: bold;
        margin-top: 12px;
        margin-bottom: 6px;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 8px;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 8px;
      }
      /* Clean print format styles */
      .print-document-title {
        font-size: 16pt;
        font-weight: bold;
        margin-top: 0;
        margin-bottom: 0.4cm;
        color: #000;
        border-bottom: 2px solid #000;
        padding-bottom: 0.15cm;
        text-align: center;
      }
      .print-section-intro {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
        font-style: italic;
      }
      .print-section-title {
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #000;
        border-bottom: 1px solid #333;
        padding-bottom: 0.1cm;
      }
      .print-section-heading {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
      }
      .print-section-subheading {
        font-size: 11pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #555;
      }
      .print-references-section {
        margin-top: 0.8cm;
        padding-top: 0.3cm;
        border-top: 1px solid #333;
      }
      .print-references-header {
        font-size: 13pt;
        font-weight: bold;
        margin-bottom: 0.2cm;
        color: #000;
      }
      .print-references-list {
        padding-left: 0.3cm;
      }
      .print-reference-item {
        margin-bottom: 0.15cm;
        font-size: 10pt;
      }
      .print-ref-number {
        font-weight: bold;
        margin-right: 0.2cm;
      }
    }
  </style>
</head>
<body>
  <div class="answer">${s}</div>
</body>
</html>`,F=new Blob([h],{type:"text/html"}),u=URL.createObjectURL(F);if(!window.open(u,"_blank")){alert("Please allow popups to print the answer."),URL.revokeObjectURL(u);return}}function co(){var e,t,n,o;(e=l("queryFileInput"))==null||e.addEventListener("change",uo),(t=l("runQueryFileBtn"))==null||t.addEventListener("click",fo),(n=l("exportQueryFilePdfBtn"))==null||n.addEventListener("click",s=>lo(s)),(o=l("queryFileText"))==null||o.addEventListener("input",()=>{const s=l("exportQueryFilePdfBtn");s&&(s.style.display="none")})}function uo(){var t;const e=l("queryFileInput");(t=e==null?void 0:e.files)!=null&&t.length&&(Array.from(e.files).forEach(n=>Bt(n)),St(),e.value="")}function St(){me(ke(),{containerId:"querySelectedFilesList",onRemove:e=>{Mt(e),St()},emptyText:"Selected files:"})}async function po(e,t=ze(),n,o){const{sendQuery:s}=await ro(async()=>{const{sendQuery:c}=await Promise.resolve().then(()=>rn);return{sendQuery:c}},void 0,import.meta.url),i=new AbortController,r=t.ultra_comprehensive?9e5:t.detailed?6e5:3e5,d=setTimeout(()=>i.abort(),r);try{const c=await s({message:e,top_k:t.top_k,detailed:t.detailed,ultra_comprehensive:t.ultra_comprehensive},i.signal);clearTimeout(d);const f=c.response||c.answer||JSON.stringify(c);se=f,n&&(n.innerHTML=ye(f)),o&&(o.style.display="inline-block")}catch(c){clearTimeout(d),c instanceof Error&&c.name==="AbortError"?n&&(n.textContent="⏰ Query timed out. The LLM is taking too long."):n&&(n.textContent=`❌ Error: ${c instanceof Error?c.message:"Unknown error"}`)}}async function We(e,t,n=ze(),o,s){const i=new AbortController,r=n.ultra_comprehensive?3e5:n.detailed?24e4:12e4,d=setTimeout(()=>i.abort(),r);try{o&&(o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>Querying with ${t.length} existing file(s)...`);const c=await Ie({message:e,filenames:t,top_k:n.top_k,detailed:n.detailed,ultra_comprehensive:n.ultra_comprehensive},i.signal);if(clearTimeout(d),c.response||c.answer){const f=c.response||c.answer||"",h=c.sources||c.source_documents;Array.isArray(h)?B=h.map(u=>typeof u=="string"?u:u&&typeof u=="object"?u.filename||u.doc_id||u.name||JSON.stringify(u):String(u)):B=[];let F=f;B.length>0&&(F+=`


## References

`,B.forEach((u,w)=>{F+=`${w+1}. ${u}
`})),se=F,o&&(o.innerHTML=ye(F)),s&&(s.style.display="inline-block")}else c.detail?o&&(o.textContent=`❌ Error: ${c.detail}`):o&&(o.textContent=JSON.stringify(c,null,2))}catch(c){clearTimeout(d),c instanceof Error&&c.name==="AbortError"?o&&(o.textContent="⏰ Query timed out after 5 minutes."):o&&(o.textContent=`❌ Error: ${c instanceof Error?c.message:"Unknown error"}`)}}async function fo(){var c;const e=(c=l("queryFileText"))==null?void 0:c.value.trim();let t=ke();if(!t.length||!e){alert("Please upload file(s) and enter a question");return}const n=ze();G(!0);const o=l("queryFileAnswer"),s=l("exportQueryFilePdfBtn");console.log("[QueryFile] Starting query, exportBtn:",s),V("queryFileResult",!0),s&&(s.style.display="none",console.log("[QueryFile] Button hidden"));const i=n.ultra_comprehensive,a=n.detailed&&!i,r=i?"3-5 min":a?"2-4 min":"30-60 sec";let d="";i?d="Retrieving 40 chunks + Generating ultra-extensive (3000+ words) answer...":a?d="Retrieving 30 chunks + Generating comprehensive (2000+ words) answer...":n.top_k===10?d="Retrieving 10 chunks + ~ 1000 words Generating standard answer...":d="Retrieving 20 chunks + ~1500 words Generating standard answer...",o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>${d}<br>Estimated time: ${r}<br><small>Please wait, do not close or refresh the page</small>`;try{const{duplicates:f,newFiles:h,duplicateDocIds:F}=await _e(t);if(f.length>0)if(t.length===1){if(!confirm(`File "${L(f[0])}" already exists. Click OK to overwrite, Cancel to use existing file.`)){o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>📄 Using existing file...`,Qe(),await We(e,f,n,o,s),G(!1);return}}else{const k=L(f.join(", ")),p=L(h.map($=>$.name).join(", "));if(!(h.length>0?confirm(`Found ${f.length} existing: ${k}

New: ${p}

Click OK to upload all, Cancel to skip duplicates and use existing files.`):confirm(`All ${f.length} exist: ${k}

Click OK to overwrite all, Cancel to use existing files.`))){if(h.length===0){o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>📄 Using ${f.length} existing file(s)...`,Qe(),await We(e,f,n,o,s),G(!1);return}t=h}}if(t.length===0&&f.length===0){await po(e,n,o,s),G(!1);return}const u=[];for(let k=0;k<t.length;k++){const p=t[k];o.textContent=`📤 Uploading ${k+1}/${t.length}: ${L(p.name)}...`;try{const x=await fe(p);x.doc_id&&u.push({filename:p.name,doc_id:x.doc_id})}catch(x){console.error(`Upload failed for ${p.name}:`,x)}}if(u.length===0){o.textContent="❌ Upload failed. No files were uploaded.",G(!1);return}await mo(u,o);const w=u.map(k=>k.filename),y=F&&t.length<ke().length?f.filter(k=>!w.includes(k)):[],b=[...w,...y];o.innerHTML=`<span class="spinner"></span> <strong>${n.label} Mode</strong><br>Querying with ${b.length} file(s)...`;const m=new AbortController,g=i?3e5:n.detailed?24e4:12e4,S=setTimeout(()=>m.abort(),g),T=await Ie({message:e,filenames:b,top_k:n.top_k,detailed:n.detailed,ultra_comprehensive:n.ultra_comprehensive},m.signal);if(clearTimeout(S),T.response||T.answer){const k=T.response||T.answer||"",p=T.sources||T.source_documents;console.log("[QueryFile] Raw sources:",p),Array.isArray(p)?B=p.map(v=>typeof v=="string"?v:v&&typeof v=="object"?v.filename||v.doc_id||v.name||JSON.stringify(v):String(v)):B=[],console.log("[QueryFile] Processed sources:",B);let x=k;B.length>0?(x+=`


## References

`,B.forEach((v,I)=>{x+=`${I+1}. ${v}
`})):typeof p=="number"&&p>0&&(x+=`


## References

`,x+=`This answer was generated from ${p} source documents.
`,x+="(Source filenames not available from backend API.)"),se=x,o.innerHTML=ye(x);const $=l("queryFileSources");if($&&B.length>0){let v="";const I=new Set,ve=k.match(/\[(\d+)\]|Source\s+(\d+)/gi);ve&&ve.forEach(A=>{const D=A.match(/\d+/);D&&I.add(parseInt(D[0],10))});const xe=Array.from(I).sort((A,D)=>A-D).map(A=>B[A-1]).filter(A=>A!==void 0);xe.length>0&&(v+='<div class="sources-section references-section">',v+='<div class="sources-header references-header">📚 References</div>',xe.forEach((A,D)=>{v+=`<div class="source-item references-item">${D+1}. ${L(A)}</div>`}),v+="</div>"),v+='<div class="sources-section verification-section">',v+='<div class="sources-header verification-header">🔍 Sources (for Verification)</div>',B.forEach((A,D)=>{v+=`<div class="source-item verification-item">${D+1}. ${L(A)}</div>`}),v+="</div>",$.innerHTML=v}else $&&($.innerHTML='<div class="source-item">No sources available</div>');s&&(s.style.display="inline-block",console.log("[QueryFile] Button shown"))}else T.detail?o.textContent=`❌ Error: ${T.detail}`:o.textContent=JSON.stringify(T,null,2)}catch(f){console.error("Query with file failed:",f),f instanceof Error&&f.name==="AbortError"?o.textContent="⏰ Query timed out after 5 minutes.":o.textContent=`❌ Error: ${f instanceof Error?f.message:"Unknown error"}`}finally{G(!1)}}async function mo(e,t){let n=!1,o=0;for(;!n&&o<30;){const s=ln(o,1e3,5e3);await new Promise(a=>setTimeout(a,s)),o++;let i=0;for(const a of e){const r=await it(a.doc_id);(r!=null&&r.indexed||r!=null&&r.ready||r!=null&&r.chunks&&r.chunks>0)&&i++}if(t.textContent=`⏳ Indexing... (${o}s) - ${i}/${e.length} ready`,i===e.length){n=!0;break}}n?t.textContent="✅ Files indexed! Now querying...":t.textContent="⚠️ Indexing in progress, but proceeding with query..."}function go(){return`
    <div id="queryfile" class="tab-content card" role="tabpanel" aria-labelledby="tab-queryfile">
      <h2>🔗 Query with File(s)</h2>
      
      
      <h3>Upload Document(s)</h3>
      <label for="queryFileInput" class="sr-only">Select files to upload</label>
      <input type="file" id="queryFileInput" accept=".txt,.md,.pdf,.doc,.docx" multiple aria-describedby="queryFileInput-hint">
      <p id="queryFileInput-hint" class="hint">You can select multiple files (Ctrl+Click or Cmd+Click)</p>
      
      <div id="querySelectedFilesList" class="file-list" style="display: none;"></div>
      
      <h3>Question</h3>
      <label for="queryFileText" class="sr-only">Enter your question about the uploaded file</label>
      <textarea id="queryFileText" placeholder="Ask a question about the uploaded file and knowledge graph..." rows="3" aria-describedby="queryFileText-hint"></textarea>
      <p id="queryFileText-hint" class="hint">Type your question about the uploaded document</p>
      
      <h3 id="queryFileDetailLabel">Answer Detail Level</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryFileDetailLabel">
        <label class="radio-option" title="Quick answer using 10 chunks">
          <input type="radio" name="queryFileDetail" value="quick"> ⚡ Quick
        </label>
        <label class="radio-option" title="Balanced answer using 20 chunks">
          <input type="radio" name="queryFileDetail" value="balanced" checked> 📊 Balanced
        </label>
        <label class="radio-option" title="Comprehensive answer">
          <input type="radio" name="queryFileDetail" value="comprehensive"> 📚 Comprehensive
        </label>
        <label class="radio-option" title="Ultra comprehensive - Extended wait">
          <input type="radio" name="queryFileDetail" value="ultra"> 🎓 Ultra Deep
        </label>
      </div>
      
      <button id="runQueryFileBtn" class="btn" aria-label="Submit query with uploaded files">🔍 Query with File</button>
      
      <div id="queryFileResult" style="display: none;" aria-live="polite">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">

          <button type="button" id="exportQueryFilePdfBtn" class="btn" style="padding: 6px 12px; font-size: 13px; background: var(--bg-tertiary, #333); border: 1px solid var(--border-color, #444); display: none;">
            🖨️ Print
          </button>
        </div>
        <div id="queryFileAnswer" class="result-box"></div>
        <div id="queryFileSources" class="sources-box" style="margin-top: 20px;"></div>
      </div>
    </div>
  `}function ho(e,t="info",n={}){const{duration:o=4e3,dismissible:s=!0}=n;document.querySelectorAll(`.toast-container .toast.${t}`).forEach(c=>c.remove());let a=document.querySelector(".toast-container");a||(a=document.createElement("div"),a.className="toast-container",a.setAttribute("role","region"),a.setAttribute("aria-label","Notifications"),a.setAttribute("aria-live","polite"),document.body.appendChild(a));const r=document.createElement("div");r.className=`toast toast-${t}`,r.setAttribute("role","alert"),r.setAttribute("aria-live","assertive");const d={success:"✅",error:"❌",warning:"⚠️",info:"ℹ️"};if(r.innerHTML=`
    <span class="toast-icon">${d[t]}</span>
    <span class="toast-message">${bo(e)}</span>
    ${s?'<button class="toast-close" aria-label="Dismiss notification">×</button>':""}
  `,s){const c=r.querySelector(".toast-close");c==null||c.addEventListener("click",()=>Je(r))}return a.appendChild(r),requestAnimationFrame(()=>{r.classList.add("toast-show")}),o>0&&setTimeout(()=>Je(r),o),r.setAttribute("tabindex","-1"),r.focus(),r}function Je(e){e.classList.remove("toast-show"),e.classList.add("toast-hide"),e.addEventListener("transitionend",()=>{e.remove();const t=document.querySelector(".toast-container");t&&t.children.length===0&&t.remove()},{once:!0})}function Ve(e,t){ho(e,"error",t)}function bo(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}function yo(){window.onerror=(e,t,n,o,s)=>{const i=s instanceof Error?`${s.message}
${s.stack}`:String(e);console.error("🚨 Global Error:",{message:i,source:t,lineno:n,colno:o,error:s});const a=s instanceof Error?s.message:"An unexpected error occurred";return Ve(`Error: ${a}`,{duration:6e3}),!1},window.onunhandledrejection=e=>{const t=e.reason,n=t instanceof Error?`${t.message}
${t.stack}`:String(t);console.error("🚨 Unhandled Promise Rejection:",{reason:n,promise:e.promise});const o=t instanceof Error?t.message:"An unexpected error occurred";Ve(`Async Error: ${o}`,{duration:6e3})},console.log("✅ Global error handlers initialized")}function vo(){if(document.getElementById("toast-styles"))return;const e=document.createElement("style");e.id="toast-styles",e.textContent=`
    .toast-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .toast {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-radius: 8px;
      background: rgba(30, 30, 40, 0.95);
      color: #fff;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(10px);
      opacity: 0;
      transform: translateX(100%);
      transition: opacity 0.3s ease, transform 0.3s ease;
    }
    
    .toast.toast-show {
      opacity: 1;
      transform: translateX(0);
    }
    
    .toast.toast-hide {
      opacity: 0;
      transform: translateX(100%);
    }
    
    .toast-icon {
      font-size: 18px;
      flex-shrink: 0;
    }
    
    .toast-message {
      flex: 1;
      font-size: 14px;
      line-height: 1.4;
      word-break: break-word;
    }
    
    .toast-close {
      background: none;
      border: none;
      color: rgba(255, 255, 255, 0.6);
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
      transition: color 0.2s;
      flex-shrink: 0;
    }
    
    .toast-close:hover {
      color: #fff;
    }
    
    .toast-success {
      border-left: 4px solid #4caf50;
    }
    
    .toast-error {
      border-left: 4px solid #f44336;
    }
    
    .toast-warning {
      border-left: 4px solid #ff9800;
    }
    
    .toast-info {
      border-left: 4px solid #00d4ff;
    }
    
    @media (max-width: 480px) {
      .toast-container {
        left: 10px;
        right: 10px;
        max-width: none;
      }
    }
  `,document.head.appendChild(e)}function xo(){vo(),yo()}function wo(){const e=l("uploadActivityIndicator");if(!e)return;const t=Wt();e.style.display=t?"flex":"none"}let pe=null;function ko(){pe||(pe=window.setInterval(wo,1e3))}function $o(){console.log("🧠 LightRAG WebUI initializing..."),xo(),So(),Gt(),Kt("ingestProgress"),_n(),Yn(),co(),Jt(),Eo(),Fo(),It(setInterval(z,Et)),ko(),window.addEventListener("beforeunload",()=>{Dt(),Cn(),pe&&clearInterval(pe)}),console.log("✅ LightRAG WebUI ready")}function So(){const e=l("app");e&&(e.innerHTML=`
    <div class="header">
      <div class="header-main">
        <h1>🧠 LightRAG Knowledge Graph</h1>
        <div id="uploadActivityIndicator" class="upload-activity" style="display: none;">
          <span class="upload-spinner">⏳</span>
          <span class="upload-text">Uploading...</span>
          <span class="upload-hint">(Query available but may be slower)</span>
        </div>
      </div>
      <p class="header-hint">
        💡 If queries fail, try refreshing the page (F5) or check browser console (F12).
      </p>
    </div>
    
    <div id="stats-container"></div>
    
    <nav class="tabs" role="tablist" aria-label="Main navigation">
      <button class="tab active" data-tab="ingest" role="tab" aria-selected="true" aria-controls="ingest" id="tab-ingest">📥 Ingest</button>
      <button class="tab" data-tab="query" role="tab" aria-selected="false" aria-controls="query" id="tab-query">🔍 Query</button>
      <button class="tab" data-tab="queryfile" role="tab" aria-selected="false" aria-controls="queryfile" id="tab-queryfile">🔗 Query+File</button>
      <button class="tab" data-tab="config" role="tab" aria-selected="false" aria-controls="config" id="tab-config">⚙️ Config</button>
    </nav>
    
    <main id="tab-content">
      ${Vn()}
      ${oo()}
      ${go()}
      ${nn()}
    </main>
  `,l("stats-container").innerHTML=`
    <div class="card">
      <h2>📊 Knowledge Graph Stats</h2>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs">0</div>
          <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities">0</div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations">0</div>
          <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks">0</div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn" aria-label="Refresh statistics">🔄 Refresh Stats</button>
    </div>
  `)}function Eo(){const e=document.querySelectorAll(".tab");e.forEach(t=>{t.addEventListener("click",()=>{const n=t.getAttribute("data-tab");n&&(e.forEach(o=>{o.classList.remove("active"),o.setAttribute("aria-selected","false")}),t.classList.add("active"),t.setAttribute("aria-selected","true"),Ft(n))})})}function Fo(){document.addEventListener("keydown",e=>{var t;if(e.key==="Tab"&&document.body.classList.add("keyboard-mode"),e.key==="Escape"&&document.activeElement instanceof HTMLElement&&document.activeElement.blur(),(e.key==="Enter"||e.key===" ")&&((t=document.activeElement)!=null&&t.matches('button, [role="button"]'))){const n=document.activeElement;n.disabled||(n.classList.add("keyboard-activated"),setTimeout(()=>n.classList.remove("keyboard-activated"),150))}}),document.addEventListener("mousedown",()=>{document.body.classList.remove("keyboard-mode")}),document.addEventListener("click",e=>{var n;const t=e.target;t.classList.contains("toast-close")&&((n=t.closest(".toast"))==null||n.remove())},{capture:!0}),console.log("✅ Keyboard navigation initialized")}document.addEventListener("DOMContentLoaded",$o);
//# sourceMappingURL=index-Dh7ZdrP9.js.map
