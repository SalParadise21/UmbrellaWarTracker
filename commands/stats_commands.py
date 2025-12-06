"""Stats entry and viewing commands"""
import discord
from discord import app_commands
from discord.ui import View, Button
from typing import Optional

from helpers.database import get_active_war, get_user_stats, get_war_by_number, get_user_rank
from helpers.dm_handler import start_manual_entry_flow, start_edit_flow, start_screenshot_flow
from helpers.embed_helper import create_stats_embed


class StatEntryView(View):
    """View with button for manual entry"""
    def __init__(self, bot, war_id, war_number, dm_channel):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.war_id = war_id
        self.war_number = war_number
        self.dm_channel = dm_channel
    
    @discord.ui.button(label="✏️ Manual Entry", style=discord.ButtonStyle.blurple)
    async def manual_button(self, interaction: discord.Interaction, button: Button):
        """Handle manual entry button click"""
        # Acknowledge the button click first
        await interaction.response.defer(ephemeral=False)
        
        # Send confirmation (this goes to the channel, not DM)
        await interaction.followup.send("✅ Manual entry selected! Check your DMs - I'll guide you through each stat.", ephemeral=False)

        # Start manual entry flow (this sends the DM)
        await start_manual_entry_flow(self.dm_channel, interaction.user.id, self.war_id, self.war_number)
               
        self.stop()
    
    @discord.ui.button(label="📷 Submit Screenshot", style=discord.ButtonStyle.green)
    async def screenshot_button(self, interaction: discord.Interaction, button: Button):
        """Handle screenshot submission button click"""
        # Acknowledge the button click first
        await interaction.response.defer(ephemeral=False)
        
        # Send confirmation (this goes to the channel, not DM)
        await interaction.followup.send("✅ Screenshot submission selected! Check your DMs - I'll process your screenshot.", ephemeral=False)

        # Start screenshot flow (this sends the DM)
        await start_screenshot_flow(self.dm_channel, interaction.user.id, self.war_id, self.war_number)
               
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        """Handle cancel button click"""
        # Acknowledge the button click first
        await interaction.response.defer(ephemeral=False)
        
        # Send cancellation message
        await interaction.followup.send("❌ Stat entry cancelled.", ephemeral=False)
        
        self.stop()


# Track command executions to prevent duplicates
_command_executions = set()
# Track DMs sent to prevent duplicates (even if command is registered twice)
_dm_sent_tracking = set()

