#!/usr/bin/env node
/**
 * Database Backup Utility
 * Exports PostgreSQL database to JSON files for safekeeping
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const BACKUP_DIR = path.join(__dirname, '..', 'backups');
const PGVECTOR_API_URL = 'http://localhost:8002';
const API_KEY = 'static-internal-key';

async function fetchAPI(endpoint) {
  return new Promise((resolve, reject) => {
    const req = http.get(`${PGVECTOR_API_URL}${endpoint}`, {
      headers: { 'X-API-Key': API_KEY }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => reject(new Error('Timeout')));
  });
}

async function exportDatabase() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(BACKUP_DIR, `backup-${timestamp}`);
  
  console.log('📦 Starting database backup...');
  console.log(`   Backup folder: ${backupPath}`);
  
  // Create backup directory
  if (!fs.existsSync(backupPath)) {
    fs.mkdirSync(backupPath, { recursive: true });
  }
  
  try {
    // Get health/stats first
    console.log('   Fetching database stats...');
    const stats = await fetchAPI('/health');
    fs.writeFileSync(
      path.join(backupPath, 'stats.json'),
      JSON.stringify(stats, null, 2)
    );
    console.log(`   ✓ Stats: ${stats.documents_count} docs, ${stats.entities_count} entities`);
    
    // Export documents (using direct query via proxy)
    console.log('   Exporting documents list...');
    const { exec } = require('child_process');
    
    const exportTable = (tableName, query) => new Promise((resolve, reject) => {
      const cmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -t -A -F"," -c "${query}"`;
      exec(cmd, { maxBuffer: 100 * 1024 * 1024 }, (error, stdout, stderr) => {
        if (error) {
          console.warn(`   ⚠️  ${tableName} export warning: ${error.message}`);
          resolve([]);
        } else {
          const lines = stdout.trim().split('\n').filter(l => l);
          resolve(lines);
        }
      });
    });
    
    // Export chunks (document sources)
    console.log('   Exporting chunks metadata...');
    const chunks = await exportTable('chunks', 
      "SELECT chunk_id, source, chunk_index FROM chunks ORDER BY source, chunk_index LIMIT 10000"
    );
    
    // Export entities
    console.log('   Exporting entities...');
    const entities = await exportTable('entities',
      "SELECT entity_id, name, entity_type, description FROM entities ORDER BY entity_id LIMIT 10000"
    );
    
    // Export relationships
    console.log('   Exporting relationships...');
    const relationships = await exportTable('relationships',
      "SELECT source_id, target_id, relationship_type FROM relationships ORDER BY source_id LIMIT 50000"
    );
    
    // Save metadata
    const metadata = {
      timestamp: new Date().toISOString(),
      stats: {
        documents: stats.documents_count,
        entities: stats.entities_count,
        relationships: stats.relationships_count,
        chunks: stats.chunks_count
      },
      exports: {
        chunks_count: chunks.length,
        entities_count: entities.length,
        relationships_count: relationships.length
      }
    };
    
    fs.writeFileSync(path.join(backupPath, 'metadata.json'), JSON.stringify(metadata, null, 2));
    fs.writeFileSync(path.join(backupPath, 'chunks.csv'), chunks.join('\n'));
    fs.writeFileSync(path.join(backupPath, 'entities.csv'), entities.join('\n'));
    fs.writeFileSync(path.join(backupPath, 'relationships.csv'), relationships.join('\n'));
    
    // Create latest symlink
    const latestLink = path.join(BACKUP_DIR, 'latest');
    try {
      fs.unlinkSync(latestLink);
    } catch (e) {}
    try {
      fs.symlinkSync(backupPath, latestLink);
    } catch (e) {
      console.log('   ⚠️  Could not create symlink (Windows?)');
    }
    
    console.log('\n✅ Backup completed successfully!');
    console.log(`   Location: ${backupPath}`);
    console.log(`   Chunks: ${chunks.length}`);
    console.log(`   Entities: ${entities.length}`);
    console.log(`   Relationships: ${relationships.length}`);
    
    // Cleanup old backups (keep last 5)
    cleanupOldBackups();
    
    return backupPath;
    
  } catch (error) {
    console.error('\n❌ Backup failed:', error.message);
    throw error;
  }
}

function cleanupOldBackups() {
  try {
    const entries = fs.readdirSync(BACKUP_DIR)
      .filter(f => f.startsWith('backup-'))
      .map(f => ({
        name: f,
        path: path.join(BACKUP_DIR, f),
        stat: fs.statSync(path.join(BACKUP_DIR, f))
      }))
      .sort((a, b) => b.stat.mtime - a.stat.mtime);
    
    if (entries.length > 5) {
      console.log(`\n🧹 Cleaning up old backups (keeping 5)...`);
      entries.slice(5).forEach(entry => {
        fs.rmSync(entry.path, { recursive: true, force: true });
        console.log(`   Deleted: ${entry.name}`);
      });
    }
  } catch (e) {
    console.log('   ⚠️  Cleanup skipped:', e.message);
  }
}

// Main
if (require.main === module) {
  exportDatabase().catch(() => process.exit(1));
}

module.exports = { exportDatabase };
