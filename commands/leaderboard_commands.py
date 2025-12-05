"""Leaderboard commands"""
import discord
from discord import app_commands
from typing import Optional

from helpers.database import get_leaderboard, get_leaderboard_by_category, get_war_by_number, get_active_war, set_setting, set_leaderboard_message_id
from helpers.embed_helper import create_leaderboard_embed, create_category_leaderboard_embed
from helpers.dm_handler import STAT_ORDER


async def setup_commands(bot):
    """Register all leaderboard commands with the bot"""
    
    @bot.tree.command(name="leaderboard", description="View the leaderboard (top 5 per category)")
    @app_commands.choices(leaderboard_type=[
        app_commands.Choice(name="Active War", value="war"),
        app_commands.Choice(name="Lifetime", value="lifetime")
    ])
    @app_commands.describe(
        leaderboard_type="Type of leaderboard to view",
        war_number="Specific war number (only used if leaderboard_type is 'war')"
    )
    async def leaderboard(
        interaction: discord.Interaction, 
        leaderboard_type: Optional[app_commands.Choice[str]] = None,
        war_number: Optional[int] = None
    ):
        # Defer response immediately to avoid timeout
        await interaction.response.defer()
        
        # Determine leaderboard type
        war_id = None
        war_info = None
        
        # Extract value from Choice if provided
        leaderboard_type_value = leaderboard_type.value if leaderboard_type else None
        
        if leaderboard_type_value == "lifetime":
            # Lifetime leaderboard
            war_id = None
            war_info = None
        elif leaderboard_type_value == "war":
            # Specific war leaderboard
            if war_number:
                war = await get_war_by_number(war_number)
                if not war:
                    await interaction.followup.send(f"War {war_number} not found!", ephemeral=True)
                    return
                war_id = war['id']
                war_info = war
            else:
                # Use active war
                active_war = await get_active_war()
                if not active_war:
                    await interaction.followup.send("No active war found! Please specify a war number or start a war.", ephemeral=True)
                    return
                war_id = active_war['id']
                war_info = active_war
        else:
            # Default: use active war if available, otherwise lifetime
            active_war = await get_active_war()
            if active_war:
                war_id = active_war['id']
                war_info = active_war
            # Otherwise war_id stays None for lifetime
        
        # Get top 5 for each category
        category_data = {}
        for stat_name in STAT_ORDER:
            leaderboard_data = await get_leaderboard_by_category(stat_name, war_id, limit=5)
            if leaderboard_data:
                category_data[stat_name] = leaderboard_data
        
        if not category_data:
            war_text = f" for War {war_info['war_number']}" if war_info else " (lifetime)"
            await interaction.followup.send(f"No stats found{war_text}.", ephemeral=True)
            return
        
        embed = await create_category_leaderboard_embed(category_data, war_info, bot, is_live=False)
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="leaderboard_channel", description="Set the channel for automatic leaderboard updates")
    @app_commands.describe(channel="The channel to post leaderboard updates")
    async def leaderboard_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        await set_setting("leaderboard_channel_id", str(channel.id))
        
        # Trigger immediate leaderboard update for both active war and lifetime
        active_war = await get_active_war()
        
        # Active war leaderboard
        if active_war:
            category_data = {}
            for stat_name in STAT_ORDER:
                leaderboard_data = await get_leaderboard_by_category(stat_name, active_war['id'], limit=5)
                if leaderboard_data:
                    category_data[stat_name] = leaderboard_data
            
            if category_data:
                embed = await create_category_leaderboard_embed(category_data, active_war, bot, is_live=True)
                message = await channel.send(embed=embed)
                await set_leaderboard_message_id(active_war['id'], message.id)
        
        # Lifetime leaderboard
        lifetime_category_data = {}
        for stat_name in STAT_ORDER:
            leaderboard_data = await get_leaderboard_by_category(stat_name, None, limit=5)
            if leaderboard_data:
                lifetime_category_data[stat_name] = leaderboard_data
        
        if lifetime_category_data:
            lifetime_embed = await create_category_leaderboard_embed(lifetime_category_data, None, bot, is_live=True)
            lifetime_message = await channel.send(embed=lifetime_embed)
            await set_setting("lifetime_leaderboard_message_id", str(lifetime_message.id))
        
        await interaction.response.send_message(
            f"Leaderboards will now update in {channel.mention}",
            ephemeral=True
        )