async def setup_commands(bot):
    """Register all stats commands with the bot"""
    
    @bot.tree.command(name="stats_entry", description="Enter your Foxhole stats (opens DM)")
    async def stats_entry(interaction: discord.Interaction):
        # Prevent duplicate command execution using interaction ID (unique per Discord interaction)
        execution_key = f"{interaction.user.id}_{interaction.id}"
        if execution_key in _command_executions:
            # This interaction was already processed
            if not interaction.response.is_done():
                await interaction.response.send_message("This command is already being processed.", ephemeral=True)
            return
        
        # Mark this execution
        _command_executions.add(execution_key)
        
        # Clean up after 5 minutes (interaction IDs are unique)
        import asyncio
        async def cleanup():
            await asyncio.sleep(300)  # 5 minutes
            _command_executions.discard(execution_key)
            _dm_sent_tracking.discard(execution_key)
        asyncio.create_task(cleanup())
        
        # Import here to get fresh reference
        from helpers.dm_handler import active_dm_sessions
        
        # Check if user already has an active session to prevent duplicates
        if interaction.user.id in active_dm_sessions:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "You already have an active stat entry session! Please complete or cancel it first.",
                    ephemeral=True
                )
            return
        
        # Check if we've already sent a DM for this interaction (prevents duplicates even if command registered twice)
        if execution_key in _dm_sent_tracking:
            if not interaction.response.is_done():
                await interaction.response.send_message("Check your DMs! I've already sent you a message.", ephemeral=True)
            return
        
        try:
            active_war = await get_active_war()
            if not active_war:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "No active war found! Please start a war first using /war_start.",
                        ephemeral=True
                    )
                return
            
            # Respond to interaction FIRST to avoid timeout
            if not interaction.response.is_done():
                await interaction.response.send_message("Check your DMs! I've sent you a message.", ephemeral=True)
            
            # Now get DM channel and send messages
            dm_channel = await interaction.user.create_dm()
            
            # Mark that we're about to send a DM (do this before sending to prevent race conditions)
            _dm_sent_tracking.add(execution_key)
            
            # Create view with manual entry button
            view = StatEntryView(bot, active_war['id'], active_war['war_number'], dm_channel)
            
            embed = discord.Embed(
                title="📊 Stat Entry",
                description=f"Entering stats for War {active_war['war_number']}\n\n"
                           "How would you like to submit your stats?\n\n"
                           "Click a button below to choose:",
                color=discord.Color.blue()
            )
            
            # Send the choice embed to DM
            await dm_channel.send(embed=embed, view=view)
            
        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't send you a DM! Please enable DMs from server members.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "I couldn't send you a DM! Please enable DMs from server members.",
                    ephemeral=True
                )
    
    @bot.tree.command(name="stats_edit", description="Edit your most recent stats (opens DM)")
    async def stats_edit(interaction: discord.Interaction):
        try:
            # Send initial DM
            dm_channel = await interaction.user.create_dm()
            
            active_war = await get_active_war()
            if not active_war:
                await interaction.response.send_message(
                    "No active war found! Please start a war first using /war_start.",
                    ephemeral=True
                )
                return
            
            # Get user's current stats
            current_stats = await get_user_stats(interaction.user.id, active_war['id'])
            
            if not current_stats or all(v == 0 for k, v in current_stats.items() if k not in ['user_id', 'id', 'war_id']):
                await interaction.response.send_message(
                    "You don't have any stats to edit for the current war! Use /stats_entry to add stats first.",
                    ephemeral=True
                )
                return
            
            # Start edit flow
            await start_edit_flow(dm_channel, interaction.user.id, active_war['id'], active_war['war_number'], current_stats)
            
            await interaction.response.send_message("Check your DMs! I've sent you a message to edit your stats.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't send you a DM! Please enable DMs from server members.",
                ephemeral=True
            )
    
    @bot.tree.command(name="stats_view", description="View your stats")
    @app_commands.describe(
        user="The user to view stats for (defaults to you)",
        war_number="Specific war number (leave empty for lifetime stats)"
    )
    async def stats_view(interaction: discord.Interaction, user: Optional[discord.User] = None, war_number: Optional[int] = None):
        from helpers import embed_helper
        from helpers.dm_handler import STAT_ORDER
        
        target_user = user or interaction.user
        
        war_id = None
        war_info = None
        if war_number:
            war = await get_war_by_number(war_number)
            if not war:
                await interaction.response.send_message(f"War {war_number} not found!", ephemeral=True)
                return
            war_id = war['id']
            war_info = war
        else:
            active_war = await get_active_war()
            if active_war:
                war_id = active_war['id']
                war_info = active_war
        
        stats = await get_user_stats(target_user.id, war_id)
        
        if not stats or all(v == 0 for k, v in stats.items() if k != 'user_id'):
            war_text = f" for War {war_info['war_number']}" if war_info else " (lifetime)"
            await interaction.response.send_message(
                f"No stats found for {target_user.mention}{war_text}.",
                ephemeral=True
            )
            return
        
        # Calculate ranks for each stat category
        ranks = {}
        for stat_name in STAT_ORDER:
            rank = await get_user_rank(stat_name, target_user.id, war_id)
            ranks[stat_name] = rank
        
        embed = create_stats_embed(target_user, stats, war_info, ranks)
        await interaction.response.send_message(embed=embed)

