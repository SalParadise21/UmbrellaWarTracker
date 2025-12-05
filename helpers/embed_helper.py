"""Embed creation functions"""
import discord
from typing import Dict, List, Optional


def create_stats_embed(user: discord.User, stats: Dict, war_info: Optional[Dict] = None, ranks: Optional[Dict[str, Optional[int]]] = None) -> discord.Embed:
    """Create an embed for displaying user stats with ranks"""
    title = f"{user.display_name}'s Stats"
    if war_info:
        title += f" - War {war_info['war_number']}"
    else:
        title += " (Lifetime)"
    
    embed = discord.Embed(title=title, color=discord.Color.gold())
    
    # Helper function to format stat value with rank
    def format_stat_with_rank(stat_name: str, value: int) -> str:
        stat_value = f"{value:,}"
        if ranks and stat_name in ranks and ranks[stat_name] is not None:
            rank = ranks[stat_name]
            # Add rank suffix
            if rank == 1:
                rank_suffix = " 🥇"
            elif rank == 2:
                rank_suffix = " 🥈"
            elif rank == 3:
                rank_suffix = " 🥉"
            else:
                rank_suffix = f" (#{rank})"
            stat_value += rank_suffix
        return stat_value
    
    # Damage stats
    embed.add_field(name="Enemy Player Damage", value=format_stat_with_rank('enemy_player_damage', stats.get('enemy_player_damage', 0)), inline=True)
    embed.add_field(name="Friendly Player Damage", value=format_stat_with_rank('friendly_player_damage', stats.get('friendly_player_damage', 0)), inline=True)
    embed.add_field(name="Enemy Structure/Vehicle Damage", value=format_stat_with_rank('enemy_structure_vehicle_damage', stats.get('enemy_structure_vehicle_damage', 0)), inline=True)
    embed.add_field(name="Friendly Structure/Vehicle Damage", value=format_stat_with_rank('friendly_structure_vehicle_damage', stats.get('friendly_structure_vehicle_damage', 0)), inline=True)
    
    # Support stats
    embed.add_field(name="Friendly Construction", value=format_stat_with_rank('friendly_construction', stats.get('friendly_construction', 0)), inline=True)
    embed.add_field(name="Friendly Repairing", value=format_stat_with_rank('friendly_repairing', stats.get('friendly_repairing', 0)), inline=True)
    embed.add_field(name="Friendly Healing", value=format_stat_with_rank('friendly_healing', stats.get('friendly_healing', 0)), inline=True)
    embed.add_field(name="Friendly Revivals", value=format_stat_with_rank('friendly_revivals', stats.get('friendly_revivals', 0)), inline=True)
    
    # Vehicle stats
    embed.add_field(name="Vehicles Captured By Enemy", value=format_stat_with_rank('vehicles_captured_by_enemy', stats.get('vehicles_captured_by_enemy', 0)), inline=True)
    embed.add_field(name="Vehicle Self Damage (Neutral)", value=format_stat_with_rank('vehicle_self_damage_neutral', stats.get('vehicle_self_damage_neutral', 0)), inline=True)
    embed.add_field(name="Vehicle Self Damage (Colonial)", value=format_stat_with_rank('vehicle_self_damage_colonial', stats.get('vehicle_self_damage_colonial', 0)), inline=True)
    embed.add_field(name="Vehicle Self Damage (Warden)", value=format_stat_with_rank('vehicle_self_damage_warden', stats.get('vehicle_self_damage_warden', 0)), inline=True)
    
    # Material stats
    embed.add_field(name="Materials Submitted", value=format_stat_with_rank('materials_submitted', stats.get('materials_submitted', 0)), inline=True)
    embed.add_field(name="Materials Gathered", value=format_stat_with_rank('materials_gathered', stats.get('materials_gathered', 0)), inline=True)
    embed.add_field(name="Supply Value Delivered", value=format_stat_with_rank('supply_value_delivered', stats.get('supply_value_delivered', 0)), inline=True)
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    
    return embed


