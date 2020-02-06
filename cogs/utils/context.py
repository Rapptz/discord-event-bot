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

    async def prompt(self, message, *, timeout=60.0, delete_after=True):
        assert self.channel.permissions_for(self.me).add_reactions

        msg = await self.send(message)
        author_id = self.author.id
        confirm = None

        def check(payload):
            nonlocal confirm

            if payload.message_id != msg.id or payload.user_id != author_id:
                return False

            codepoint = str(payload.emoji)

            if codepoint == '\N{WHITE HEAVY CHECK MARK}':
                confirm = True
                return True
            elif codepoint == '\N{CROSS MARK}':
                confirm = False
                return True

            return False

        for emoji in ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}'):
            await msg.add_reaction(emoji)

        try:
            await self.bot.wait_for('raw_reaction_add', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            confirm = None

        try:
            if delete_after:
                await msg.delete()
        except discord.HTTPException:
            pass
        finally:
            return confirm

    async def request(self, message, converter=commands.MemberConverter(), *, timeout=60.0, delete_after=True):
        """Request information from the user interactively.

        Parameters
        -----------
        message: str
            The message to show along with the prompt.
        converter: :class:`Converter`
            The converter to convert the requested data from.
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.

        Returns
        --------
        Optional[Any]
            The result of the converter conversion applied to the message.
            If conversion fails then ``None`` is returned.
            If there's a timeout then ``...`` is returned.
        """

        await self.send(message)
        author_id = self.author.id
        channel_id = self.channel.id

        def check(m):
            return m.author.id == author_id and m.channel.id == channel_id

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            result = ...
        else:
            try:
                result = await converter.convert(self, msg.content)
            except Exception:
                result = None

        try:
            if delete_after:
                await msg.delete()
        except discord.HTTPException:
            pass
        finally:
            return result

    async def silent_react(self, emoji):
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass
