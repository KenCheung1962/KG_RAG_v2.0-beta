#!/usr/bin/env node
/**
 * Database Cleanup Utility
 * Clears database tables after backup to free space
 */

const { exec } = require('child_process');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function query(question) {
  return new Promise(resolve => rl.question(question, resolve));
}

function execSQL(sql) {
  return new Promise((resolve, reject) => {
    const cmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -c "${sql}"`;
    exec(cmd, (error, stdout, stderr) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}

function getTableCounts() {
  return new Promise((resolve, reject) => {
    const cmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -c "
      SELECT 'chunks', COUNT(*) FROM chunks
      UNION ALL SELECT 'entities', COUNT(*) FROM entities
      UNION ALL SELECT 'relationships', COUNT(*) FROM relationships;
    "`;
    exec(cmd, (error, stdout) => {
      if (error) reject(error);
      else {
        const counts = {};
        stdout.split('\n').forEach(line => {
          const match = line.match(/(chunks|entities|relationships)\s*\|\s*(\d+)/);
          if (match) counts[match[1]] = parseInt(match[2]);
        });
        resolve(counts);
      }
    });
  });
}

async function cleanupDatabase(options = {}) {
  const { skipConfirm = false, vacuum = true } = options;
  
  console.log('🧹 Database Cleanup Utility\n');
  
  // Show current counts
  const counts = await getTableCounts();
  console.log('Current database state:');
  console.log(`   Chunks: ${counts.chunks || 0}`);
  console.log(`   Entities: ${counts.entities || 0}`);
  console.log(`   Relationships: ${counts.relationships || 0}`);
  
  if ((counts.chunks || 0) === 0) {
    console.log('\n✓ Database is already empty.');
    rl.close();
    return;
  }
  
  // Confirm
  if (!skipConfirm) {
    const answer = await query('\n⚠️  This will DELETE all data. Have you backed up? (yes/no): ');
    if (answer.toLowerCase() !== 'yes') {
      console.log('Aborted.');
      rl.close();
      return;
    }
  }
  
  console.log('\n🗑️  Cleaning up...');
  
  try {
    // Truncate tables (faster than DELETE)
    console.log('   Truncating relationships...');
    await execSQL('TRUNCATE TABLE relationships CASCADE');
    
    console.log('   Truncating entities...');
    await execSQL('TRUNCATE TABLE entities CASCADE');
    
    console.log('   Truncating chunks...');
    await execSQL('TRUNCATE TABLE chunks CASCADE');
    
    if (vacuum) {
      console.log('   Running VACUUM to reclaim space...');
      await execSQL('VACUUM FULL');
    }
    
    // Verify
    const newCounts = await getTableCounts();
    console.log('\n✅ Cleanup completed!');
    console.log('   New state:');
    console.log(`   Chunks: ${newCounts.chunks || 0}`);
    console.log(`   Entities: ${newCounts.entities || 0}`);
    console.log(`   Relationships: ${newCounts.relationships || 0}`);
    
    // Clear upload tracker
    console.log('\n📝 Clearing upload tracker history...');
    // This would need to be done from the browser, but we can log it
    
  } catch (error) {
    console.error('\n❌ Cleanup failed:', error.message);
    throw error;
  } finally {
    rl.close();
  }
}

async function cleanupUploadTracker() {
  console.log('\n📝 To clear the upload tracker in your browser:');
  console.log('   1. Open WebUI in browser (http://localhost:8081)');
  console.log('   2. Open DevTools (F12)');
  console.log('   3. Run: localStorage.clear()');
  console.log('   4. Refresh the page');
}

// Main
if (require.main === module) {
  const args = process.argv.slice(2);
  const skipConfirm = args.includes('--yes') || args.includes('-y');
  const vacuum = !args.includes('--no-vacuum');
  
  cleanupDatabase({ skipConfirm, vacuum })
    .then(() => cleanupUploadTracker())
    .catch(err => {
      console.error(err.message);
      process.exit(1);
    });
}

module.exports = { cleanupDatabase, getTableCounts };
