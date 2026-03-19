import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

COGS = ["cogs.courses", "cogs.grades", "cogs.professors"]


class CourseCompassBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)
            print(f"Loaded cog: {cog}")
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"CourseCompass is online as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="VT course registrations 🦃"
            )
        )


def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in your .env file.")
    bot = CourseCompassBot()
    bot.run(token)


if __name__ == "__main__":
    main()
