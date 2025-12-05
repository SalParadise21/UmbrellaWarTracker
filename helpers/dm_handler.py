"""DM message handler for stat entry interactions"""
import discord
import re
from typing import Dict

from helpers.database import update_user_stats, set_user_stat
from helpers.embed_helper import create_stat_update_embed


# Store active DM interactions
active_dm_sessions: Dict[int, Dict] = {}  # {user_id: {'war_id': int, 'mode': 'manual_step'|'edit', 'current_stat': str, 'stats': dict, 'stat_index': int, 'editing_stats': dict}}

# List of all stats in order
STAT_ORDER = [
    'enemy_player_damage',
    'friendly_player_damage',
    'enemy_structure_vehicle_damage',
    'friendly_structure_vehicle_damage',
    'friendly_construction',
    'friendly_repairing',
    'friendly_healing',
    'friendly_revivals',
    'vehicles_captured_by_enemy',
    'vehicle_self_damage_neutral',
    'vehicle_self_damage_colonial',
    'vehicle_self_damage_warden',
    'materials_submitted',
    'materials_gathered',
    'supply_value_delivered'
]

# Human-readable stat names
STAT_NAMES = {
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


async def handle_dm_message(message: discord.Message, bot):
    """Handle incoming DM messages for stat entry"""
    user_id = message.author.id
    
    # Check if user has an active session
    if user_id not in active_dm_sessions:
        return False
    
    session = active_dm_sessions[user_id]
    
    # Handle cancel
    if message.content.lower() == 'cancel':
        del active_dm_sessions[user_id]
        await message.channel.send("Stat entry cancelled.")
        return True
    
    # Handle skip (for manual step-by-step entry)
    if message.content.lower() == 'skip' and session.get('mode') == 'manual_step':
        # Use 0 for skipped stat
        if 'stats' not in session:
            session['stats'] = {}
        session['stats'][session['current_stat']] = 0
        
        # Move to next stat
        session['stat_index'] += 1
        
        # Check if we're done
        if session['stat_index'] >= len(STAT_ORDER):
            # All stats collected, save them
            await update_user_stats(
                user_id,
                session['war_id'],
                **session['stats']
            )
            del active_dm_sessions[user_id]
            
            embed = create_stat_update_embed(session['stats'])
            await message.channel.send(
                "✅ All stats have been recorded!",
                embed=embed
            )
            return True
        else:
            # Ask for next stat
            next_stat = STAT_ORDER[session['stat_index']]
            session['current_stat'] = next_stat
            
            progress = f"({session['stat_index']}/{len(STAT_ORDER)})"
            embed = discord.Embed(
                title=f"📊 Stat Entry {progress}",
                description=f"**{STAT_NAMES[next_stat]}**\n\n"
                           f"Please enter the value for this stat.\n"
                           f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
                color=discord.Color.blue()
            )
            await message.channel.send(embed=embed)
            return True
    
    # Handle manual step-by-step entry mode
    if session['mode'] == 'manual_step':
        try:
            # Try to extract a number from the message
            content = message.content.strip()
            
            # Look for any number in the message
            numbers = re.findall(r'\d+', content)
            if not numbers:
                await message.channel.send(
                    "❌ I couldn't find a number in your message. Please enter just the number (e.g., `1000` or `0`).\n"
                    f"Current stat: **{STAT_NAMES.get(session['current_stat'], session['current_stat'])}**"
                )
                return True
            
            # Use the first number found
            stat_value = int(numbers[0])
            
            # Store the stat
            if 'stats' not in session:
                session['stats'] = {}
            session['stats'][session['current_stat']] = stat_value
            
            # Move to next stat
            session['stat_index'] += 1
            
            # Check if we're done
            if session['stat_index'] >= len(STAT_ORDER):
                # All stats collected, save them
                await update_user_stats(
                    user_id,
                    session['war_id'],
                    **session['stats']
                )
                del active_dm_sessions[user_id]
                
                embed = create_stat_update_embed(session['stats'])
                await message.channel.send(
                    "✅ All stats have been recorded!",
                    embed=embed
                )
                return True
            else:
                # Ask for next stat
                next_stat = STAT_ORDER[session['stat_index']]
                session['current_stat'] = next_stat
                
                progress = f"({session['stat_index']}/{len(STAT_ORDER)})"
                embed = discord.Embed(
                    title=f"📊 Stat Entry {progress}",
                    description=f"**{STAT_NAMES[next_stat]}**\n\n"
                               f"Please enter the value for this stat.\n"
                               f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
                return True
                
        except ValueError:
            await message.channel.send(
                "❌ Please enter a valid number. You can also type `skip` to use 0 for this stat."
            )
            return True
        except Exception as e:
            await message.channel.send(f"❌ Error processing stat: {str(e)}")
            return True
    
    # Handle edit mode
    if session['mode'] == 'edit':
        try:
            # Check if we're waiting for a stat selection or value input
            if 'waiting_for_stat_selection' in session and session['waiting_for_stat_selection']:
                # User should have clicked a button, this shouldn't happen via text
                await message.channel.send(
                    "Please use the buttons above to select which stat you'd like to edit, or type `cancel` to cancel."
                )
                return True
            
            if 'waiting_for_value' in session and session['waiting_for_value']:
                # User is entering a new value for a stat
                content = message.content.strip()
                
                # Handle cancel
                if content.lower() == 'cancel':
                    del active_dm_sessions[user_id]
                    await message.channel.send("Stat editing cancelled.")
                    return True
                
                # Extract number
                numbers = re.findall(r'\d+', content)
                if not numbers:
                    current_val = session['editing_stats'].get(session['editing_stat'], 0)
                    await message.channel.send(
                        f"❌ I couldn't find a number in your message. Please enter the new value for **{STAT_NAMES.get(session['editing_stat'], session['editing_stat'])}**.\n"
                        f"Current value: **{int(current_val):,}**\n"
                        f"Type `cancel` to cancel."
                    )
                    return True
                
                new_value = int(numbers[0])
                stat_name = session['editing_stat']
                
                # Update the stat in the editing stats dict
                session['editing_stats'][stat_name] = new_value
                
                # Update in database
                await set_user_stat(user_id, session['war_id'], stat_name, new_value)
                
                # Ask if they want to edit more
                embed = discord.Embed(
                    title="✅ Stat Updated",
                    description=f"**{STAT_NAMES[stat_name]}** has been updated to **{int(new_value):,}**.\n\n"
                               f"Would you like to edit another stat?",
                    color=discord.Color.green()
                )
                
                # Create view with Yes/No buttons
                from discord.ui import View, Button
                
                class EditMoreView(View):
                    def __init__(self, user_id, war_id, war_number, editing_stats):
                        super().__init__(timeout=300)
                        self.user_id = user_id
                        self.war_id = war_id
                        self.war_number = war_number
                        self.editing_stats = editing_stats
                    
                    @discord.ui.button(label="Yes, edit another", style=discord.ButtonStyle.green)
                    async def yes_button(self, interaction: discord.Interaction, button: Button):
                        await interaction.response.defer(ephemeral=True)
                        # Reload stats from database to ensure we have latest values
                        from helpers.database import get_user_stats
                        updated_stats = await get_user_stats(self.user_id, self.war_id)
                        # Restart edit flow with updated stats
                        await start_edit_flow(
                            interaction.channel,
                            self.user_id,
                            self.war_id,
                            self.war_number,
                            updated_stats,
                            show_current=True
                        )
                        await interaction.followup.send("Select which stat you'd like to edit next.", ephemeral=True)
                        self.stop()
                    
                    @discord.ui.button(label="No, I'm done", style=discord.ButtonStyle.red)
                    async def no_button(self, interaction: discord.Interaction, button: Button):
                        await interaction.response.defer(ephemeral=True)
                        # Save all edits and end
                        if self.user_id in active_dm_sessions:
                            del active_dm_sessions[self.user_id]
                        
                        from helpers.embed_helper import create_stat_update_embed
                        final_embed = create_stat_update_embed(self.editing_stats)
                        await interaction.channel.send(
                            "✅ All stats have been updated! Here's your final stats:",
                            embed=final_embed
                        )
                        await interaction.followup.send("✅ Stats updated successfully!", ephemeral=True)
                        self.stop()
                
                view = EditMoreView(user_id, session['war_id'], session.get('war_number', 'Unknown'), session['editing_stats'])
                await message.channel.send(embed=embed, view=view)
                
                # Clear waiting flags
                session['waiting_for_value'] = False
                session.pop('editing_stat', None)
                
                return True
                
        except ValueError:
            await message.channel.send("❌ Please enter a valid number.")
            return True
        except Exception as e:
            await message.channel.send(f"❌ Error processing edit: {str(e)}")
            return True
    
    # Handle old manual entry mode (for backwards compatibility)
    if session['mode'] == 'manual':
        # This mode is deprecated but kept for compatibility
        await message.channel.send(
            "⚠️ This entry method is no longer supported. Please use /stats_entry and select 'Manual Entry'."
        )
        del active_dm_sessions[user_id]
        return True
    
    return False


def end_dm_session(user_id: int):
    """End a DM session"""
    if user_id in active_dm_sessions:
        del active_dm_sessions[user_id]


async def start_manual_entry_flow(channel: discord.DMChannel, user_id: int, war_id: int, war_number: int):
    """Start the step-by-step manual entry flow"""
    # Check if user already has an active session to prevent duplicates
    if user_id in active_dm_sessions:
        # User already has an active session, don't start a new one
        return
    
    # Initialize session for step-by-step entry
    active_dm_sessions[user_id] = {
        'war_id': war_id,
        'mode': 'manual_step',
        'current_stat': STAT_ORDER[0],
        'stats': {},
        'stat_index': 0
    }
    
    # Send first stat question
    progress = f"(1/{len(STAT_ORDER)})"
    embed = discord.Embed(
        title=f"📊 Manual Stat Entry - War {war_number}",
        description=f"**{STAT_NAMES[STAT_ORDER[0]]}**\n\n"
                   f"I'll ask you for each stat one by one.\n"
                   f"Please enter the value for this stat.\n\n"
                   f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)


async def start_edit_flow(channel: discord.DMChannel, user_id: int, war_id: int, war_number: int, current_stats: Dict, show_current: bool = False):
    """Start the stat editing flow"""
    import discord
    from discord.ui import View, Button
    
    # Convert stats dict to only include stat values (remove metadata)
    editing_stats = {}
    for stat in STAT_ORDER:
        editing_stats[stat] = current_stats.get(stat, 0)
    
    # Initialize edit session
    active_dm_sessions[user_id] = {
        'war_id': war_id,
        'war_number': war_number,
        'mode': 'edit',
        'editing_stats': editing_stats,
        'waiting_for_stat_selection': True,
        'waiting_for_value': False
    }
    
    # Create view with buttons for each stat
    view = View(timeout=300)
    
    # Add buttons for all stats (Discord limit is 25, we have 15)
    for stat in STAT_ORDER:
        # Create a closure to capture the stat name
        def make_callback(stat_name):
            async def button_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True)
                
                # Update session
                if user_id in active_dm_sessions:
                    session = active_dm_sessions[user_id]
                    session['waiting_for_stat_selection'] = False
                    session['waiting_for_value'] = True
                    session['editing_stat'] = stat_name
                
                # Ask for new value
                current_val = editing_stats[stat_name]
                embed = discord.Embed(
                    title="✏️ Edit Stat",
                    description=f"**{STAT_NAMES[stat_name]}**\n\n"
                               f"Current value: **{int(current_val):,}**\n\n"
                               f"Please enter the new value for this stat.\n"
                               f"Type `cancel` to cancel.",
                    color=discord.Color.blue()
                )
                await interaction.channel.send(embed=embed)
                await interaction.followup.send("Enter the new value in the chat.", ephemeral=True)
            
            return button_callback
        
        stat_value = editing_stats[stat]
        button = Button(
            label=f"{STAT_NAMES[stat]}: {int(stat_value):,}",
            style=discord.ButtonStyle.secondary
        )
        button.callback = make_callback(stat)
        view.add_item(button)
    
    # Create initial embed
    if show_current:
        stats_text = "\n".join([f"**{STAT_NAMES[stat]}**: {int(editing_stats[stat]):,}" for stat in STAT_ORDER[:10]])
        if len(STAT_ORDER) > 10:
            stats_text += f"\n... and {len(STAT_ORDER) - 10} more stats"
        
        embed = discord.Embed(
            title=f"✏️ Edit Stats - War {war_number}",
            description=f"Select which stat you'd like to edit:\n\n{stats_text}",
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title=f"✏️ Edit Stats - War {war_number}",
            description="Select which stat you'd like to edit from the buttons below.\n\n"
                       "Click a button to edit that stat's value.\n"
                       "Type `cancel` to cancel.",
            color=discord.Color.blue()
        )
    
    await channel.send(embed=embed, view=view)

