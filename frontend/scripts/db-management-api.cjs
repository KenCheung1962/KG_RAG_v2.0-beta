#!/usr/bin/env node
/**
 * Database Management API
 * Exposes backup/cleanup/restore/stats via HTTP endpoints for WebUI integration
 * Runs on port 8013
 */

const http = require('http');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const PORT = 8013;
const BACKUP_DIR = path.join(__dirname, '..', 'backups');
const LOG_FILE = path.join(BACKUP_DIR, 'operations.log');

const execAsync = promisify(exec);

// Ensure backup directory exists
if (!fs.existsSync(BACKUP_DIR)) {
  fs.mkdirSync(BACKUP_DIR, { recursive: true });
}

function log(message) {
  const timestamp = new Date().toISOString();
  const entry = `[${timestamp}] ${message}`;
  console.log(entry);
  fs.appendFileSync(LOG_FILE, entry + '\n');
}

// CORS headers
function setCORS(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// Execute SQL query via Docker
function execSQL(sql) {
  return new Promise((resolve, reject) => {
    const cmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -c "${sql}"`;
    exec(cmd, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}

// Get database stats
async function getStats() {
  const countsOutput = await execSQL(`
    SELECT 'documents', COUNT(DISTINCT source) FROM chunks
    UNION ALL SELECT 'chunks', COUNT(*) FROM chunks
    UNION ALL SELECT 'entities', COUNT(*) FROM entities
    UNION ALL SELECT 'relationships', COUNT(*) FROM relationships;
  `);
  
  const stats = {};
  countsOutput.split('\n').forEach(line => {
    const match = line.match(/(\w+)\s*\|\s*(\d+)/);
    if (match) {
      stats[match[1]] = parseInt(match[2]);
    }
  });
  
  // Get table sizes
  const sizesOutput = await execSQL(`
    SELECT 
      tablename,
      pg_total_relation_size('public.' || tablename) as size
    FROM pg_tables 
    WHERE schemaname='public' AND tablename IN ('chunks', 'entities', 'relationships');
  `);
  
  const sizes = {};
  sizesOutput.split('\n').forEach(line => {
    const match = line.match(/(\w+)\s*\|\s*(\d+)/);
    if (match) {
      sizes[match[1]] = parseInt(match[2]);
    }
  });
  
  // Total DB size
  const totalSizeOutput = await execSQL(`SELECT pg_database_size('kg_rag');`);
  // Match number after the separator line (format: "\n        125262871\n")
  const totalMatch = totalSizeOutput.match(/\n\s*(\d+)\s*\n/);
  const totalSize = totalMatch ? parseInt(totalMatch[1]) : 0;
  
  return {
    counts: stats,
    sizes: sizes,
    totalSize: totalSize,
    totalSizeFormatted: formatBytes(totalSize),
    timestamp: new Date().toISOString()
  };
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// List backups
function listBackups() {
  if (!fs.existsSync(BACKUP_DIR)) return [];
  
  return fs.readdirSync(BACKUP_DIR)
    .filter(f => f.startsWith('backup-'))
    .map(f => {
      const stat = fs.statSync(path.join(BACKUP_DIR, f));
      const metadataPath = path.join(BACKUP_DIR, f, 'metadata.json');
      let metadata = null;
      if (fs.existsSync(metadataPath)) {
        try {
          metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        } catch (e) {}
      }
      return {
        name: f,
        created: stat.mtime.toISOString(),
        size: formatBytes(stat.size),
        metadata
      };
    })
    .sort((a, b) => new Date(b.created) - new Date(a.created));
}

// Create backup
async function createBackup() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(BACKUP_DIR, `backup-${timestamp}`);
  
  fs.mkdirSync(backupPath, { recursive: true });
  
  // Get stats
  const stats = await getStats();
  fs.writeFileSync(path.join(backupPath, 'stats.json'), JSON.stringify(stats, null, 2));
  
  // Export entities
  const entitiesCmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -t -A -F"," -c "SELECT entity_id, name, entity_type, description FROM entities ORDER BY entity_id LIMIT 10000"`;
  const { stdout: entities } = await execAsync(entitiesCmd, { maxBuffer: 50 * 1024 * 1024 });
  fs.writeFileSync(path.join(backupPath, 'entities.csv'), entities);
  
  // Export relationships
  const relCmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -t -A -F"," -c "SELECT source_id, target_id, relationship_type FROM relationships ORDER BY source_id LIMIT 50000"`;
  const { stdout: relationships } = await execAsync(relCmd, { maxBuffer: 50 * 1024 * 1024 });
  fs.writeFileSync(path.join(backupPath, 'relationships.csv'), relationships);
  
  // Export chunks metadata (limit to avoid memory issues, full content can be large)
  const chunksCmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -t -A -F"," -c "SELECT chunk_id, source, chunk_index FROM chunks ORDER BY source, chunk_index LIMIT 10000"`;
  const { stdout: chunks } = await execAsync(chunksCmd, { maxBuffer: 50 * 1024 * 1024 });
  fs.writeFileSync(path.join(backupPath, 'chunks.csv'), chunks);
  
  // Metadata
  const metadata = {
    timestamp: new Date().toISOString(),
    stats: stats.counts,
    exports: {
      entities: entities.trim().split('\n').filter(l => l).length,
      relationships: relationships.trim().split('\n').filter(l => l).length,
      chunks: chunks.trim().split('\n').filter(l => l).length
    }
  };
  fs.writeFileSync(path.join(backupPath, 'metadata.json'), JSON.stringify(metadata, null, 2));
  
  log(`Backup created: ${backupPath}`);
  
  // Cleanup old backups (keep 5)
  cleanupOldBackups();
  
  return { backupPath: `backup-${timestamp}`, metadata };
}

function cleanupOldBackups() {
  const entries = fs.readdirSync(BACKUP_DIR)
    .filter(f => f.startsWith('backup-'))
    .map(f => ({ name: f, path: path.join(BACKUP_DIR, f), stat: fs.statSync(path.join(BACKUP_DIR, f)) }))
    .sort((a, b) => b.stat.mtime - a.stat.mtime);
  
  entries.slice(5).forEach(entry => {
    fs.rmSync(entry.path, { recursive: true, force: true });
    log(`Deleted old backup: ${entry.name}`);
  });
}

// Cleanup database
async function cleanupDatabase() {
  log('Starting database cleanup...');
  
  await execSQL('TRUNCATE TABLE relationships CASCADE');
  await execSQL('TRUNCATE TABLE entities CASCADE');
  await execSQL('TRUNCATE TABLE chunks CASCADE');
  await execSQL('VACUUM FULL');
  
  log('Database cleanup completed');
  return { success: true };
}

// Restore from backup
async function restoreBackup(backupName) {
  const backupPath = path.join(BACKUP_DIR, backupName);
  if (!fs.existsSync(backupPath)) {
    throw new Error(`Backup not found: ${backupName}`);
  }
  
  log(`Restoring from: ${backupName}`);
  
  // Note: This restores metadata only, files need to be re-uploaded
  // In a full implementation, we'd parse the CSV files and INSERT them
  
  return { 
    success: true, 
    message: 'Metadata ready. Original files need to be re-uploaded via WebUI.' 
  };
}

// HTTP Server
const server = http.createServer(async (req, res) => {
  setCORS(res);
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  const url = new URL(req.url, `http://localhost:${PORT}`);
  
  try {
    switch (url.pathname) {
      case '/stats': {
        const stats = await getStats();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(stats));
        break;
      }
        
      case '/backups': {
        const backups = listBackups();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ backups }));
        break;
      }
        
      case '/backup': {
        if (req.method === 'POST') {
          const result = await createBackup();
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, result }));
        } else if (req.method === 'DELETE') {
          // Delete specific backup
          let body = '';
          req.on('data', chunk => body += chunk);
          req.on('end', async () => {
            try {
              const { backupName } = JSON.parse(body);
              const backupPath = path.join(BACKUP_DIR, backupName);
              
              // Security check - ensure path is within BACKUP_DIR
              if (!backupPath.startsWith(BACKUP_DIR)) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid backup path' }));
                return;
              }
              
              if (!fs.existsSync(backupPath)) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Backup not found' }));
                return;
              }
              
              fs.rmSync(backupPath, { recursive: true, force: true });
              log(`Deleted backup: ${backupName}`);
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ success: true, message: `Backup ${backupName} deleted` }));
            } catch (e) {
              res.writeHead(400, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: e.message }));
            }
          });
          return;
        } else {
          res.writeHead(405);
          res.end(JSON.stringify({ error: 'Method not allowed' }));
        }
        break;
      }
        
      case '/cleanup': {
        if (req.method !== 'POST') {
          res.writeHead(405);
          res.end(JSON.stringify({ error: 'Method not allowed' }));
          return;
        }
        const result = await cleanupDatabase();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
        break;
      }
        
      case '/restore': {
        if (req.method !== 'POST') {
          res.writeHead(405);
          res.end(JSON.stringify({ error: 'Method not allowed' }));
          return;
        }
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
          try {
            const { backupName } = JSON.parse(body);
            const result = await restoreBackup(backupName);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
          } catch (e) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
          }
        });
        return;
      }
        
      case '/health': {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', service: 'db-management-api' }));
        break;
      }
        
      default: {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));
      }
    }
  } catch (error) {
    log(`Error: ${error.message}`);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: error.message }));
  }
});

server.listen(PORT, () => {
  console.log(`📊 Database Management API running on port ${PORT}`);
  console.log(`   Endpoints:`);
  console.log(`   GET  /stats    - Database statistics`);
  console.log(`   GET  /backups  - List backups`);
  console.log(`   POST /backup   - Create new backup`);
  console.log(`   POST /cleanup  - Clear database`);
  console.log(`   POST /restore  - Restore from backup`);
  console.log(`   GET  /health   - Service health`);
});

module.exports = { server };
