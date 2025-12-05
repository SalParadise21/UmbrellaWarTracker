"""Leaderboard commands"""
import discord
from discord import app_commands
from typing import Optional

from helpers.database import get_leaderboard, get_war_by_number, get_active_war, set_setting, set_leaderboard_message_id
from helpers.embed_helper import create_leaderboard_embed


async def setup_commands(bot):
    """Register all leaderboard commands with the bot"""
    
    @bot.tree.command(name="leaderboard", description="View the leaderboard")
    @app_commands.describe(
        war_number="Specific war number (leave empty for lifetime leaderboard)",
        limit="Number of players to show (default: 10, max: 25)"
    )
    async def leaderboard(interaction: discord.Interaction, war_number: Optional[int] = None, limit: int = 10):
        if limit < 1 or limit > 25:
            limit = 10
        
        war_id = None
        war_info = None
        if war_number:
            war = await get_war_by_number(war_number)
            if not war:
                await interaction.response.send_message(f"War {war_number} not found!", ephemeral=True)
                return
            war_id = war['id']
            war_info = war
        
        leaderboard_data = await get_leaderboard(war_id, limit)
        
        if not leaderboard_data:
            war_text = f" for War {war_info['war_number']}" if war_info else ""
            await interaction.response.send_message(f"No stats found{war_text}.", ephemeral=True)
            return
        
        embed = await create_leaderboard_embed(leaderboard_data, war_info, bot)
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="leaderboard_channel", description="Set the channel for automatic leaderboard updates")
    @app_commands.describe(channel="The channel to post leaderboard updates")
    async def leaderboard_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        await set_setting("leaderboard_channel_id", str(channel.id))
        
        # Trigger immediate leaderboard update
        active_war = await get_active_war()
        if active_war:
            leaderboard_data = await get_leaderboard(active_war['id'], 10)
            if leaderboard_data:
                embed = await create_leaderboard_embed(leaderboard_data, active_war, bot, is_live=True)
                message = await channel.send(embed=embed)
                await set_leaderboard_message_id(active_war['id'], message.id)
        
        await interaction.response.send_message(
            f"Leaderboard will now update in {channel.mention}",
            ephemeral=True
        )

