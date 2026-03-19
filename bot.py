import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

COGS = ["cogs.courses", "cogs.grades", "cogs.professors"]


class CourseCompassBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

    async def setup_hook(self):
        print("=== Setup hook called ===")
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"Loaded cog: {cog}")
            except Exception as e:
                print(f"Failed to load cog {cog}: {e}")
        try:
            await self.tree.sync()
            print("Slash commands synced.")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f"CourseCompass is online as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="/recommend")
        )


def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in your .env file.")
    bot = CourseCompassBot()
    bot.run(token)


if __name__ == "__main__":
    main()
