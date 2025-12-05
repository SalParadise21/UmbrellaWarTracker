"""Leaderboard update task handler"""
import discord
from discord.ext import tasks

from helpers.database import get_setting, get_active_war, get_leaderboard_by_category, get_leaderboard_message_id, set_leaderboard_message_id
from helpers.embed_helper import create_category_leaderboard_embed
from helpers.dm_handler import STAT_ORDER


async def update_leaderboard_task(bot):
    """Update the leaderboards in the specified channel (both active war and lifetime)"""
    channel_id = await get_setting("leaderboard_channel_id")
    if not channel_id:
        return
    
    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return
        
        # Update active war leaderboard
        active_war = await get_active_war()
        if active_war:
            category_data = {}
            for stat_name in STAT_ORDER:
                leaderboard_data = await get_leaderboard_by_category(stat_name, active_war['id'], limit=5)
                if leaderboard_data:
                    category_data[stat_name] = leaderboard_data
            
            if category_data:
                embed = await create_category_leaderboard_embed(category_data, active_war, bot, is_live=True)
                
                # Try to get existing leaderboard message
                message_id = await get_leaderboard_message_id(active_war['id'])
                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.edit(embed=embed)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        # Message was deleted or inaccessible, create new one
                        message = await channel.send(embed=embed)
                        await set_leaderboard_message_id(active_war['id'], message.id)
                else:
                    # Send new leaderboard message and store its ID
                    message = await channel.send(embed=embed)
                    await set_leaderboard_message_id(active_war['id'], message.id)
        
        # Update lifetime leaderboard
        lifetime_category_data = {}
        for stat_name in STAT_ORDER:
            leaderboard_data = await get_leaderboard_by_category(stat_name, None, limit=5)
            if leaderboard_data:
                lifetime_category_data[stat_name] = leaderboard_data
        
        if lifetime_category_data:
            lifetime_embed = await create_category_leaderboard_embed(lifetime_category_data, None, bot, is_live=True)
            
            # Try to get existing lifetime leaderboard message
            lifetime_message_id = await get_setting("lifetime_leaderboard_message_id")
            if lifetime_message_id:
                try:
                    lifetime_message_id = int(lifetime_message_id)
                    message = await channel.fetch_message(lifetime_message_id)
                    await message.edit(embed=lifetime_embed)
                except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
                    # Message was deleted or inaccessible, create new one
                    message = await channel.send(embed=lifetime_embed)
                    await set_setting("lifetime_leaderboard_message_id", str(message.id))
            else:
                # Send new lifetime leaderboard message and store its ID
                message = await channel.send(embed=lifetime_embed)
                await set_setting("lifetime_leaderboard_message_id", str(message.id))
        
    except Exception as e:
        print(f"Error updating leaderboard: {e}")


def start_leaderboard_updater(bot):
    """Start the leaderboard update task"""
    @tasks.loop(minutes=5)
    async def update_leaderboard():
        await update_leaderboard_task(bot)
    
    update_leaderboard.start()
    return update_leaderboard

