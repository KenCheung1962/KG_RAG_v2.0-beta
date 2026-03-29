/**
 * PGVector Stats Proxy
 * Uses docker exec to query pgvector and serve stats via HTTP
 * 
 * Usage: node scripts/pgvector-proxy.cjs
 * Endpoint: http://localhost:3001/stats
 */

const { exec } = require('child_process');
const http = require('http');
const util = require('util');

const PORT = 8012;
const execPromise = util.promisify(exec);

async function queryStats() {
  const sql = `
    SELECT 'entities' as item, COUNT(*) as count FROM entities
    UNION ALL
    SELECT 'relationships', COUNT(*) FROM relationships
    UNION ALL
    SELECT 'chunks', COUNT(*) FROM chunks
    UNION ALL
    SELECT 'documents', COUNT(DISTINCT source) FROM chunks
  `;
  
  try {
    const { stdout } = await execPromise(
      `docker exec kg_rag_postgres psql -U postgres -d kg_rag -t -c "${sql}"`
    );
    
    // Parse the output
    const stats = {};
    const lines = stdout.trim().split('\n');
    
    for (const line of lines) {
      const parts = line.trim().split('|');
      if (parts.length === 2) {
        const key = parts[0].trim();
        const value = parseInt(parts[1].trim(), 10);
        stats[key] = value;
      }
    }
    
    return stats;
  } catch (error) {
    console.error('Docker query error:', error);
    throw error;
  }
}

const server = http.createServer(async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  res.setHeader('Content-Type', 'application/json');
  
  if (req.url === '/stats' && req.method === 'GET') {
    try {
      const stats = await queryStats();
      res.writeHead(200);
      res.end(JSON.stringify(stats));
    } catch (error) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: error.message }));
    }
  } else if (req.url === '/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'ok' }));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

server.listen(PORT, () => {
  console.log(`PGVector stats proxy running on http://localhost:${PORT}`);
  console.log('Endpoints:');
  console.log(`  - http://localhost:${PORT}/stats`);
  console.log(`  - http://localhost:${PORT}/health`);
});
