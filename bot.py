from discord.ext import commands
import config
import logging
import datetime
import discord

from cogs.utils import context

# This help command is simple so...
class HelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        e = discord.Embed(colour=0xFD8063)
        filtered = await self.filter_commands(self.context.bot.commands, sort=True)
        for command in filtered:
            e.add_field(name=f'{command.name} {command.signature}', value=command.short_doc, inline=False)

        await self.get_destination().send(embed=e)

    async def send_command_help(self, command):
        e = discord.Embed(title=f'{command.qualified_name} {command.signature}', colour=0xFD8063)
        e.description = command.help
        if isinstance(command, commands.Group):
            for child in command.commands:
                e.add_field(name=f'{child.qualified_name} {child.signature}', value=child.short_doc, inline=False)

        await self.get_destination().send(embed=e)

    send_group_help = send_command_help

class EventBot(commands.Bot):
    def __init__(self):
        super().__init__(help_command=HelpCommand(), command_prefix=commands.when_mentioned_or('e!'))
        self.uptime = None
        self.load_extension('cogs.admin')
        self.load_extension('cogs.virus')

    def run(self):
        super().run(config.token)

    async def on_ready(self):
        if self.uptime is None:
            self.uptime = datetime.datetime.utcnow()

        print(f'Logged on as {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print(f'Resumed connection...')

    async def on_message(self, message):
        ctx = await self.get_context(message, cls=context.Context)
        if ctx.valid:
            await self.invoke(ctx)
        else:
            self.dispatch('regular_message', message)

def main():
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

    log = logging.getLogger()
    log.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(fmt)
    log.addHandler(handler)

    bot = EventBot()
    bot.run()

if __name__ == '__main__':
    main()
