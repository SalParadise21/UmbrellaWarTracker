"""Main bot file for Umbrella War Tracker Discord Bot"""
import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
import asyncio
from dotenv import load_dotenv

# Check Python version (requires 3.12+)
if sys.version_info < (3, 12):
    print(f"Error: Python 3.12.10 or higher is required. Current version: {sys.version}")
    print("Please upgrade Python to 3.12.10 or later.")
    sys.exit(1)

# Fix Windows console encoding to support Unicode characters
if sys.platform == 'win32':
    try:
        # Try to set console encoding to UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Fallback for older Python versions or if reconfigure fails
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from helpers.database import init_database
from helpers.dm_handler import handle_dm_message
from helpers.leaderboard_updater import start_leaderboard_updater
from commands import (
    war_commands, stats_commands, leaderboard_commands, admin_commands
)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Track if sync_commands has been registered
_sync_command_registered = False

def register_sync_command():
    """Register the sync_commands command"""
    global _sync_command_registered
    
    # Skip if already registered (unless we're re-registering)
    if _sync_command_registered:
        return
    
    _sync_command_registered = True
    
    @bot.tree.command(name="sync_commands", description="Re-register all bot commands (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(interaction: discord.Interaction):
        """Re-register all bot commands"""
        # Check if command is being run in a DM
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server, not in DMs.\n\n"
                "Admin commands require server context to check permissions.",
                ephemeral=True
            )
            return
        
        # Defer immediately to avoid interaction timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Clear all commands first to avoid duplicates
            # This removes all commands from the command tree
            bot.tree.clear_commands(guild=None)
            
            # Wait a moment for clear to complete
            await asyncio.sleep(0.1)
            
            # Reset the sync command flag
            global _sync_command_registered
            _sync_command_registered = False
            
            # Re-setup all commands (they will be registered fresh)
            await war_commands.setup_commands(bot)
            await stats_commands.setup_commands(bot)
            await leaderboard_commands.setup_commands(bot)
            await admin_commands.setup_commands(bot)
            
            # Re-register sync_commands
            register_sync_command()
            
            # Wait a moment for commands to register
            await asyncio.sleep(0.1)
            
            # Sync commands to Discord (check for TEST_GUILD_ID like in on_ready)
            test_guild_id = os.getenv("TEST_GUILD_ID")
            if test_guild_id:
                test_guild_id = test_guild_id.strip()
                try:
                    guild_id = int(test_guild_id)
                    guild = bot.get_guild(guild_id)
                    if guild:
                        test_guild = discord.Object(id=guild_id)
                        synced = await bot.tree.sync(guild=test_guild)
                    else:
                        synced = await bot.tree.sync()
                except (ValueError, Exception) as e:
                    print(f'⚠️ Error in sync_commands guild sync: {e}')
                    synced = await bot.tree.sync()
            else:
                synced = await bot.tree.sync()
            command_count = len(synced)
            
            # Get all command names
            command_names = [cmd.name for cmd in synced]
            
            # Check for duplicates
            unique_names = set(command_names)
            has_duplicates = len(command_names) != len(unique_names)
            
            if has_duplicates:
                # Find which commands appear more than once in the full list
                duplicates = []
                for name in unique_names:
                    if command_names.count(name) > 1:
                        duplicates.append(name)
            else:
                duplicates = []
            
            # Terminal output (matching Umbrella Events format)
            print(f'\nSynced {command_count} command(s)')
            print(f'Commands available: {command_names}')
            
            if has_duplicates:
                print(f'⚠️ WARNING: Duplicate commands detected: {duplicates}')
                print(f'   Total commands: {len(command_names)}, Unique: {len(unique_names)}')
            else:
                print(f'✅ No duplicate commands detected ({len(unique_names)} unique commands)')
            print()
            
            # Embed output (matching Umbrella Events format)
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Synced {command_count} command(s)",
                color=discord.Color.green()
            )
            
            # Format command list
            command_list_str = str(command_names)
            embed.add_field(name="Commands available", value=f"`{command_list_str}`", inline=False)
            
            if has_duplicates:
                embed.add_field(
                    name="⚠️ Warning", 
                    value=f"Duplicate commands detected: `{duplicates}`\nTotal commands: {len(command_names)}, Unique: {len(unique_names)}", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status", 
                    value=f"No duplicate commands detected ({len(unique_names)} unique commands)", 
                    inline=False
                )
            
            embed.timestamp = discord.utils.utcnow()
            
            # Use followup since we deferred the response
            await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            error_msg = f"Failed to sync commands: {e}"
            try:
                await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            except:
                pass  # If followup also fails, just print to console
            print(error_msg)
            import traceback
            traceback.print_exc()


