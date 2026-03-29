#!/usr/bin/env node
/**
 * Database Backup Scheduler
 * Runs periodic backups based on configuration
 */

const { exportDatabase } = require('./db-backup.cjs');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'backup-config.json');
const LOG_PATH = path.join(__dirname, '..', 'backups', 'scheduler.log');

// Default config
const DEFAULT_CONFIG = {
  enabled: false,
  interval: '24h',      // Backup interval: 1h, 6h, 12h, 24h, 7d
  maxBackups: 5,        // Maximum backups to keep
  onStartup: true,      // Backup on scheduler start
  autoCleanup: true     // Auto cleanup old backups
};

function loadConfig() {
  if (fs.existsSync(CONFIG_PATH)) {
    return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8')) };
  }
  return DEFAULT_CONFIG;
}

function saveConfig(config) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
}

function log(message) {
  const timestamp = new Date().toISOString();
  const entry = `[${timestamp}] ${message}\n`;
  console.log(message);
  
  const logDir = path.dirname(LOG_PATH);
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  fs.appendFileSync(LOG_PATH, entry);
}

function parseInterval(interval) {
  const match = interval.match(/(\d+)([hd])/);
  if (!match) return 24 * 60 * 60 * 1000; // Default 24h
  
  const [, num, unit] = match;
  const multiplier = unit === 'h' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
  return parseInt(num) * multiplier;
}

async function runBackup() {
  try {
    log('🔄 Running scheduled backup...');
    const backupPath = await exportDatabase();
    log(`✅ Backup completed: ${path.basename(backupPath)}`);
    return backupPath;
  } catch (error) {
    log(`❌ Backup failed: ${error.message}`);
    throw error;
  }
}

async function startScheduler() {
  const config = loadConfig();
  
  if (!config.enabled) {
    console.log('Scheduler is disabled. Enable it in backup-config.json');
    console.log('Run: node scripts/db-scheduler.cjs --enable');
    return;
  }
  
  log('🚀 Starting backup scheduler...');
  log(`   Interval: ${config.interval}`);
  log(`   Max backups: ${config.maxBackups}`);
  
  // Initial backup
  if (config.onStartup) {
    await runBackup();
  }
  
  // Schedule next backup
  const intervalMs = parseInterval(config.interval);
  log(`   Next backup in ${config.interval}`);
  
  setInterval(async () => {
    await runBackup();
  }, intervalMs);
  
  // Keep process alive
  process.stdin.resume();
}

// CLI commands
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  
  switch (command) {
    case '--enable':
    case '-e': {
      const config = loadConfig();
      config.enabled = true;
      saveConfig(config);
      console.log('✅ Scheduler enabled');
      console.log('Config:', CONFIG_PATH);
      break;
    }
      
    case '--disable':
    case '-d': {
      const config = loadConfig();
      config.enabled = false;
      saveConfig(config);
      console.log('✅ Scheduler disabled');
      break;
    }
      
    case '--config':
    case '-c': {
      const config = loadConfig();
      console.log('Current config:');
      console.log(JSON.stringify(config, null, 2));
      console.log(`\nConfig file: ${CONFIG_PATH}`);
      break;
    }
      
    case '--set-interval':
    case '-i': {
      const interval = args[1];
      if (!interval || !interval.match(/^\d+[hd]$/)) {
        console.log('Usage: --set-interval <interval>');
        console.log('Examples: 1h, 6h, 12h, 24h, 7d');
        process.exit(1);
      }
      const config = loadConfig();
      config.interval = interval;
      saveConfig(config);
      console.log(`✅ Interval set to ${interval}`);
      break;
    }
      
    case '--run-once':
    case '-r': {
      await runBackup();
      break;
    }
      
    case '--help':
    case '-h':
    default: {
      console.log('Database Backup Scheduler');
      console.log('');
      console.log('Commands:');
      console.log('  --enable, -e           Enable automatic backups');
      console.log('  --disable, -d          Disable automatic backups');
      console.log('  --config, -c           Show current configuration');
      console.log('  --set-interval, -i     Set backup interval (1h, 6h, 12h, 24h, 7d)');
      console.log('  --run-once, -r         Run a single backup now');
      console.log('  --help, -h             Show this help');
      console.log('');
      console.log('Examples:');
      console.log('  node scripts/db-scheduler.cjs --enable');
      console.log('  node scripts/db-scheduler.cjs --set-interval 6h');
      console.log('  node scripts/db-scheduler.cjs --run-once');
      break;
    }
  }
}

// Start if running directly
if (require.main === module) {
  main().catch(err => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { startScheduler, runBackup };
