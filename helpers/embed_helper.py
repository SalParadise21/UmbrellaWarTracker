"""Embed creation functions"""
import discord
from typing import Dict, List, Optional


def create_stats_embed(user: discord.User, stats: Dict, war_info: Optional[Dict] = None) -> discord.Embed:
    """Create an embed for displaying user stats"""
    title = f"{user.display_name}'s Stats"
    if war_info:
        title += f" - War {war_info['war_number']}"
    else:
        title += " (Lifetime)"
    
    embed = discord.Embed(title=title, color=discord.Color.gold())
    
    # Damage stats
    embed.add_field(name="Enemy Player Damage", value=f"{stats.get('enemy_player_damage', 0):,}", inline=True)
    embed.add_field(name="Friendly Player Damage", value=f"{stats.get('friendly_player_damage', 0):,}", inline=True)
    embed.add_field(name="Enemy Structure/Vehicle Damage", value=f"{stats.get('enemy_structure_vehicle_damage', 0):,}", inline=True)
    embed.add_field(name="Friendly Structure/Vehicle Damage", value=f"{stats.get('friendly_structure_vehicle_damage', 0):,}", inline=True)
    
    # Support stats
    embed.add_field(name="Friendly Construction", value=f"{stats.get('friendly_construction', 0):,}", inline=True)
    embed.add_field(name="Friendly Repairing", value=f"{stats.get('friendly_repairing', 0):,}", inline=True)
    embed.add_field(name="Friendly Healing", value=f"{stats.get('friendly_healing', 0):,}", inline=True)
    embed.add_field(name="Friendly Revivals", value=f"{stats.get('friendly_revivals', 0):,}", inline=True)
    
    # Vehicle stats
    embed.add_field(name="Vehicles Captured By Enemy", value=f"{stats.get('vehicles_captured_by_enemy', 0):,}", inline=True)
    embed.add_field(name="Vehicle Self Damage (Neutral)", value=f"{stats.get('vehicle_self_damage_neutral', 0):,}", inline=True)
    embed.add_field(name="Vehicle Self Damage (Colonial)", value=f"{stats.get('vehicle_self_damage_colonial', 0):,}", inline=True)
    embed.add_field(name="Vehicle Self Damage (Warden)", value=f"{stats.get('vehicle_self_damage_warden', 0):,}", inline=True)
    
    # Material stats
    embed.add_field(name="Materials Submitted", value=f"{stats.get('materials_submitted', 0):,}", inline=True)
    embed.add_field(name="Materials Gathered", value=f"{stats.get('materials_gathered', 0):,}", inline=True)
    embed.add_field(name="Supply Value Delivered", value=f"{stats.get('supply_value_delivered', 0):,}", inline=True)
    
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