async def create_leaderboard_embed(
    leaderboard_data: List[Dict],
    war_info: Optional[Dict] = None,
    bot: Optional[discord.Client] = None,
    is_live: bool = False
) -> discord.Embed:
    """Create an embed for displaying the leaderboard"""
    title = "🏆 Leaderboard"
    if is_live:
        title = "🏆 Live Leaderboard"
    
    if war_info:
        title += f" - War {war_info['war_number']}"
    else:
        title += " (Lifetime)"
    
    embed = discord.Embed(title=title, color=discord.Color.gold())
    
    description = ""
    medals = ["🥇", "🥈", "🥉"]
    
    for i, entry in enumerate(leaderboard_data):
        user_id = entry['user_id']
        try:
            if bot:
                user = await bot.fetch_user(user_id)
                username = user.display_name
            else:
                username = f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        medal = medals[i] if i < 3 else f"{i+1}."
        enemy_player_damage = entry.get('total_enemy_player_damage', 0) or 0
        enemy_structure_damage = entry.get('total_enemy_structure_vehicle_damage', 0) or 0
        construction = entry.get('total_friendly_construction', 0) or 0
        supply_value = entry.get('total_supply_value_delivered', 0) or 0
        
        if is_live:
            description += f"{medal} **{username}** - {enemy_player_damage:,} enemy dmg | {enemy_structure_damage:,} structure dmg | {construction:,} construction\n"
        else:
            description += f"{medal} **{username}** - {enemy_player_damage:,} enemy player dmg | {enemy_structure_damage:,} structure/vehicle dmg\n"
    
    embed.description = description
    if is_live:
        embed.set_footer(text="Updates every 5 minutes")
    embed.timestamp = discord.utils.utcnow()
    
    return embed


async def create_category_leaderboard_embed(
    category_data: Dict[str, List[Dict]],
    war_info: Optional[Dict] = None,
    bot: Optional[discord.Client] = None,
    is_live: bool = False
) -> discord.Embed:
    """Create an embed for displaying category-based leaderboards (top 5 per category)"""
    title = "🏆 Leaderboard"
    if is_live:
        title = "🏆 Live Leaderboard"
    
    if war_info:
        title += f" - War {war_info['war_number']}"
    else:
        title += " (Lifetime)"
    
    embed = discord.Embed(title=title, color=discord.Color.gold())
    
    # Stat names mapping (from dm_handler)
    stat_names = {
        'enemy_player_damage': 'Enemy Player Damage',
        'friendly_player_damage': 'Friendly Player Damage',
        'enemy_structure_vehicle_damage': 'Enemy Structure/Vehicle Damage',
        'friendly_structure_vehicle_damage': 'Friendly Structure/Vehicle Damage',
        'friendly_construction': 'Friendly Construction',
        'friendly_repairing': 'Friendly Repairing',
        'friendly_healing': 'Friendly Healing',
        'friendly_revivals': 'Friendly Revivals',
        'vehicles_captured_by_enemy': 'Vehicles Captured By Enemy',
        'vehicle_self_damage_neutral': 'Vehicle Self Damage (Neutral)',
        'vehicle_self_damage_colonial': 'Vehicle Self Damage (Colonial)',
        'vehicle_self_damage_warden': 'Vehicle Self Damage (Warden)',
        'materials_submitted': 'Materials Submitted',
        'materials_gathered': 'Materials Gathered',
        'supply_value_delivered': 'Supply Value Delivered'
    }
    
    medals = ["🥇", "🥈", "🥉"]
    
    # Create fields for each category
    for stat_name, entries in category_data.items():
        if not entries:
            continue
        
        field_value = ""
        for i, entry in enumerate(entries):
            user_id = entry['user_id']
            value = entry.get('total_value', 0) or 0
            
            try:
                if bot:
                    user = await bot.fetch_user(user_id)
                    username = user.display_name
                else:
                    username = f"User {user_id}"
            except:
                username = f"User {user_id}"
            
            medal = medals[i] if i < 3 else f"{i+1}."
            field_value += f"{medal} **{username}** - {value:,}\n"
        
        # Truncate field value if too long (Discord limit is 1024 chars)
        if len(field_value) > 1024:
            field_value = field_value[:1021] + "..."
        
        display_name = stat_names.get(stat_name, stat_name.replace('_', ' ').title())
        embed.add_field(name=display_name, value=field_value, inline=True)
    
    if is_live:
        embed.set_footer(text="Updates every 5 minutes")
    embed.timestamp = discord.utils.utcnow()
    
    return embed


def create_stat_update_embed(stats: Dict) -> discord.Embed:
    """Create an embed for confirming stat updates"""
    embed = discord.Embed(
        title="✅ Stats Updated!",
        description="Your stats have been successfully recorded.",
        color=discord.Color.green()
    )
    for key, value in stats.items():
        # Format numbers with commas, skip non-numeric values
        if isinstance(value, (int, float)):
            formatted_value = f"{int(value):,}"
        else:
            formatted_value = str(value)
        embed.add_field(name=key.replace('_', ' ').title(), value=formatted_value, inline=True)
    return embed

