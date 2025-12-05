"""Database functions for war and stats management"""
import aiosqlite
import csv
import io
from datetime import datetime
from typing import Optional, List, Dict
from helpers.config import DATABASE_PATH


async def init_database():
    """Initialize the database with required tables"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Wars table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_number INTEGER UNIQUE NOT NULL,
                start_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User stats table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                war_id INTEGER,
                enemy_player_damage INTEGER DEFAULT 0,
                friendly_player_damage INTEGER DEFAULT 0,
                enemy_structure_vehicle_damage INTEGER DEFAULT 0,
                friendly_structure_vehicle_damage INTEGER DEFAULT 0,
                friendly_construction INTEGER DEFAULT 0,
                friendly_repairing INTEGER DEFAULT 0,
                friendly_healing INTEGER DEFAULT 0,
                friendly_revivals INTEGER DEFAULT 0,
                vehicles_captured_by_enemy INTEGER DEFAULT 0,
                vehicle_self_damage_neutral INTEGER DEFAULT 0,
                vehicle_self_damage_colonial INTEGER DEFAULT 0,
                vehicle_self_damage_warden INTEGER DEFAULT 0,
                materials_submitted INTEGER DEFAULT 0,
                materials_gathered INTEGER DEFAULT 0,
                supply_value_delivered INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (war_id) REFERENCES wars(id),
                UNIQUE(user_id, war_id)
            )
        """)
        
        # Settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        await db.commit()
        
        # Initialize default settings if they don't exist
        await init_default_settings()
        
        # Migrate existing database if needed
        await migrate_database()


async def init_default_settings():
    """Initialize default settings if they don't exist"""
    # No default settings to initialize currently
    pass


async def migrate_database():
    """Migrate existing database schema to new format"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if old columns exist
        cursor = await db.execute("PRAGMA table_info(user_stats)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # List of new columns to add
        new_columns = [
            ('enemy_player_damage', 'INTEGER DEFAULT 0'),
            ('friendly_player_damage', 'INTEGER DEFAULT 0'),
            ('enemy_structure_vehicle_damage', 'INTEGER DEFAULT 0'),
            ('friendly_structure_vehicle_damage', 'INTEGER DEFAULT 0'),
            ('friendly_construction', 'INTEGER DEFAULT 0'),
            ('friendly_repairing', 'INTEGER DEFAULT 0'),
            ('friendly_healing', 'INTEGER DEFAULT 0'),
            ('friendly_revivals', 'INTEGER DEFAULT 0'),
            ('vehicles_captured_by_enemy', 'INTEGER DEFAULT 0'),
            ('vehicle_self_damage_neutral', 'INTEGER DEFAULT 0'),
            ('vehicle_self_damage_colonial', 'INTEGER DEFAULT 0'),
            ('vehicle_self_damage_warden', 'INTEGER DEFAULT 0'),
            ('materials_submitted', 'INTEGER DEFAULT 0'),
            ('materials_gathered', 'INTEGER DEFAULT 0'),
            ('supply_value_delivered', 'INTEGER DEFAULT 0'),
        ]
        
        # Add missing columns
        for col_name, col_type in new_columns:
            if col_name not in column_names:
                try:
                    await db.execute(f"ALTER TABLE user_stats ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    print(f"Warning: Could not add column {col_name}: {e}")
        
        # Remove old columns if they exist (SQLite doesn't support DROP COLUMN directly)
        # We'll leave them for now - they won't be used but won't cause issues
        old_columns = ['kills', 'deaths', 'damage_dealt', 'damage_taken', 
                      'structures_built', 'structures_destroyed', 
                      'vehicles_destroyed', 'supplies_delivered']
        
        await db.commit()


async def get_active_war() -> Optional[Dict]:
    """Get the currently active war"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM wars WHERE is_active = 1 ORDER BY start_date DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def setup_war(war_number: int) -> bool:
    """Setup a new war (doesn't activate it)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO wars (war_number) VALUES (?)",
                (war_number,)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def start_war(war_number: int) -> bool:
    """Start a war (deactivates all other wars)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # Deactivate all wars
            await db.execute("UPDATE wars SET is_active = 0")
            # Activate the specified war
            await db.execute(
                "UPDATE wars SET is_active = 1, start_date = ? WHERE war_number = ?",
                (datetime.now().isoformat(), war_number)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def end_war(war_number: int) -> bool:
    """End a war"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "UPDATE wars SET is_active = 0, end_date = ? WHERE war_number = ?",
                (datetime.now().isoformat(), war_number)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def get_war_by_number(war_number: int) -> Optional[Dict]:
    """Get war information by war number"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM wars WHERE war_number = ?", (war_number,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_all_wars() -> List[Dict]:
    """Get all wars from the database"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM wars ORDER BY war_number DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_active_wars() -> List[Dict]:
    """Get all currently active wars"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM wars WHERE is_active = 1 ORDER BY start_date DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_user_stats(
    user_id: int,
    war_id: Optional[int],
    enemy_player_damage: int = 0,
    friendly_player_damage: int = 0,
    enemy_structure_vehicle_damage: int = 0,
    friendly_structure_vehicle_damage: int = 0,
    friendly_construction: int = 0,
    friendly_repairing: int = 0,
    friendly_healing: int = 0,
    friendly_revivals: int = 0,
    vehicles_captured_by_enemy: int = 0,
    vehicle_self_damage_neutral: int = 0,
    vehicle_self_damage_colonial: int = 0,
    vehicle_self_damage_warden: int = 0,
    materials_submitted: int = 0,
    materials_gathered: int = 0,
    supply_value_delivered: int = 0
):
    """Update or insert user stats for a war"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO user_stats 
            (user_id, war_id, enemy_player_damage, friendly_player_damage, enemy_structure_vehicle_damage,
             friendly_structure_vehicle_damage, friendly_construction, friendly_repairing, friendly_healing,
             friendly_revivals, vehicles_captured_by_enemy, vehicle_self_damage_neutral,
             vehicle_self_damage_colonial, vehicle_self_damage_warden, materials_submitted,
             materials_gathered, supply_value_delivered, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, war_id) DO UPDATE SET
                enemy_player_damage = enemy_player_damage + ?,
                friendly_player_damage = friendly_player_damage + ?,
                enemy_structure_vehicle_damage = enemy_structure_vehicle_damage + ?,
                friendly_structure_vehicle_damage = friendly_structure_vehicle_damage + ?,
                friendly_construction = friendly_construction + ?,
                friendly_repairing = friendly_repairing + ?,
                friendly_healing = friendly_healing + ?,
                friendly_revivals = friendly_revivals + ?,
                vehicles_captured_by_enemy = vehicles_captured_by_enemy + ?,
                vehicle_self_damage_neutral = vehicle_self_damage_neutral + ?,
                vehicle_self_damage_colonial = vehicle_self_damage_colonial + ?,
                vehicle_self_damage_warden = vehicle_self_damage_warden + ?,
                materials_submitted = materials_submitted + ?,
                materials_gathered = materials_gathered + ?,
                supply_value_delivered = supply_value_delivered + ?,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id, war_id, enemy_player_damage, friendly_player_damage, enemy_structure_vehicle_damage,
            friendly_structure_vehicle_damage, friendly_construction, friendly_repairing, friendly_healing,
            friendly_revivals, vehicles_captured_by_enemy, vehicle_self_damage_neutral,
            vehicle_self_damage_colonial, vehicle_self_damage_warden, materials_submitted,
            materials_gathered, supply_value_delivered, datetime.now().isoformat(),
            enemy_player_damage, friendly_player_damage, enemy_structure_vehicle_damage,
            friendly_structure_vehicle_damage, friendly_construction, friendly_repairing, friendly_healing,
            friendly_revivals, vehicles_captured_by_enemy, vehicle_self_damage_neutral,
            vehicle_self_damage_colonial, vehicle_self_damage_warden, materials_submitted,
            materials_gathered, supply_value_delivered
        ))
        await db.commit()


async def set_user_stat(user_id: int, war_id: int, stat_name: str, stat_value: int) -> bool:
    """Set a specific stat value for a user (for editing)"""
    # Validate stat name
    valid_stats = [
        'enemy_player_damage', 'friendly_player_damage', 'enemy_structure_vehicle_damage',
        'friendly_structure_vehicle_damage', 'friendly_construction', 'friendly_repairing',
        'friendly_healing', 'friendly_revivals', 'vehicles_captured_by_enemy',
        'vehicle_self_damage_neutral', 'vehicle_self_damage_colonial', 'vehicle_self_damage_warden',
        'materials_submitted', 'materials_gathered', 'supply_value_delivered'
    ]
    
    if stat_name not in valid_stats:
        return False
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # First, ensure the record exists
            await db.execute("""
                INSERT OR IGNORE INTO user_stats 
                (user_id, war_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (user_id, war_id))
            
            # Update the specific stat
            await db.execute(f"""
                UPDATE user_stats 
                SET {stat_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND war_id = ?
            """, (stat_value, user_id, war_id))
            
            await db.commit()
            return True
        except Exception:
            return False


async def get_user_stats(user_id: int, war_id: Optional[int] = None) -> Dict:
    """Get user stats for a specific war or lifetime"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if war_id:
            async with db.execute(
                "SELECT * FROM user_stats WHERE user_id = ? AND war_id = ?",
                (user_id, war_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        else:
            # Lifetime stats
            async with db.execute("""
                SELECT 
                    SUM(enemy_player_damage) as enemy_player_damage,
                    SUM(friendly_player_damage) as friendly_player_damage,
                    SUM(enemy_structure_vehicle_damage) as enemy_structure_vehicle_damage,
                    SUM(friendly_structure_vehicle_damage) as friendly_structure_vehicle_damage,
                    SUM(friendly_construction) as friendly_construction,
                    SUM(friendly_repairing) as friendly_repairing,
                    SUM(friendly_healing) as friendly_healing,
                    SUM(friendly_revivals) as friendly_revivals,
                    SUM(vehicles_captured_by_enemy) as vehicles_captured_by_enemy,
                    SUM(vehicle_self_damage_neutral) as vehicle_self_damage_neutral,
                    SUM(vehicle_self_damage_colonial) as vehicle_self_damage_colonial,
                    SUM(vehicle_self_damage_warden) as vehicle_self_damage_warden,
                    SUM(materials_submitted) as materials_submitted,
                    SUM(materials_gathered) as materials_gathered,
                    SUM(supply_value_delivered) as supply_value_delivered
                FROM user_stats
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and any(row.values()):
                    return dict(row)
        return {}


async def get_leaderboard(war_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
    """Get leaderboard for a war or lifetime"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if war_id:
            async with db.execute("""
                SELECT user_id, 
                       SUM(enemy_player_damage) as total_enemy_player_damage,
                       SUM(enemy_structure_vehicle_damage) as total_enemy_structure_vehicle_damage,
                       SUM(friendly_construction) as total_friendly_construction,
                       SUM(supply_value_delivered) as total_supply_value_delivered
                FROM user_stats
                WHERE war_id = ?
                GROUP BY user_id
                ORDER BY total_enemy_player_damage DESC, total_enemy_structure_vehicle_damage DESC
                LIMIT ?
            """, (war_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        else:
            # Lifetime leaderboard
            async with db.execute("""
                SELECT user_id,
                       SUM(enemy_player_damage) as total_enemy_player_damage,
                       SUM(enemy_structure_vehicle_damage) as total_enemy_structure_vehicle_damage,
                       SUM(friendly_construction) as total_friendly_construction,
                       SUM(supply_value_delivered) as total_supply_value_delivered
                FROM user_stats
                GROUP BY user_id
                ORDER BY total_enemy_player_damage DESC, total_enemy_structure_vehicle_damage DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


async def get_leaderboard_by_category(stat_name: str, war_id: Optional[int] = None, limit: int = 5) -> List[Dict]:
    """Get leaderboard for a specific stat category"""
    # Validate stat name
    valid_stats = [
        'enemy_player_damage', 'friendly_player_damage', 'enemy_structure_vehicle_damage',
        'friendly_structure_vehicle_damage', 'friendly_construction', 'friendly_repairing',
        'friendly_healing', 'friendly_revivals', 'vehicles_captured_by_enemy',
        'vehicle_self_damage_neutral', 'vehicle_self_damage_colonial', 'vehicle_self_damage_warden',
        'materials_submitted', 'materials_gathered', 'supply_value_delivered'
    ]
    
    if stat_name not in valid_stats:
        return []
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if war_id:
            async with db.execute(f"""
                SELECT user_id, 
                       SUM({stat_name}) as total_value
                FROM user_stats
                WHERE war_id = ?
                GROUP BY user_id
                HAVING total_value > 0
                ORDER BY total_value DESC
                LIMIT ?
            """, (war_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        else:
            # Lifetime leaderboard
            async with db.execute(f"""
                SELECT user_id,
                       SUM({stat_name}) as total_value
                FROM user_stats
                GROUP BY user_id
                HAVING total_value > 0
                ORDER BY total_value DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


async def get_user_rank(stat_name: str, user_id: int, war_id: Optional[int] = None) -> Optional[int]:
    """Get user's rank in a specific stat category (1-based, None if no stats)"""
    # Validate stat name
    valid_stats = [
        'enemy_player_damage', 'friendly_player_damage', 'enemy_structure_vehicle_damage',
        'friendly_structure_vehicle_damage', 'friendly_construction', 'friendly_repairing',
        'friendly_healing', 'friendly_revivals', 'vehicles_captured_by_enemy',
        'vehicle_self_damage_neutral', 'vehicle_self_damage_colonial', 'vehicle_self_damage_warden',
        'materials_submitted', 'materials_gathered', 'supply_value_delivered'
    ]
    
    if stat_name not in valid_stats:
        return None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # First, get the user's value
        if war_id:
            async with db.execute(f"""
                SELECT SUM({stat_name}) as user_value
                FROM user_stats
                WHERE user_id = ? AND war_id = ?
            """, (user_id, war_id)) as cursor:
                row = await cursor.fetchone()
                if not row or not row['user_value'] or row['user_value'] == 0:
                    return None
                user_value = row['user_value']
        else:
            async with db.execute(f"""
                SELECT SUM({stat_name}) as user_value
                FROM user_stats
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row or not row['user_value'] or row['user_value'] == 0:
                    return None
                user_value = row['user_value']
        
        # Count how many users have a higher value
        if war_id:
            async with db.execute(f"""
                SELECT COUNT(DISTINCT user_id) as rank
                FROM user_stats
                WHERE war_id = ?
                GROUP BY user_id
                HAVING SUM({stat_name}) > ?
            """, (war_id, user_value)) as cursor:
                row = await cursor.fetchone()
                rank = (row['rank'] if row else 0) + 1
        else:
            async with db.execute(f"""
                SELECT COUNT(DISTINCT user_id) as rank
                FROM user_stats
                GROUP BY user_id
                HAVING SUM({stat_name}) > ?
            """, (user_value,)) as cursor:
                row = await cursor.fetchone()
                rank = (row['rank'] if row else 0) + 1
        
        return rank


async def get_setting(key: str) -> Optional[str]:
    """Get a setting value"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None


async def set_setting(key: str, value: str):
    """Set a setting value"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_leaderboard_message_id(war_id: int) -> Optional[int]:
    """Get the message ID for a war's leaderboard"""
    message_id = await get_setting(f"leaderboard_message_id_{war_id}")
    if message_id:
        try:
            return int(message_id)
        except ValueError:
            return None
    return None


async def set_leaderboard_message_id(war_id: int, message_id: int):
    """Set the message ID for a war's leaderboard"""
    await set_setting(f"leaderboard_message_id_{war_id}", str(message_id))


async def export_database_to_csv() -> io.BytesIO:
    """Export all database tables to a CSV file in memory"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Export wars table
        writer.writerow(["=== WARS TABLE ==="])
        writer.writerow(["id", "war_number", "start_date", "end_date", "is_active", "created_at"])
        async with db.execute("SELECT * FROM wars ORDER BY war_number") as cursor:
            async for row in cursor:
                writer.writerow([row["id"], row["war_number"], row["start_date"], 
                                row["end_date"], row["is_active"], row["created_at"]])
        writer.writerow([])  # Empty row separator
        
        # Export user_stats table
        writer.writerow(["=== USER_STATS TABLE ==="])
        writer.writerow(["id", "user_id", "war_id", "enemy_player_damage", "friendly_player_damage",
                        "enemy_structure_vehicle_damage", "friendly_structure_vehicle_damage",
                        "friendly_construction", "friendly_repairing", "friendly_healing",
                        "friendly_revivals", "vehicles_captured_by_enemy", "vehicle_self_damage_neutral",
                        "vehicle_self_damage_colonial", "vehicle_self_damage_warden",
                        "materials_submitted", "materials_gathered", "supply_value_delivered", "updated_at"])
        async with db.execute("SELECT * FROM user_stats ORDER BY user_id, war_id") as cursor:
            async for row in cursor:
                writer.writerow([
                    row["id"], row["user_id"], row["war_id"],
                    row["enemy_player_damage"], row["friendly_player_damage"],
                    row["enemy_structure_vehicle_damage"], row["friendly_structure_vehicle_damage"],
                    row["friendly_construction"], row["friendly_repairing"],
                    row["friendly_healing"], row["friendly_revivals"],
                    row["vehicles_captured_by_enemy"], row["vehicle_self_damage_neutral"],
                    row["vehicle_self_damage_colonial"], row["vehicle_self_damage_warden"],
                    row["materials_submitted"], row["materials_gathered"],
                    row["supply_value_delivered"], row["updated_at"]
                ])
        writer.writerow([])  # Empty row separator
        
        # Export settings table
        writer.writerow(["=== SETTINGS TABLE ==="])
        writer.writerow(["key", "value"])
        async with db.execute("SELECT * FROM settings ORDER BY key") as cursor:
            async for row in cursor:
                writer.writerow([row["key"], row["value"]])
    
    # Convert StringIO to BytesIO for file attachment
    csv_content = output.getvalue()
    output.close()
    csv_bytes = io.BytesIO(csv_content.encode('utf-8-sig'))  # utf-8-sig for Excel compatibility
    csv_bytes.seek(0)
    return csv_bytes

