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
                value="Not set\n\nUse the button below to set a channel for automatic updates.",
                inline=False
            )
        
        # Screenshot processing setting
        screenshot_enabled = await get_setting("screenshot_processing_enabled")
        screenshot_enabled = screenshot_enabled != "false"  # Default to True if not set
        status_text = "✅ Enabled" if screenshot_enabled else "❌ Disabled"
        embed.add_field(
            name="📷 Screenshot Processing",
            value=f"{status_text}\n\nWhen enabled, users can submit screenshots for automatic stat extraction.\n\nUse the buttons below to toggle this setting.",
            inline=False
        )
        
        embed.timestamp = discord.utils.utcnow()
        
        # Create view with toggle buttons and channel select
        from discord.ui import View, Button, ChannelSelect
        
        class SettingsView(View):
            def __init__(self, bot):
                super().__init__(timeout=300)
                self.bot = bot
            
            @discord.ui.button(label="✅ Enable Screenshot Processing", style=discord.ButtonStyle.green, row=0)
            async def enable_button(self, interaction: discord.Interaction, button: Button):
                await interaction.response.defer(ephemeral=True)
                await set_setting("screenshot_processing_enabled", "true")
                await interaction.followup.send("✅ Screenshot processing has been enabled!", ephemeral=True)
                # Refresh the settings view
                await self.refresh_settings(interaction)
            
            @discord.ui.button(label="❌ Disable Screenshot Processing", style=discord.ButtonStyle.red, row=0)
            async def disable_button(self, interaction: discord.Interaction, button: Button):
                await interaction.response.defer(ephemeral=True)
                await set_setting("screenshot_processing_enabled", "false")
                await interaction.followup.send("❌ Screenshot processing has been disabled!", ephemeral=True)
                # Refresh the settings view
                await self.refresh_settings(interaction)
            
            @discord.ui.button(label="📊 Set Leaderboard Channel", style=discord.ButtonStyle.blurple, row=1)
            async def set_channel_button(self, interaction: discord.Interaction, button: Button):
                """Show channel select menu"""
                bot_ref = self.bot  # Capture bot reference
                
                # Create a view with channel select
                class ChannelSelectView(View):
                    def __init__(self, bot):
                        super().__init__(timeout=300)
                        self.bot = bot
                        
                        # Create and add channel select component
                        self.channel_select = ChannelSelect(
                            placeholder="Select a text channel...",
                            channel_types=[discord.ChannelType.text],
                            row=0
                        )
                        self.channel_select.callback = self.channel_select_callback
                        self.add_item(self.channel_select)
                    
                    async def channel_select_callback(self, interaction: discord.Interaction):
                        await interaction.response.defer(ephemeral=True)
                        
                        channel = self.channel_select.values[0]
                        if not isinstance(channel, discord.TextChannel):
                            await interaction.followup.send("❌ Please select a text channel.", ephemeral=True)
                            return
                        
                        # Save the channel setting
                        await set_setting("leaderboard_channel_id", str(channel.id))
                        
                        # Trigger immediate leaderboard update
                        from helpers.database import get_active_war, set_leaderboard_message_id
                        from helpers.dm_handler import STAT_ORDER
                        from helpers.database import get_leaderboard_by_category
                        from helpers.embed_helper import create_category_leaderboard_embed
                        
                        active_war = await get_active_war()
                        
                        # Active war leaderboard
                        if active_war:
                            category_data = {}
                            for stat_name in STAT_ORDER:
                                leaderboard_data = await get_leaderboard_by_category(stat_name, active_war['id'], limit=5)
                                if leaderboard_data:
                                    category_data[stat_name] = leaderboard_data
                            
                            if category_data:
                                embed = await create_category_leaderboard_embed(category_data, active_war, self.bot, is_live=True)
                                message = await channel.send(embed=embed)
                                await set_leaderboard_message_id(active_war['id'], message.id)
                        
                        # Lifetime leaderboard
                        lifetime_category_data = {}
                        for stat_name in STAT_ORDER:
                            leaderboard_data = await get_leaderboard_by_category(stat_name, None, limit=5)
                            if leaderboard_data:
                                lifetime_category_data[stat_name] = leaderboard_data
                        
                        if lifetime_category_data:
                            lifetime_embed = await create_category_leaderboard_embed(lifetime_category_data, None, self.bot, is_live=True)
                            lifetime_message = await channel.send(embed=lifetime_embed)
                            await set_setting("lifetime_leaderboard_message_id", str(lifetime_message.id))
                        
                        await interaction.followup.send(
                            f"✅ Leaderboards will now update in {channel.mention}\n\n"
                            f"You can run `/settings` again to see the updated configuration.",
                            ephemeral=True
                        )
                        self.stop()
                
                channel_view = ChannelSelectView(bot_ref)
                embed = discord.Embed(
                    title="📊 Set Leaderboard Channel",
                    description="Select a text channel from the dropdown below where leaderboard updates will be posted.",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=channel_view, ephemeral=True)
            
            async def refresh_settings(self, interaction: discord.Interaction):
                """Refresh the settings embed"""
                # Get current settings
                leaderboard_channel_id = await get_setting("leaderboard_channel_id")
                leaderboard_channel = None
                if leaderboard_channel_id:
                    try:
                        leaderboard_channel = self.bot.get_channel(int(leaderboard_channel_id))
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
                        value="Not set\n\nUse the button below to set a channel for automatic updates.",
                        inline=False
                    )
                
                # Screenshot processing setting
                screenshot_enabled = await get_setting("screenshot_processing_enabled")
                screenshot_enabled = screenshot_enabled != "false"  # Default to True if not set
                status_text = "✅ Enabled" if screenshot_enabled else "❌ Disabled"
                embed.add_field(
                    name="📷 Screenshot Processing",
                    value=f"{status_text}\n\nWhen enabled, users can submit screenshots for automatic stat extraction.\n\nUse the buttons below to toggle this setting.",
                    inline=False
                )
                
                embed.timestamp = discord.utils.utcnow()
                
                await interaction.edit_original_response(embed=embed, view=self)
        
        view = SettingsView(bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
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

