# Foxhole War Tracker Discord Bot

A Discord bot for tracking Foxhole game statistics across multiple wars. The bot allows users to submit stats via slash commands and automatically maintains leaderboards.

## Features

- **War Management**: Setup, start, and end wars
- **Stat Entry**: Manual entry or screenshot processing through DM interactions
- **Screenshot Processing**: Automatic stat extraction from screenshots using OCR (optional)
- **Stat Editing**: Edit previously submitted stats
- **Stat Tracking**: Store stats in SQLite database with war association
- **Stat Display**: View individual user stats for specific wars or lifetime
- **Real-time Leaderboards**: Automatic leaderboard updates in a specified channel
- **Data Governance**: Input validation ensuring data quality (numbers only, range checks)

## Setup

### Prerequisites

1. Python 3.12.10 (recommended) or Python 3.12+
2. Tesseract OCR installed on your system
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`

### Installation

1. **Ensure Python 3.12.10 is installed**:
   ```bash
   python --version
   # Should show: Python 3.12.10
   ```
   If you need to install Python 3.12.10, download it from [python.org](https://www.python.org/downloads/)

2. Clone or download this repository

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```
DISCORD_BOT_TOKEN=your_bot_token_here
LEADERBOARD_CHANNEL_ID=your_channel_id_here
TEST_GUILD_ID=your_guild_id_here  # Optional: For guild-level command syncing
```

5. Get your Discord bot token:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application or select an existing one
   - Go to the "Bot" section
   - Create a bot and copy the token
   - Enable "Message Content Intent" in the Bot settings
   - Enable "Server Members Intent" if you want to see member lists

6. Invite your bot to your server:
   - In the Developer Portal, go to "OAuth2" > "URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select bot permissions: `Send Messages`, `Read Message History`, `Attach Files`, `Embed Links`
   - Copy the generated URL and open it in your browser to invite the bot

### Running the Bot

```bash
python bot.py
```

## Commands

### War Management

- `/war_setup <war_number>` - Setup a new war number
- `/war_start <war_number>` - Start a war (deactivates all other wars) **[Admin only]**
- `/war_end <war_number>` - End a war **[Admin only]**
- `/view_wars` - View all wars in the database with status indicators

### Stat Entry

- `/stats_entry` - Opens a DM to enter your stats
  - Choose between **Manual Entry** (step-by-step prompts) or **Screenshot Submission** (OCR processing)
  - Manual entry uses buttons for Skip and Cancel actions
  - Screenshot processing extracts stats automatically from images
  - If you already have stats for the current war, new submissions will **replace** existing stats

- `/stats_edit` - Opens a DM to edit your most recent stats for the current war

### Stat Viewing

- `/stats_view [user] [war_number]` - View stats for a user (defaults to you, current war, or lifetime)
- `/leaderboard [leaderboard_type] [war_number]` - View the leaderboard (top 5 per category)
  - Options: "Active War" or "Lifetime"
  - Defaults to current active war, or lifetime if no active war

### Configuration (Admin Only)

- `/settings` - View and manage bot settings
  - Toggle screenshot processing on/off
  - Set leaderboard channel for automatic updates
- `/export_database` - Export database to CSV file (sent via DM)
- `/sync_commands` - Re-register all bot commands (useful after updates)

## Usage

1. **Setup a War**:
   ```
   /war_setup war_number:100
   /war_start war_number:100
   ```
   Use `/view_wars` to see all wars and their status (🟢 active, 🔴 inactive)

2. **Submit Stats**:
   - Use `/stats_entry` to open a DM with the bot
   - Choose your entry method:
     - **Manual Entry**: Step-by-step prompts with buttons for each stat
       - Use the **Skip** button to skip a stat (uses 0)
       - Use the **Cancel** button to cancel at any time
     - **Screenshot Submission**: Attach a screenshot of your stats screen
       - The bot will extract stats using OCR
       - Review extracted stats and confirm or reject
       - If extraction fails, you can retry or switch to manual entry
   - **Important**: If you already have stats for the current war, new submissions will **replace** your existing stats (not add to them)

3. **Edit Stats**:
   - Use `/stats_edit` to modify your stats for the current war
   - Select which stat to edit from the buttons
   - Enter the new value
   - Use the **Cancel** button to cancel at any time

4. **View Stats**:
   ```
   /stats_view                                    # Your stats for current war
   /stats_view user:@username war_number:100      # Specific user and war
   /leaderboard leaderboard_type:Active War      # Leaderboard for active war
   /leaderboard leaderboard_type:Lifetime         # Lifetime leaderboard
   ```

5. **Configure Settings** (Admin only):
   ```
   /settings  # Opens settings menu with buttons to:
              # - Toggle screenshot processing on/off
              # - Set leaderboard channel
   ```

6. **Export Data** (Admin only):
   ```
   /export_database  # Exports all database tables to CSV files (sent via DM)
   ```

## Database Schema

The bot uses SQLite with the following tables:

- **wars**: Stores war information (number, start/end dates, active status)
- **user_stats**: Stores user statistics per war
- **settings**: Stores bot configuration

## Notes

- The leaderboard updates every 5 minutes automatically
- **Stats replace existing entries**: If you submit stats multiple times for the same war, the new submission will **replace** your existing stats (not add to them)
- Make sure users have DMs enabled to use stat entry features
- Screenshot processing requires Tesseract OCR to be installed (see Prerequisites)
- Screenshot processing can be enabled/disabled via `/settings` (Admin only)
- All stat entry interactions use buttons - no need to type "skip" or "cancel" commands
- Input validation ensures data quality: numbers only (0-999,999,999), no spaces, text, or hyphens

## Troubleshooting

- **OCR not working**: 
  - Ensure Tesseract is installed and in your system PATH
  - Check that screenshot processing is enabled in `/settings`
  - Verify the screenshot is clear and readable
- **DM not received**: Check that the user has DMs enabled from server members
- **Bot not responding**: Verify the bot token is correct and the bot has necessary permissions
- **Database errors**: Delete `foxhole_stats.db` to reset (this will delete all data)
- **Commands not appearing**: Use `/sync_commands` (Admin only) to re-register commands
- **Button interactions hanging**: Check terminal for error messages; ensure the bot has proper permissions
- **Stats not updating**: Remember that new submissions **replace** existing stats for the same war, they don't add to them

## License

This project is provided as-is for personal use.

