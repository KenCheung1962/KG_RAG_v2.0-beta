/**
 * Database Management API Client
 * Interfaces with the database management API on port 8013
 */

const DB_API_URL = 'http://localhost:8013';

export interface DatabaseStats {
  counts: {
    documents?: number;
    chunks?: number;
    entities?: number;
    relationships?: number;
  };
  sizes: {
    chunks?: number;
    entities?: number;
    relationships?: number;
  };
  totalSize: number;
  totalSizeFormatted: string;
  timestamp: string;
}

export interface BackupInfo {
  name: string;
  created: string;
  size: string;
  metadata?: {
    timestamp: string;
    stats: {
      documents: number;
      chunks: number;
      entities: number;
      relationships: number;
    };
  };
}

export interface BackupResult {
  success: boolean;
  result: {
    backupPath: string;
    metadata: {
      timestamp: string;
      stats: Record<string, number>;
      exports: {
        entities: number;
        relationships: number;
        chunks: number;
      };
    };
  };
}

async function fetchDB(endpoint: string, options?: RequestInit): Promise<any> {
  try {
    const response = await fetch(`${DB_API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers
      }
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'TypeError') {
      // Network error - API not running
      throw new Error('Database Management API not running. Start it with: npm run db:api');
    }
    throw error;
  }
}

export async function getDatabaseStats(): Promise<DatabaseStats> {
  return fetchDB('/stats');
}

export async function listBackups(): Promise<BackupInfo[]> {
  const data = await fetchDB('/backups');
  return data.backups;
}

export async function createBackup(): Promise<BackupResult> {
  return fetchDB('/backup', { method: 'POST' });
}

export async function cleanupDatabase(): Promise<{ success: boolean }> {
  return fetchDB('/cleanup', { method: 'POST' });
}

export async function restoreBackup(backupName: string): Promise<{ success: boolean; message?: string }> {
  return fetchDB('/restore', {
    method: 'POST',
    body: JSON.stringify({ backupName })
  });
}

export async function deleteBackup(backupName: string): Promise<{ success: boolean; message?: string }> {
  return fetchDB('/backup', {
    method: 'DELETE',
    body: JSON.stringify({ backupName })
  });
}

export interface UploadFailure {
  timestamp: string;
  filename: string;
  error: string;
  size: string;
}

export interface UploadSuccess {
  timestamp: string;
  filename: string;
  doc_id: string;
  chunks: string;
  size: string;
}

export async function getUploadFailures(): Promise<{ 
  failures: UploadFailure[]; 
  successes: UploadSuccess[];
  total_failures: number;
  total_successes: number;
  log_file: string;
}> {
  // Note: This uses the main API (port 8002), not the DB management API (port 8013)
  const response = await fetch('http://localhost:8002/api/v1/upload-failures');
  if (!response.ok) {
    throw new Error(`Failed to fetch upload failures: ${response.status}`);
  }
  return response.json();
}

export async function checkDBManagementAPI(): Promise<boolean> {
  try {
    const response = await fetch(`${DB_API_URL}/health`, { 
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return response.ok;
  } catch {
    return false;
  }
}
