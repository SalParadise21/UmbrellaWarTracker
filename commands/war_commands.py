"""War management commands"""
import discord
from discord import app_commands

from helpers.database import setup_war, start_war, end_war, get_war_by_number, get_all_wars, get_active_wars


async def setup_commands(bot):
    """Register all war management commands with the bot"""
    
    @bot.tree.command(name="war_setup", description="Setup a new war number")
    @app_commands.describe(war_number="The war number to setup")
    async def war_setup(interaction: discord.Interaction, war_number: int):
        if war_number <= 0:
            await interaction.response.send_message("War number must be positive!", ephemeral=True)
            return
        
        success = await setup_war(war_number)
        if success:
            await interaction.response.send_message(f"War {war_number} has been setup!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to setup war {war_number}. It may already exist.", ephemeral=True)
    
    @bot.tree.command(name="war_start", description="Start a war (Admin only)")
    @app_commands.describe(war_number="The war number to start")
    @app_commands.checks.has_permissions(administrator=True)
    async def war_start(interaction: discord.Interaction, war_number: int):
        """Start a war - requires administrator permissions"""
        war = await get_war_by_number(war_number)
        if not war:
            await interaction.response.send_message(f"War {war_number} has not been setup yet! Use /war_setup first.", ephemeral=True)
            return
        
        success = await start_war(war_number)
        if success:
            await interaction.response.send_message(f"War {war_number} has been started!", ephemeral=False)
        else:
            await interaction.response.send_message(f"Failed to start war {war_number}.", ephemeral=True)
    
    @war_start.autocomplete('war_number')
    async def war_start_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[int]]:
        """Autocomplete for war_start command - shows all available wars"""
        wars = await get_all_wars()
        choices = []
        
        for war in wars:
            war_num = war['war_number']
            war_str = str(war_num)
            
            # Filter by current input if provided, otherwise show all
            if not current or current.lower() in war_str.lower():
                status = " (Active)" if war.get('is_active') else ""
                choices.append(
                    app_commands.Choice(name=f"War {war_str}{status}", value=war_num)
                )
        
        return choices[:25]  # Discord limit is 25 choices
    
    @bot.tree.command(name="war_end", description="End a war (Admin only)")
    @app_commands.describe(war_number="The war number to end")
    @app_commands.checks.has_permissions(administrator=True)
    async def war_end(interaction: discord.Interaction, war_number: int):
        """End a war - requires administrator permissions"""
        success = await end_war(war_number)
        if success:
            await interaction.response.send_message(f"War {war_number} has been ended!", ephemeral=False)
        else:
            await interaction.response.send_message(f"Failed to end war {war_number}.", ephemeral=True)
    
    @war_end.autocomplete('war_number')
    async def war_end_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[int]]:
        """Autocomplete for war_end command - shows only active wars"""
        active_wars = await get_active_wars()
        choices = []
        
        for war in active_wars:
            war_num = war['war_number']
            war_str = str(war_num)
            
            # Filter by current input if provided, otherwise show all active wars
            if not current or current.lower() in war_str.lower():
                choices.append(
                    app_commands.Choice(name=f"War {war_str} (Active)", value=war_num)
                )
        
        return choices[:25]  # Discord limit is 25 choices

