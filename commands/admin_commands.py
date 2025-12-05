"""Administrative commands for bot management"""
import discord
from discord import app_commands
from datetime import datetime

from helpers.database import get_setting, set_setting, export_database_to_csv


async def setup_commands(bot):
    """Register all admin commands with the bot"""
    # Note: sync_commands is now defined in bot.py to avoid duplicate registration issues
    # This file is kept for other admin commands
    
    @bot.tree.command(name="settings", description="View and manage bot settings (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings(interaction: discord.Interaction):
        """View and manage bot settings - requires administrator permissions"""
        # Get current settings
        leaderboard_channel_id = await get_setting("leaderboard_channel_id")
        leaderboard_channel = None
        if leaderboard_channel_id:
            try:
                leaderboard_channel = bot.get_channel(int(leaderboard_channel_id))
            except:
                pass
        
        # Create embed with current settings
        embed = discord.Embed(
            title="⚙️ Bot Settings",
            description="Current bot configuration settings.",
            color=discord.Color.blue()
        )
        
        # Leaderboard channel
        if leaderboard_channel:
            embed.add_field(
                name="📊 Leaderboard Channel",
                value=f"{leaderboard_channel.mention}\n\nAutomatic leaderboard updates are posted here.",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Leaderboard Channel",
                value="Not set\n\nUse `/leaderboard_channel` to set a channel for automatic updates.",
                inline=False
            )
        
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="export_database", description="Export database to CSV file (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def export_database(interaction: discord.Interaction):
        """Export the entire database to a CSV file and send it via DM"""
        # Defer immediately to avoid interaction timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Export database to CSV
            csv_file = await export_database_to_csv()
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"foxhole_stats_export_{timestamp}.csv"
            
            # Create Discord file object
            discord_file = discord.File(csv_file, filename=filename)
            
            # Try to send via DM
            try:
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send(
                    content="📊 **Database Export**\n\nHere is your database export file.",
                    file=discord_file
                )
                await interaction.followup.send(
                    "✅ Database export sent to your DMs!",
                    ephemeral=True
                )
            except discord.Forbidden:
                # If DMs are disabled, send in the channel
                await interaction.followup.send(
                    "⚠️ I couldn't send you a DM. Please enable DMs from server members, or here's the file:",
                    file=discord_file,
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Failed to send database export: {str(e)}",
                    ephemeral=True
                )
            
            # Close the BytesIO object
            csv_file.close()
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to export database: {str(e)}",
                ephemeral=True
            )

