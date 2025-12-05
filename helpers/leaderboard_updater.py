"""Leaderboard update task handler"""
import discord
from discord.ext import tasks

from helpers.database import get_setting, get_active_war, get_leaderboard, get_leaderboard_message_id, set_leaderboard_message_id
from helpers.embed_helper import create_leaderboard_embed


async def update_leaderboard_task(bot):
    """Update the leaderboard in the specified channel"""
    channel_id = await get_setting("leaderboard_channel_id")
    if not channel_id:
        return
    
    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return
        
        active_war = await get_active_war()
        if not active_war:
            return
        
        leaderboard_data = await get_leaderboard(active_war['id'], 10)
        
        if not leaderboard_data:
            return
        
        embed = await create_leaderboard_embed(leaderboard_data, active_war, bot, is_live=True)
        
        # Try to get existing leaderboard message
        message_id = await get_leaderboard_message_id(active_war['id'])
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # Message was deleted or inaccessible, create new one
                pass
        
        # Send new leaderboard message and store its ID
        message = await channel.send(embed=embed)
        await set_leaderboard_message_id(active_war['id'], message.id)
        
    except Exception as e:
        print(f"Error updating leaderboard: {e}")


def start_leaderboard_updater(bot):
    """Start the leaderboard update task"""
    @tasks.loop(minutes=5)
    async def update_leaderboard():
        await update_leaderboard_task(bot)
    
    update_leaderboard.start()
    return update_leaderboard

