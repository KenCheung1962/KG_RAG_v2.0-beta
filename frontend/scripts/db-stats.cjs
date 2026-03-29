#!/usr/bin/env node
/**
 * Quick Database Stats Utility
 * Shows current database size and counts
 */

const { exec } = require('child_process');

function execSQL(sql) {
  return new Promise((resolve, reject) => {
    const cmd = `docker exec kg_rag_postgres psql -U postgres -d kg_rag -c "${sql}"`;
    exec(cmd, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}

async function showStats() {
  console.log('📊 Database Stats\n');
  
  try {
    // Table counts
    const countsOutput = await execSQL(`
      SELECT 'Documents', COUNT(DISTINCT source) FROM chunks
      UNION ALL SELECT 'Chunks', COUNT(*) FROM chunks
      UNION ALL SELECT 'Entities', COUNT(*) FROM entities
      UNION ALL SELECT 'Relationships', COUNT(*) FROM relationships;
    `);
    
    console.log('Counts:');
    countsOutput.split('\n').forEach(line => {
      const match = line.match(/(\w+)\s*\|\s*(\d+)/);
      if (match) {
        console.log(`   ${match[1]}: ${parseInt(match[2]).toLocaleString()}`);
      }
    });
    
    // Table sizes
    const sizesOutput = await execSQL(`
      SELECT 
        tablename,
        pg_size_pretty(pg_total_relation_size('public.' || tablename))
      FROM pg_tables 
      WHERE schemaname='public' AND tablename IN ('chunks', 'entities', 'relationships')
      ORDER BY pg_total_relation_size('public.' || tablename) DESC;
    `);
    
    console.log('\nTable Sizes:');
    sizesOutput.split('\n').forEach(line => {
      const match = line.match(/(\w+)\s*\|\s*(.+)/);
      if (match) {
        console.log(`   ${match[1]}: ${match[2].trim()}`);
      }
    });
    
    // Total database size
    const totalSize = await execSQL(`SELECT pg_size_pretty(pg_database_size('kg_rag'));`);
    const sizeMatch = totalSize.match(/\|\s*(.+)/);
    if (sizeMatch) {
      console.log(`\nTotal Database Size: ${sizeMatch[1].trim()}`);
    }
    
    console.log('\n💡 Tips:');
    console.log('   • Backup: npm run db:backup');
    console.log('   • Cleanup: npm run db:cleanup');
    console.log('   • Restore: npm run db:restore');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.log('\nMake sure Docker and PostgreSQL are running.');
  }
}

showStats();