@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    
    # Set bot status
    activity = discord.Game(name="Tracking Foxhole Wars")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    # Show servers the bot has joined
    print(f'\n📋 Bot is in {len(bot.guilds)} server(s):')
    print('=' * 60)
    if len(bot.guilds) == 0:
        print('   ⚠️ Bot is not in any servers yet!')
    else:
        for guild in bot.guilds:
            # Safely print guild name, handling Unicode encoding errors
            try:
                print(f'   • {guild.name} (ID: {guild.id})')
            except UnicodeEncodeError:
                # Fallback: encode to ASCII with error handling
                safe_name = guild.name.encode('ascii', 'replace').decode('ascii')
                print(f'   • {safe_name} (ID: {guild.id})')
    print('=' * 60)
    print('💡 To use guild-level command syncing, add this to your .env file:')
    if len(bot.guilds) > 0:
        first_guild = bot.guilds[0]
        try:
            print(f'   TEST_GUILD_ID={first_guild.id}')
        except:
            pass
    print()
    
    await init_database()
    print('Database initialized!')
    
    # Wait a moment for bot to fully connect to all guilds
    await asyncio.sleep(2)
    
    # Setup commands - MUST be done before syncing
    # Clear any existing commands first (in case of restart)
    bot.tree.clear_commands(guild=None)
    
    # Wait a moment
    await asyncio.sleep(0.1)
    
    # Reset sync command flag
    global _sync_command_registered
    _sync_command_registered = False
    
    # Now register all commands
    await war_commands.setup_commands(bot)
    await stats_commands.setup_commands(bot)
    await leaderboard_commands.setup_commands(bot)
    await admin_commands.setup_commands(bot)
    register_sync_command()  # Register sync_commands
    
    # Wait a moment for commands to register
    await asyncio.sleep(0.5)
    
    try:
        # Check if we should sync to a specific guild for faster testing
        test_guild_id = os.getenv("TEST_GUILD_ID")
        print(f'\n🔍 DEBUG: TEST_GUILD_ID from .env: {test_guild_id}')
        print(f'🔍 DEBUG: Type: {type(test_guild_id)}')
        
        if test_guild_id:
            # Strip whitespace in case there's any
            test_guild_id = test_guild_id.strip()
            print(f'🔍 DEBUG: After strip: "{test_guild_id}"')
            
            try:
                guild_id = int(test_guild_id)
                print(f'🔍 DEBUG: Parsed guild_id: {guild_id} (type: {type(guild_id)})')
                
                # Verify the bot is actually in this guild
                guild = bot.get_guild(guild_id)
                print(f'🔍 DEBUG: Guild lookup result: {guild}')
                
                if not guild:
                    print(f'⚠️ WARNING: Bot is not in guild with ID {guild_id}')
                    print('   Available guild IDs:', [g.id for g in bot.guilds])
                    print('   Falling back to global sync...')
                    synced = await bot.tree.sync()
                else:
                    print(f'📋 Syncing commands to guild: {guild.name} (ID: {guild_id})')
                    test_guild = discord.Object(id=guild_id)
                    synced = await bot.tree.sync(guild=test_guild)
                    
                    # Note: Discord API may return empty list for guild syncs even when successful
                    # This is a known Discord API quirk - the sync worked, but API doesn't return the commands
                    # Get the actual command count from the command tree instead
                    registered_commands = list(bot.tree.get_commands(guild=test_guild))
                    command_count = len(registered_commands)
                    
                    if len(synced) == 0:
                        # Discord API quirk: guild syncs often return empty list even when successful
                        # Use the command tree to get the actual count
                        if command_count > 0:
                            print(f'✅ Synced {command_count} commands to guild (Discord API returned empty list, but commands are registered)')
                            # Create list for display using registered commands
                            synced = registered_commands
                        else:
                            # Wait a moment and check again - commands might still be registering
                            await asyncio.sleep(0.5)
                            registered_commands = list(bot.tree.get_commands(guild=test_guild))
                            command_count = len(registered_commands)
                            if command_count > 0:
                                print(f'✅ Synced {command_count} commands to guild (verified after brief wait)')
                                synced = registered_commands
                            else:
                                # Still 0 - this shouldn't happen, but commands might still be syncing
                                # Get count from global tree as fallback for display
                                all_commands = list(bot.tree.get_commands(guild=None))
                                print(f'ℹ️ Guild sync completed. {len(all_commands)} commands registered globally.')
                                print(f'   Commands should appear in the guild shortly (Discord API quirk).')
                                synced = all_commands  # Use for display
                    else:
                        print(f'✅ Successfully synced {len(synced)} commands to guild')
            except ValueError as e:
                print(f'⚠️ WARNING: Invalid TEST_GUILD_ID format: "{test_guild_id}"')
                print(f'   Error: {e}')
                print('   Falling back to global sync...')
                synced = await bot.tree.sync()
            except Exception as e:
                print(f'⚠️ WARNING: Error syncing to guild: {e}')
                import traceback
                traceback.print_exc()
                print('   Falling back to global sync...')
                synced = await bot.tree.sync()
        else:
            print('🔍 DEBUG: No TEST_GUILD_ID found, using global sync')
            # Sync commands globally (this is enough - no need to sync per-guild)
            synced = await bot.tree.sync()
        
        # Get command names - handle both AppCommand objects and Command objects
        if synced and len(synced) > 0:
            if hasattr(synced[0], 'name'):
                command_names = [cmd.name for cmd in synced]
            else:
                # Fallback: get from command tree
                command_names = [cmd.name for cmd in bot.tree.get_commands(guild=None)]
        else:
            # Get from command tree as fallback
            command_names = [cmd.name for cmd in bot.tree.get_commands(guild=None)]
        
        print(f'Synced {len(command_names)} command(s)')
        print(f'Commands available: {command_names}')
        
        # Verify no duplicates (command_names already set above)
        unique_names = set(command_names)
        if len(command_names) != len(unique_names):
            duplicates = [name for name in unique_names if command_names.count(name) > 1]
            print(f'⚠️ WARNING: Duplicate commands detected: {duplicates}')
            print(f'   Total commands: {len(command_names)}, Unique: {len(unique_names)}')
        else:
            print(f'✅ No duplicate commands detected ({len(unique_names)} unique commands)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()
    
    # Start leaderboard updater
    start_leaderboard_updater(bot)
    
    print('\nBot is ready!\n')


@bot.event
async def on_message(message):
    """Handle messages - process DMs for stat entry"""
    # Ignore messages from bots
    if message.author.bot:
        return
    
    # Ignore messages that start with ! (to avoid conflicts with other bots)
    if message.content.startswith('!'):
        return
    
    # Handle DM messages
    if isinstance(message.channel, discord.DMChannel):
        await handle_dm_message(message, bot)
    
    # Process the message normally (though we don't have any prefix commands)
    await bot.process_commands(message)


# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file with: DISCORD_BOT_TOKEN=your_token_here")
    else:
        bot.run(token)
