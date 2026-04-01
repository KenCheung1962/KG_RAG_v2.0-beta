#!/usr/bin/env python3
"""
Relationship Embedding Progress Monitor
Run this to check embedding progress: python3 monitor_embeddings.py
"""

import asyncio
import asyncpg
import sys
from datetime import datetime

async def check_progress():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            database='kg_rag',
            user='postgres',
            password='postgres'
        )
        
        # Get counts
        total = await conn.fetchval('SELECT COUNT(*) FROM relationships')
        with_embeddings = await conn.fetchval('SELECT COUNT(*) FROM relationships WHERE embedding IS NOT NULL')
        without_embeddings = total - with_embeddings
        percentage = (with_embeddings / total * 100) if total > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"Relationship Embedding Progress - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Total Relationships:     {total:,}")
        print(f"With Embeddings:         {with_embeddings:,} ({percentage:.2f}%)")
        print(f"Without Embeddings:      {without_embeddings:,} ({100-percentage:.2f}%)")
        print(f"{'='*60}")
        
        # Calculate ETA to 50%
        target = total * 0.5
        remaining_to_50 = int(target - with_embeddings)
        if remaining_to_50 > 0:
            rate_per_minute = 200  # estimated rate
            eta_minutes = remaining_to_50 / rate_per_minute
            eta_hours = eta_minutes / 60
            print(f"Progress to 50%:         {percentage:.2f}% / 50%")
            print(f"Remaining for 50%:       {remaining_to_50:,} embeddings")
            print(f"Estimated Rate:          ~{rate_per_minute}/minute")
            print(f"ETA to 50%:              ~{eta_hours:.1f} hours")
        else:
            print(f"✓ Already exceeded 50%!")
        
        print(f"{'='*60}\n")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure PostgreSQL is running and accessible.")

if __name__ == "__main__":
    asyncio.run(check_progress())
