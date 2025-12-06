"""DM message handler for stat entry interactions"""
import discord
import re
import time
from typing import Dict, Optional, Tuple

from helpers.database import update_user_stats, set_user_stat
from helpers.embed_helper import create_stat_update_embed


# Store active DM interactions
active_dm_sessions: Dict[int, Dict] = {}  # {user_id: {'war_id': int, 'mode': 'manual_step'|'edit', 'current_stat': str, 'stats': dict, 'stat_index': int, 'editing_stats': dict}}

# Rate limiting for "Skip" responses: {user_id: last_skip_timestamp}
skip_rate_limit: Dict[int, float] = {}
SKIP_RATE_LIMIT_SECONDS = 2.0  # Ignore "Skip" if sent within 2 seconds of previous "Skip"

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

# Validation constants
MIN_STAT_VALUE = 0
MAX_STAT_VALUE = 999999999


def validate_stat_input(content: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate stat input according to data governance rules.
    
    Rules:
    - Only numbers allowed (no text, spaces, hyphens)
    - Value must be >= 0 and <= 999,999,999
    
    Returns:
        Tuple of (is_valid, value, error_message)
        - is_valid: True if input is valid
        - value: The parsed integer value if valid, None otherwise
        - error_message: Error message if invalid, None otherwise
    """
    content = content.strip()
    
    # Check for empty input
    if not content:
        return False, None, "Input cannot be empty. Please enter a number between 0 and 999,999,999."
    
    # Check for spaces
    if ' ' in content:
        return False, None, "❌ **Invalid input**: Spaces are not allowed.\n\nPlease enter only numbers (0-999,999,999) with no spaces, text, or hyphens."
    
    # Check for hyphens
    if '-' in content:
        return False, None, "❌ **Invalid input**: Hyphens are not allowed.\n\nPlease enter only numbers (0-999,999,999) with no spaces, text, or hyphens."
    
    # Check if content contains only digits
    if not content.isdigit():
        return False, None, "❌ **Invalid input**: Only numbers are allowed (no text, spaces, or hyphens).\n\nPlease enter a number between 0 and 999,999,999."
    
    # Parse the number
    try:
        value = int(content)
    except ValueError:
        return False, None, "❌ **Invalid input**: Could not parse number.\n\nPlease enter a number between 0 and 999,999,999."
    
    # Check range
    if value < MIN_STAT_VALUE:
        return False, None, f"❌ **Invalid input**: Value must be >= {MIN_STAT_VALUE:,}.\n\nPlease enter a number between 0 and 999,999,999."
    
    if value > MAX_STAT_VALUE:
        return False, None, f"❌ **Invalid input**: Value must be <= {MAX_STAT_VALUE:,}.\n\nPlease enter a number between 0 and 999,999,999."
    
    return True, value, None


def check_skip_rate_limit(user_id: int) -> bool:
    """
    Check if "Skip" command should be rate limited.
    
    Returns:
        True if "Skip" should be processed, False if it should be ignored
    """
    current_time = time.time()
    
    if user_id in skip_rate_limit:
        last_skip_time = skip_rate_limit[user_id]
        if current_time - last_skip_time < SKIP_RATE_LIMIT_SECONDS:
            # Rate limited - ignore this skip
            return False
    
    # Update last skip time
    skip_rate_limit[user_id] = current_time
    return True


def reset_skip_rate_limit(user_id: int):
    """Reset the skip rate limit for a user (call when new prompt is sent)"""
    skip_rate_limit.pop(user_id, None)


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
        reset_skip_rate_limit(user_id)
        await message.channel.send("Stat entry cancelled.")
        return True
    
    # Handle screenshot submission
    if session.get('mode') == 'screenshot':
        # Check if message has image attachments
        if message.attachments:
            image_attachment = None
            for attachment in message.attachments:
                # Check if it's an image
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    image_attachment = attachment
                    break
            
            if image_attachment:
                # Process the image
                await message.channel.send("📷 Processing screenshot... This may take a moment.")
                
                try:
                    # Download the image
                    image_bytes = await image_attachment.read()
                    
                    # Extract stats from image
                    from helpers.screenshot_processor import extract_stats_from_image, OCR_AVAILABLE
                    
                    if not OCR_AVAILABLE:
                        await message.channel.send(
                            "❌ Screenshot processing is not available. Please install pytesseract and Pillow, "
                            "or use manual entry instead."
                        )
                        del active_dm_sessions[user_id]
                        return True
                    
                    extracted_stats, error_message = extract_stats_from_image(image_bytes)
                    
                    if not extracted_stats or len(extracted_stats) == 0:
                        # Create error embed with buttons
                        error_description = "Could not extract stats from the screenshot.\n\n"
                        if error_message:
                            # Truncate error message if too long
                            error_preview = error_message[:200] + "..." if len(error_message) > 200 else error_message
                            error_description += f"**Details:** {error_preview}\n\n"
                        error_description += (
                            "**What would you like to do?**\n\n"
                            "• **Manual Entry**: Enter stats manually one by one\n"
                            "• **Re-run Submit Screenshot**: Try submitting a new screenshot\n"
                            "• **Cancel**: Cancel stat entry"
                        )
                        
                        embed = discord.Embed(
                            title="❌ Could Not Extract Stats",
                            description=error_description,
                            color=discord.Color.red()
                        )
                        
                        # Create view with buttons
                        from discord.ui import View, Button
                        
                        class ExtractionErrorView(View):
                            def __init__(self, user_id, war_id, war_number, dm_channel):
                                super().__init__(timeout=300)
                                self.user_id = user_id
                                self.war_id = war_id
                                self.war_number = war_number
                                self.dm_channel = dm_channel
                            
                            @discord.ui.button(label="✏️ Manual Entry", style=discord.ButtonStyle.green)
                            async def manual_button(self, interaction: discord.Interaction, button: Button):
                                await interaction.response.defer(ephemeral=False)
                                
                                # Start manual entry flow
                                await start_manual_entry_flow(
                                    interaction.channel,
                                    self.user_id,
                                    self.war_id,
                                    self.war_number
                                )
                                
                                await interaction.followup.send("Starting manual entry flow.", ephemeral=False)
                                self.stop()
                            
                            @discord.ui.button(label="📷 Re-run Submit Screenshot", style=discord.ButtonStyle.blurple)
                            async def rerun_button(self, interaction: discord.Interaction, button: Button):
                                await interaction.response.defer(ephemeral=False)
                                
                                # Restart screenshot flow
                                await start_screenshot_flow(
                                    interaction.channel,
                                    self.user_id,
                                    self.war_id,
                                    self.war_number
                                )
                                
                                await interaction.followup.send("Please submit a new screenshot.", ephemeral=False)
                                self.stop()
                            
                            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
                            async def cancel_button(self, interaction: discord.Interaction, button: Button):
                                await interaction.response.defer(ephemeral=False)
                                
                                # Clean up session
                                if self.user_id in active_dm_sessions:
                                    del active_dm_sessions[self.user_id]
                                reset_skip_rate_limit(self.user_id)
                                
                                await interaction.channel.send("❌ Stat entry cancelled.")
                                await interaction.followup.send("Cancelled.", ephemeral=False)
                                self.stop()
                        
                        view = ExtractionErrorView(user_id, session['war_id'], session.get('war_number', 'Unknown'), message.channel)
                        await message.channel.send(embed=embed, view=view)
                        # Don't delete the session here - let the buttons handle it
                        return True
                    
                    # Initialize all stats to 0, then update with extracted values
                    all_stats = {stat: 0 for stat in STAT_ORDER}
                    for stat, value in extracted_stats.items():
                        if stat in STAT_ORDER:
                            all_stats[stat] = value
                    
                    # Store extracted stats in session
                    session['extracted_stats'] = all_stats
                    session['waiting_for_confirmation'] = True
                    
                    # Create embed with all extracted stats
                    embed = create_stat_update_embed(all_stats)
                    embed.title = "📷 Extracted Stats from Screenshot"
                    embed.description = "Please review the extracted stats below. Are these values correct?"
                    
                    # Create confirmation view with Yes/No buttons
                    from discord.ui import View, Button
                    
                    class ScreenshotConfirmView(View):
                        def __init__(self, user_id, war_id, war_number, extracted_stats, dm_channel):
                            super().__init__(timeout=300)
                            self.user_id = user_id
                            self.war_id = war_id
                            self.war_number = war_number
                            self.extracted_stats = extracted_stats
                            self.dm_channel = dm_channel
                        
                        @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.green)
                        async def yes_button(self, interaction: discord.Interaction, button: Button):
                            await interaction.response.defer(ephemeral=False)
                            
                            # Save the stats
                            await update_user_stats(
                                self.user_id,
                                self.war_id,
                                **self.extracted_stats
                            )
                            
                            # Clean up session
                            if self.user_id in active_dm_sessions:
                                del active_dm_sessions[self.user_id]
                            reset_skip_rate_limit(self.user_id)
                            
                            # Show confirmation
                            final_embed = create_stat_update_embed(self.extracted_stats)
                            await interaction.channel.send(
                                "✅ Stats have been saved from your screenshot!",
                                embed=final_embed
                            )
                            await interaction.followup.send("✅ Stats saved successfully!", ephemeral=False)
                            self.stop()
                        
                        @discord.ui.button(label="❌ No", style=discord.ButtonStyle.red)
                        async def no_button(self, interaction: discord.Interaction, button: Button):
                            await interaction.response.defer(ephemeral=False)
                            
                            # Ask if they want to rerun image processing or do manual entry
                            embed = discord.Embed(
                                title="📷 Stats Not Correct",
                                description="What would you like to do?\n\n"
                                           "• **Rerun Image Processing**: Submit a new screenshot\n"
                                           "• **Manual Entry**: Enter stats manually one by one",
                                color=discord.Color.orange()
                            )
                            
                            class RetryChoiceView(View):
                                def __init__(self, user_id, war_id, war_number, dm_channel):
                                    super().__init__(timeout=300)
                                    self.user_id = user_id
                                    self.war_id = war_id
                                    self.war_number = war_number
                                    self.dm_channel = dm_channel
                                
                                @discord.ui.button(label="📷 Rerun Image Processing", style=discord.ButtonStyle.blurple)
                                async def rerun_button(self, interaction: discord.Interaction, button: Button):
                                    await interaction.response.defer(ephemeral=False)
                                    
                                    # Restart screenshot flow
                                    await start_screenshot_flow(
                                        interaction.channel,
                                        self.user_id,
                                        self.war_id,
                                        self.war_number
                                    )
                                    
                                    await interaction.followup.send("Please submit a new screenshot.", ephemeral=False)
                                    self.stop()
                                
                                @discord.ui.button(label="✏️ Manual Entry", style=discord.ButtonStyle.green)
                                async def manual_button(self, interaction: discord.Interaction, button: Button):
                                    await interaction.response.defer(ephemeral=False)
                                    
                                    # Start manual entry flow
                                    await start_manual_entry_flow(
                                        interaction.channel,
                                        self.user_id,
                                        self.war_id,
                                        self.war_number
                                    )
                                    
                                    await interaction.followup.send("Starting manual entry flow.", ephemeral=False)
                                    self.stop()
                                
                                @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
                                async def cancel_button(self, interaction: discord.Interaction, button: Button):
                                    await interaction.response.defer(ephemeral=False)
                                    
                                    # Clean up session
                                    if self.user_id in active_dm_sessions:
                                        del active_dm_sessions[self.user_id]
                                    reset_skip_rate_limit(self.user_id)
                                    
                                    await interaction.channel.send("❌ Stat entry cancelled.")
                                    await interaction.followup.send("Cancelled.", ephemeral=False)
                                    self.stop()
                            
                            retry_view = RetryChoiceView(self.user_id, self.war_id, self.war_number, self.dm_channel)
                            await interaction.channel.send(embed=embed, view=retry_view)
                            await interaction.followup.send("Please choose an option.", ephemeral=False)
                            self.stop()
                    
                    view = ScreenshotConfirmView(user_id, session['war_id'], session.get('war_number', 'Unknown'), all_stats, message.channel)
                    await message.channel.send(embed=embed, view=view)
                    return True
                except Exception as e:
                    await message.channel.send(
                        f"❌ Error processing screenshot: {str(e)}\n\n"
                        f"Please try again or use manual entry instead."
                    )
                    del active_dm_sessions[user_id]
                    return True
            else:
                await message.channel.send(
                    "❌ Please send an image file. Supported formats: PNG, JPG, JPEG, GIF, WEBP\n\n"
                    f"Type `cancel` to cancel."
                )
                return True
        else:
            await message.channel.send(
                "📷 Please attach a screenshot of your stats.\n\n"
                f"Type `cancel` to cancel."
            )
            return True
    
    # Handle skip (for manual step-by-step entry) with rate limiting
    if message.content.lower() == 'skip' and session.get('mode') == 'manual_step':
        # Check rate limit
        if not check_skip_rate_limit(user_id):
            # Rate limited - ignore this skip
            return True
        
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
            reset_skip_rate_limit(user_id)
            
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
                           f"Please enter the value for this stat.\n\n"
                           f"**Requirements:**\n"
                           f"• Numbers only (0-999,999,999)\n"
                           f"• No spaces, text, or hyphens\n"
                           f"• Value must be >= 0 and <= 999,999,999\n\n"
                           f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
                color=discord.Color.blue()
            )
            await message.channel.send(embed=embed)
            # Reset rate limit when new prompt is sent
            reset_skip_rate_limit(user_id)
            return True
    
    # Handle manual step-by-step entry mode
    if session['mode'] == 'manual_step':
        try:
            content = message.content.strip()
            
            # Validate input using data governance rules
            is_valid, stat_value, error_message = validate_stat_input(content)
            
            if not is_valid:
                # Show error and reprompt
                current_stat_name = STAT_NAMES.get(session['current_stat'], session['current_stat'])
                progress = f"({session['stat_index'] + 1}/{len(STAT_ORDER)})"
                embed = discord.Embed(
                    title=f"📊 Stat Entry {progress}",
                    description=f"**{current_stat_name}**\n\n"
                               f"{error_message}\n\n"
                               f"**Requirements:**\n"
                               f"• Numbers only (0-999,999,999)\n"
                               f"• No spaces, text, or hyphens\n"
                               f"• Value must be >= 0 and <= 999,999,999\n\n"
                               f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                return True
            
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
                reset_skip_rate_limit(user_id)
                
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
                               f"Please enter the value for this stat.\n\n"
                               f"**Requirements:**\n"
                               f"• Numbers only (0-999,999,999)\n"
                               f"• No spaces, text, or hyphens\n"
                               f"• Value must be >= 0 and <= 999,999,999\n\n"
                               f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
                # Reset rate limit when new prompt is sent
                reset_skip_rate_limit(user_id)
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
                    reset_skip_rate_limit(user_id)
                    await message.channel.send("Stat editing cancelled.")
                    return True
                
                # Validate input using data governance rules
                is_valid, new_value, error_message = validate_stat_input(content)
                
                if not is_valid:
                    # Show error and reprompt
                    stat_name = session['editing_stat']
                    current_val = session['editing_stats'].get(stat_name, 0)
                    embed = discord.Embed(
                        title="✏️ Edit Stat",
                        description=f"**{STAT_NAMES[stat_name]}**\n\n"
                                   f"Current value: **{int(current_val):,}**\n\n"
                                   f"{error_message}\n\n"
                                   f"**Requirements:**\n"
                                   f"• Numbers only (0-999,999,999)\n"
                                   f"• No spaces, text, or hyphens\n"
                                   f"• Value must be >= 0 and <= 999,999,999\n\n"
                                   f"Please enter the new value for this stat.\n"
                                   f"Type `cancel` to cancel.",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed)
                    return True
                
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
                        await interaction.response.defer(ephemeral=False)
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
                        await interaction.followup.send("Select which stat you'd like to edit next.", ephemeral=False)
                        self.stop()
                    
                    @discord.ui.button(label="No, I'm done", style=discord.ButtonStyle.red)
                    async def no_button(self, interaction: discord.Interaction, button: Button):
                        await interaction.response.defer(ephemeral=False)
                        # Save all edits and end
                        if self.user_id in active_dm_sessions:
                            del active_dm_sessions[self.user_id]
                        
                        from helpers.embed_helper import create_stat_update_embed
                        final_embed = create_stat_update_embed(self.editing_stats)
                        await interaction.channel.send(
                            "✅ All stats have been updated! Here's your final stats:",
                            embed=final_embed
                        )
                        await interaction.followup.send("✅ Stats updated successfully!", ephemeral=False)
                        self.stop()
                
                view = EditMoreView(user_id, session['war_id'], session.get('war_number', 'Unknown'), session['editing_stats'])
                await message.channel.send(embed=embed, view=view)
                
                # Clear waiting flags
                session['waiting_for_value'] = False
                session.pop('editing_stat', None)
                
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
                   f"**Requirements:**\n"
                   f"• Numbers only (0-999,999,999)\n"
                   f"• No spaces, text, or hyphens\n"
                   f"• Value must be >= 0 and <= 999,999,999\n\n"
                   f"Type `cancel` to cancel, or `skip` to skip this stat (use 0).",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)
    # Reset rate limit when new prompt is sent
    reset_skip_rate_limit(user_id)


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
                await interaction.response.defer(ephemeral=False)
                
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
                               f"Please enter the new value for this stat.\n\n"
                               f"**Requirements:**\n"
                               f"• Numbers only (0-999,999,999)\n"
                               f"• No spaces, text, or hyphens\n"
                               f"• Value must be >= 0 and <= 999,999,999\n\n"
                               f"Type `cancel` to cancel.",
                    color=discord.Color.blue()
                )
                await interaction.channel.send(embed=embed)
                # Reset rate limit when new prompt is sent
                reset_skip_rate_limit(user_id)
                await interaction.followup.send("Enter the new value in the chat.", ephemeral=False)
            
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


async def start_screenshot_flow(channel: discord.DMChannel, user_id: int, war_id: int, war_number: int):
    """Start the screenshot submission flow"""
    # Check if user already has an active session to prevent duplicates
    if user_id in active_dm_sessions:
        # User already has an active session, don't start a new one
        return
    
    # Initialize session for screenshot submission
    active_dm_sessions[user_id] = {
        'war_id': war_id,
        'war_number': war_number,
        'mode': 'screenshot',
        'waiting_for_confirmation': False
    }
    
    # Send instructions
    embed = discord.Embed(
        title=f"📷 Screenshot Submission - War {war_number}",
        description="Please attach a screenshot of your stats screen.\n\n"
                   "**Instructions:**\n"
                   "• Take a clear screenshot of your stats\n"
                   "• Make sure all text is readable\n"
                   "• Attach the image to this DM\n\n"
                   "I'll extract the stats from your screenshot automatically.\n\n"
                   f"Type `cancel` to cancel.",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)

