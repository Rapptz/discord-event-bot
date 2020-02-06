from discord.ext import commands
import discord
import io

class Context(commands.Context):
    def tick(self, opt, label=None):
        lookup = {
            True: '<:greenTick:596576670815879169>',
            False: '<:redTick:596576672149667840>',
            None: '<:greyTick:596576672900186113>',
        }
        emoji = lookup.get(opt, '<:redTick:596576672149667840>')
        if label is not None:
            return f'{emoji}: {label}'
        return emoji

    async def react_tick(self, opt):
        try:
            await self.message.add_reaction(self.tick(opt))
        except discord.HTTPException:
            pass

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        """Same as send except with some safe guards.

        1) If the message is too long then it sends a file with the results instead.
        2) If ``escape_mentions`` is ``True`` then it escapes mentions.
        """
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop('file', None)
            return await self.send(file=discord.File(fp, filename='message_too_long.txt'), **kwargs)
        else:
            return await self.send(content)
