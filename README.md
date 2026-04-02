# CourseCompass

A Discord bot for Virginia Tech students that provides AI-powered course recommendations, grade distributions, and professor ratings. Built by the commit-and-pray team for the CS team.

## Features

- **Course Recommendations** — Get AI-powered course suggestions based on your interests and academic level (freshman through graduate)
- **Grade Distributions** — View detailed grade distribution charts for VT courses
- **Compare Courses** — Compare side-by-side grade distributions for two courses
- **Professor Ratings** — Look up Rate My Professor ratings for Virginia Tech professors

## Prerequisites

- Python 3.10 or higher
- A Discord bot token
- OpenAI API key (for AI course recommendations)
- Internet connection (for Rate My Professor and course data)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CourseCompass
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the root directory with the following:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   **Getting your tokens:**
   - **Discord Bot Token:** Create a bot on the [Discord Developer Portal](https://discord.com/developers/applications), then copy the token
   - **OpenAI API Key:** Get it from your [OpenAI account](https://platform.openai.com/api-keys)

5. **Invite the bot to your Discord server**

   In the Discord Developer Portal:
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`
   - Copy the generated URL and open it in your browser to invite the bot

## Running the Bot

```bash
/usr/local/bin/python3.11 bot.py
```

You should see output like:
```
=== Setup hook called ===
Loaded cog: cogs.courses
Loaded cog: cogs.grades
Loaded cog: cogs.professors
Slash commands synced.
CourseCompass is online as YourBotName (ID: 123456789)
```

## Commands

All commands use Discord's slash command system. Type `/` in chat to see available commands.

### `/recommend`
Get AI-powered course recommendations based on your interests and academic level.

**Parameters:**
- `interests` (required): Topics or skills that interest you (e.g., "machine learning, web development, systems programming")
- `level` (required): Your academic level
  - Freshman
  - Sophomore
  - Junior
  - Senior
  - Graduate

**Example:**
```
/recommend interests: machine learning, AI level: Junior
```

### `/grades`
View grade distribution for a Virginia Tech course.

**Parameters:**
- `course` (required): Course code (e.g., "CS 3114", "ECE 2574")

**Features:**
- Autocomplete suggesting available courses as you type
- Displays grade distribution as a bar chart
- Shows percentages for each grade range (A, B, C, D/F, W)

**Example:**
```
/grades course: CS 3114
```

### `/compare`
Compare grade distributions of two VT courses side by side.

**Parameters:**
- `course1` (required): First course code
- `course2` (required): Second course code

**Features:**
- Shows both courses' grade breakdowns
- Side-by-side bar chart comparison
- Displays semester information for each course

**Example:**
```
/compare course1: CS 2114 course2: CS 3114
```

### `/professor`
Look up a Virginia Tech professor's Rate My Professor rating.

**Parameters:**
- `name` (required): Professor's name (e.g., "Godmar Back")

**Features:**
- Overall rating (0-5 stars)
- Difficulty level (0-5)
- "Would take again" percentage
- Total number of ratings
- Direct link to their Rate My Professor profile

**Example:**
```
/professor name: Godmar Back
```

## Project Structure

```
CourseCompass/
├── bot.py                 # Main bot entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
│
├── cogs/                  # Discord command modules
│   ├── __init__.py
│   ├── courses.py        # AI course recommendations
│   ├── grades.py         # Grade distribution commands
│   └── professors.py     # Professor rating lookups
│
└── utils/                # Utility modules
    ├── __init__.py
    ├── ai_client.py      # OpenAI integration
    ├── vt_data.py        # Virginia Tech course data
    ├── rmp.py            # Rate My Professor scraping
    ├── charts.py         # Grade distribution charts
    └── (other utilities)
```

## Dependencies

- **discord.py** (≥2.7.1) — Discord bot framework
- **openai** (≥1.0.0) — OpenAI API client for AI recommendations
- **matplotlib** (≥3.8.0) — Chart generation for grade distributions
- **Pillow** (≥10.0.0) — Image processing
- **python-dotenv** (≥1.0.0) — Environment variable management
- **aiohttp** (≥3.9.0) — Async HTTP client
- **certifi** (≥2024.0.0) — SSL certification validation

## Troubleshooting

### AI service import error with AnyIO

If you see an error like:

```
AI service error: cannot import name 'set_current_async_library' from 'anyio._core._eventloop' (.../Library/Python/3.9/...)
```

you are likely running with Python 3.9 user-site packages instead of this project's environment.

Use Python 3.10+ (recommended 3.11) and run from your project venv:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python bot.py
```

If needed, force-repair the 3.9 user-site dependency stack:

```bash
/usr/bin/python3 -m pip install --user --upgrade --force-reinstall "anyio>=4,<5" "httpx>=0.28,<1" "httpcore>=1,<2" "openai>=1,<3"
```

### Bot won't start
- Check that `DISCORD_TOKEN` is set correctly in `.env`
- Ensure your bot token is valid and hasn't been regenerated
- Check that the bot has permissions in your Discord server

### Commands aren't showing up
- Slash commands may take up to 1 hour to sync
- Try restarting the bot
- Check bot permissions in the Discord server (should have permission to use app commands)

### "Course not found" errors
- Course codes are case-insensitive, but format matters (e.g., use "CS 3114" not "CS3114")
- Use the autocomplete feature to see available courses
- Not all VT courses have grade data available

### API errors for AI recommendations
- Check that your OpenAI API key is valid and has available credits
- Ensure you have internet connectivity

### Rate My Professor errors
- Some professors may not be on Rate My Professor
- Try using the professor's full name
- Check that the name is spelled correctly

## Contributing

This project is maintained by the commit-and-pray team. For issues or feature requests, contact the team.

## License


## Support

---
