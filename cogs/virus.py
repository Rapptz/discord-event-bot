from discord.ext import commands
from collections import deque, defaultdict
from collections.abc import Sequence
from bisect import bisect_left

import dataclasses
import discord
import random
import datetime
import typing
import itertools
import asyncio
import textwrap
import enum

from .utils import storage, formats

GENERAL_ID = 336642776609456130
SNAKE_PIT_ID = 448285120634421278
TESTING_ID = 381963689470984203
EVENT_ID = 674833398744743936
INFECTED_ROLE_ID = 674811235190964235
HEALER_ROLE_ID = 674838998736437248
DISCORD_PY = 336642139381301249
MOD_TESTING_ID = 568662293190148106

# GENERAL_ID = 182325885867786241
# SNAKE_PIT_ID = 182328316676538369
# TESTING_ID = 182328141862273024
# EVENT_ID = 182332539975892992
# INFECTED_ROLE_ID = 674854333577297930
# HEALER_ROLE_ID = 674854310655557633
# DISCORD_PY = 182325885867786241

class UniqueCappedList(Sequence):
    def __init__(self, maxlen):
        self.data = deque(maxlen=maxlen)

    def __getitem__(self, idx):
        return self.data[idx]

    def __len__(self):
        return len(self.data)

    def __contains__(self, item):
        return item in self.data

    def __iter__(self):
        return iter(self.data)

    def __reversed__(self):
        return reversed(self.data)

    def index(self, value, *args, **kwargs):
        return self.data.index(value, *args, **kwargs)

    def count(self, value):
        return self.data.count(value)

    def append(self, item):
        if item not in self.data:
            self.data.append(item)

class State(enum.Enum):
    alive = 0
    dead = 1
    already_dead = 2
    cured = 3
    become_healer = 4

@dataclasses.dataclass
class Participant:
    member_id: int
    infected: bool = False
    healer: bool = False
    masked: bool = False
    immunocompromised: typing.Optional[bool] = None
    infected_since: typing.Optional[datetime.datetime] = None
    death: typing.Optional[datetime.datetime] = None
    sickness: int = 0
    backpack: typing.Dict[str, bool] = dataclasses.field(default_factory=dict)
    # healed: typing.List[int] = dataclasses.field(default_factory=list)
    # last_heal: typing.Optional[datetime.datetime] = None

    data_type: dataclasses.InitVar[int] = 1

    def __lt__(self, other):
        return isinstance(other, Participant) and self.member_id < other.member_id

    def __post_init__(self, data_type):
        # This is pretty hard to model realistically since the definition
        # of immunocompromised depends on what type, we have
        # old age, HIV, AIDS, cancer, transplant recipients, etc.
        # There are over 400 primary immunodeficiency disorders
        # So it's hard to pick a certain rate here.
        # For the sake of simplicity and to make the game more fun than realistic
        # an immunodeficiency rate of ~15% was chosen.
        if self.immunocompromised is None:
            self.immunocompromised = random.random() < 0.15

    def is_dead(self):
        return self.sickness >= 100

    def is_susceptible(self):
        return not self.infected and not self.healer

    def is_infectious(self):
        return self.infected and self.sickness not in (0, 100)

    def infect(self):
        if self.infected:
            return False

        self.infected = True
        self.sickness = 15
        self.infected_since = datetime.datetime.utcnow()
        return True

    def kill(self):
        if self.death:
            return False

        self.sickness = 100
        self.death = datetime.datetime.utcnow()
        return True

    def add_sickness(self, number=None):
        """Increases sickness. If no number is passed then it randomly increases it.

        Returns None if already dead, False if not dead, True if became dead.
        """

        if self.is_dead():
            return State.already_dead

        if number is None:
            # 1% chance of gaining +3
            # 5% chance of gaining +1
            roll = random.random()
            if roll < 0.01:
                self.sickness += 5 if self.immunocompromised else 3
            elif roll < 0.05:
                self.sickness += 2 if self.immunocompromised else 1
        else:
            self.sickness += number

        if self.sickness <= 0:
            self.sickness = 0
            return State.cured

        # RIP
        if self.is_dead():
            return State.dead
        return State.alive

    @property
    def sickness_rate(self):
        # The sickness rate is the adjusted sickness
        # when accounting for certain properties like wearing
        # a mask or being a healer
        # Masks are 35% effective in this model
        base = self.sickness * 0.65 if self.masked else self.sickness
        if self.healer:
            base /= 2.0

        return min(base * 1.5, 100.0) if self.immunocompromised else base

    def buy(self, item):
        item.in_stock -= 1
        self.backpack[item.emoji] = item.uses

    def use(self, item):
        state = item.use(self)
        self.backpack[item.emoji] -= 1
        return state

    def to_json(self):
        o = dataclasses.asdict(self)
        o['data_type'] = 1
        return o


@dataclasses.dataclass
class Item:
    emoji: str
    name: str
    description: str
    total: int
    code: str
    predicate: typing.Optional[str] = None
    in_stock: typing.Optional[int] = None
    unlocked: bool = False
    uses: int = 1

    data_type: dataclasses.InitVar[int] = 2

    def __post_init__(self, data_type):
        if self.in_stock is None:
            self.in_stock = self.total

        to_compile = f'def func(self, user):\n{textwrap.indent(self.code, "  ")}'
        if self.predicate is None:
            to_compile = f'{to_compile}\n\ndef pred(self, user):\n  return True'
        else:
            to_compile = f'{to_compile}\n\ndef pred(self, user):\n{textwrap.indent(self.predicate, "  ")}'

        env = globals()

        try:
            exec(to_compile, env)
        except Exception as e:
            raise RuntimeError(f'Could not compile source for item {self.emoji}: {e.__class__.__name__}: {e}') from e

        self._caller = env['func']
        self._pred = env['pred']

    def to_json(self):
        o = dataclasses.asdict(self)
        o['data_type'] = 2
        return o

    def use(self, user):
        return self._caller(self, user)

    def usable_by(self, user):
        return not user.is_dead() and self._pred(self, user)

    def is_buyable_for(self, user):
        return (not user.is_dead() and
                self.in_stock and
                self.unlocked and
                self._pred(self, user) and
                self.emoji not in user.backpack)

@dataclasses.dataclass
class Stats:
    infected: int = 0
    healers: int = 0
    dead: int = 0
    cured: int = 0

    data_type: dataclasses.InitVar[int] = 3

    def to_json(self):
        o = dataclasses.asdict(self)
        o['data_type'] = 3
        return o

class VirusStorageHook(storage.StorageHook):
    @classmethod
    def from_json(cls, data):
        try:
            data_type = data['data_type']
        except KeyError:
            return storage.StorageHook.from_json(data)

        if data_type == 1:
            return Participant(**data)
        elif data_type == 2:
            return Item(**data)
        elif data_type == 3:
            return Stats(**data)

class Virus(commands.Cog):
    """The discord.py virus has spread and needs to be contained \N{FACE SCREAMING IN FEAR}"""

    def __init__(self, bot):
        self.bot = bot
        self.storage = storage.Storage('virus.json', hook=VirusStorageHook, init=self.init_storage)
        # last 5 (unique) authors of a message
        # these are Participant instances
        self._authors = defaultdict(lambda: UniqueCappedList(maxlen=5))
        self._shop_restocking = False
        self._timer_has_data = asyncio.Event()
        self._task = bot.loop.create_task(self.day_cycle())

    def cog_unload(self):
        self._task.cancel()

    def init_storage(self):
        from .data import items
        return {
            'participants': {},
            'stats': Stats(),
            'store': [
                Item(**data)
                for data in items.raw
            ],
            'next_cycle': None,
            'event_started': None,
        }

    def cog_check(self, ctx):
        return ctx.guild and ctx.guild.id == DISCORD_PY and ctx.channel.id in (TESTING_ID, SNAKE_PIT_ID, MOD_TESTING_ID)

    @staticmethod
    def get_unique(number, elements, already_seen):
        diff = list(elements - already_seen)
        if len(diff) <= number:
            return diff

        elements = []
        while number:
            index = random.randrange(len(diff))
            elements.append(diff[index])
            del diff[index]
            number -= 1
        return elements

    async def get_participant(self, member_id):
        participants = self.storage['participants']
        string_id = str(member_id)
        try:
            return participants[string_id]
        except KeyError:
            participants[string_id] = participant = Participant(member_id=member_id)
            await self.storage.put('participants', participants)
            return participant

    async def day_cycle(self):
        if self.storage.get('next_cycle') is None:
            await self._timer_has_data.wait()

        await self.bot.wait_until_ready()
        while True:
            next_cycle = self.storage.get('next_cycle')
            await discord.utils.sleep_until(next_cycle)
            await self.continue_virus()
            await self.storage.put('next_cycle', next_cycle + datetime.timedelta(days=1))

    @commands.group()
    @commands.is_owner()
    async def virus(self, ctx):
        """Manages the virus"""
        pass

    async def new_virus_day(self, guild, infected=None, healers=None, new_infected=5, new_healers=2):
        infected = infected or set()
        healers = healers or set()

        infected_ret = set()
        healers_ret = set()
        for channel_id in (GENERAL_ID, SNAKE_PIT_ID, TESTING_ID):
            channel = guild.get_channel(channel_id)
            authors = {
                m.author
                async for m in channel.history(limit=500)
                if not m.author.bot and isinstance(m.author, discord.Member)
            }
            infected_ret.update(self.get_unique(new_infected, authors, infected | healers | healers_ret | infected_ret))
            healers_ret.update(self.get_unique(new_healers, authors, infected | healers | healers_ret | infected_ret))

        to_send = []

        # Initialize and fill the storage
        stats = self.storage['stats']
        stats.infected += len(infected_ret)
        stats.healers += len(healers_ret)

        participants = self.storage['participants']

        for member in infected_ret:
            try:
                await member.add_roles(discord.Object(id=INFECTED_ROLE_ID))
            except discord.HTTPException:
                to_send.append(f'\N{CROSS MARK} Could not infect {member.mention}')
            else:
                to_send.append(f'\N{WHITE HEAVY CHECK MARK} Infected {member.mention}')
            finally:
                participants[str(member.id)] = p = Participant(member_id=member.id)
                p.infect()

        for member in healers_ret:
            try:
                await member.add_roles(discord.Object(id=HEALER_ROLE_ID))
            except discord.HTTPException:
                to_send.append(f'\N{CROSS MARK} Could not make {member.mention} healer')
            else:
                to_send.append(f'\N{WHITE HEAVY CHECK MARK} Made {member.mention} healer')
            finally:
                participants[str(member.id)] = p = Participant(member_id=member.id, healer=True)

        await self.storage.save()

        infected_mentions = [str(m) for m in infected_ret]
        healer_mentions = [str(m) for m in healers_ret]

        if infected_mentions:
            await self.log_channel.send(f'{formats.human_join(infected_mentions)} are suddenly infected.')
        if healer_mentions:
            await self.log_channel.send(f'{formats.human_join(healer_mentions)} are suddenly healers...?')

        return '\n'.join(to_send)

    @virus.command(name='start')
    async def virus_start(self, ctx):
        """Starts the virus infection."""
        to_send = await self.new_virus_day(ctx.guild)
        if to_send:
            await ctx.send(to_send)

        now = ctx.message.created_at
        next_cycle = datetime.datetime.combine(now.date(), datetime.time()) + datetime.timedelta(days=1)
        await self.storage.put('event_started', now)
        await self.storage.put('next_cycle', next_cycle)
        self._timer_has_data.set()

    async def continue_virus(self):
        guild = self.bot.get_guild(DISCORD_PY)
        infected = set(guild.get_role(INFECTED_ROLE_ID).members)
        healers = set(guild.get_role(HEALER_ROLE_ID).members)

        try:
            await self.new_virus_day(guild, infected, healers, 2, 1)
        except discord.HTTPException:
            pass

        # Infect everyone who is currently infected:
        participants = self.storage['participants']
        for member in infected:
            try:
                user = participants[str(member.id)]
            except KeyError:
                continue

            if user.is_infectious():
                died = user.add_sickness(20)
                if died is State.dead:
                    await self.kill(user)

        await self.storage.save()

    def get_member(self, member_id):
        guild = self.bot.get_guild(DISCORD_PY)
        return guild.get_member(member_id)

    @property
    def log_channel(self):
        return self.bot.get_guild(DISCORD_PY).get_channel(EVENT_ID)

    async def infect(self, user):
        self.storage['stats'].infected += user.infect()
        await self.storage.save()

        member = self.get_member(user.member_id)
        if member is not None:
            await member.add_roles(discord.Object(id=INFECTED_ROLE_ID))

        await self.send_infect_message(user)

    async def kill(self, user):
        self.storage['stats'].dead += user.kill()
        await self.storage.save()
        await self.send_dead_message(user)

    async def cure(self, user):
        user.sickness = 0
        self.storage['stats'].cured += 1
        await self.storage.save()
        await self.send_cured_message(user)

    async def potentially_infect(self, channel_id, participant):
        # Infection rate is calculated using the last 5 people who sent messages in the channel.
        # We can consider it equivalent to the 5 people in the room.
        # Everyone has a sickness value assigned to them
        participants = self._authors[channel_id]
        if len(participants) == 0:
            return

        total_sickness = sum(p.sickness_rate for p in participants) / len(participants)

        # 0 sickness -> 0% chance, 100 sickness -> 10% chance
        # of getting infected
        cutoff = total_sickness / 1000

        if random.random() < cutoff:
            # got infected
            await self.infect(participant)

    async def send_dead_message(self, participant):
        guild = self.bot.get_guild(DISCORD_PY)
        total = self.storage['stats'].dead

        try:
            ping = self.bot.get_user(participant.member_id) or await self.bot.fetch_user(participant.member_id)
        except discord.HTTPException:
            return

        dialogue = [
            f'A moment silence for {ping} <:rooBless:597589960270544916> (by the way, {total} dead so far)',
            f"Some people die, some people live, others just disappear altogether. One thing is certain: {ping} isn't alive. Oh also, {total} dead so far.",
            f"Got a letter saying that {ping} isn't with us anymore. Can you believe we have {total} dead to this thing?",
            f"Uh.. {ping} died? I don't even know who {ping} is lol. Well anyway that's {total} dead.",
            f"Someone that goes by {ping} died. RIP. Kinda forgot what's supposed to go here. Oh yeah {total} dead so far.",
            f'\N{SKULL} {ping} has died. {total} dead so far.',
        ]

        try:
            await self.log_channel.send(random.choice(dialogue))
        except discord.HTTPException:
            pass

    async def send_infect_message(self, participant):
        total = self.storage['stats'].infected
        guild = self.bot.get_guild(DISCORD_PY)

        try:
            ping = self.bot.get_user(participant.member_id) or await self.bot.fetch_user(participant.member_id)
        except discord.HTTPException:
            return

        dialogue = [
            f'{ping} has been infected. {total} infected so far...',
            f'{ping} is officially infected. Feel free to stay away from them and {total-1} more.',
            f"Ya know, shaming someone for being sick isn't very nice. Protect {ping} and their {total-1} friends.",
            f"Unfortunately {ping} has fallen ill. Get well soon. Oh and {total} infected so far.",
            f'"from:{ping} sick" might bring up some interesting results <:rooThink:596576798351949847> ({total} infected)',
        ]

        try:
            await self.log_channel.send(random.choice(dialogue))
        except discord.HTTPException:
            pass

    async def send_cured_message(self, participant):
        total = self.storage['stats'].cured
        guild = self.bot.get_guild(DISCORD_PY)

        try:
            ping = self.bot.get_user(participant.member_id) or await self.bot.fetch_user(participant.member_id)
        except discord.HTTPException:
            return


        try:
            await self.log_channel.send(f'{ping} has been cured! Amazing. {total} cured so far.')
        except discord.HTTPException:
            pass

    async def send_healer_message(self, participant):
        total = self.storage['stats'].healers
        guild = self.bot.get_guild(DISCORD_PY)

        try:
            ping = self.bot.get_user(participant.member_id) or await self.bot.fetch_user(participant.member_id)
        except discord.HTTPException:
            return

        try:
            await self.log_channel.send(f'{ping} is now a healer...? Wonder what that means. Rather rare, only {total} of them.')
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_regular_message(self, message):
        if message.guild is None or message.guild.id != DISCORD_PY:
            return

        if message.author.id == self.bot.user.id:
            return

        user = await self.get_participant(message.author.id)
        if user.is_susceptible():
            await self.potentially_infect(message.channel.id, user)
        elif user.is_infectious():
            died = user.add_sickness()
            if died is State.dead:
                await self.kill(user)

        self._authors[message.channel.id].append(user)

    @commands.group(invoke_without_command=True, aliases=['store'])
    async def shop(self, ctx):
        """The item shop!"""
        user = await self.get_participant(ctx.author.id)
        buyable = [item for item in self.storage['store'] if item.is_buyable_for(user)]

        embed = discord.Embed(title='Item Shop')
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(format='png'))
        if len(buyable) == 0:
            embed.description = 'Nothing to see here'
            return await ctx.send(embed=embed)

        for item in buyable:
            embed.add_field(name=item.emoji, value=f'{item.in_stock} in stock!\n{item.name}\n{item.description}')

        await ctx.send(embed=embed)

    @shop.command(name='buy')
    @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
    @commands.check(lambda ctx: not ctx.cog._shop_restocking)
    async def shop_buy(self, ctx, *, emoji: str):
        """Buy an item from the shop

        You have to use the emoji to buy it.

        Items are free and on a first come, first served basis.
        You can only buy an item once.
        """

        item = discord.utils.get(self.storage['store'], emoji=emoji)
        if item is None:
            dialogue = [
                "It's {current_year} and we still don't know how to use emoji lol",
                "Hmm.. what are you buying? <:rooThink:596576798351949847>",
                "You look around the room. Countless people staring at your mistake. You leave in silence.",
            ]
            return await ctx.send(random.choice(dialogue))

        user = await self.get_participant(ctx.author.id)
        if not item.is_buyable_for(user):
            dialogue = [
                "Hm.. doesn't seem like you can buy that one bub.",
                "For some reason the cosmic rays are telling me that this isn't allowed to be purchased.",
                "Whoops, the item fell and I need to go look for it. Maybe it doesn't like you?",
                "Nothing to see here friend \N{SLEUTH OR SPY}\ufe0f",
            ]
            return await ctx.send(random.choice(dialogue))

        user.buy(item)
        await self.storage.save()
        await ctx.send(f'Alright {ctx.author.mention}, you bought {item.emoji}. Check your backpack.')

    @shop_buy.error
    async def shop_buy_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure) and self._shop_restocking:
            await ctx.send('Sorry, the store is being re-stocked right now...')

    @shop.command(name='restock', aliases=['unlock', 'lock'])
    @commands.is_owner()
    async def shop_restock(self, ctx, *items: str):
        """Control the shop."""
        status = []
        store = self.storage['store']
        getter = discord.utils.get

        for emoji in items:
            item = getter(store, emoji=emoji)
            if item is None:
                status.append(f'{emoji}: {ctx.tick(False)}')
            else:
                status.append(f'{emoji}: {ctx.tick(True)}')
                item.in_stock = item.total
                if ctx.invoked_with == 'unlock':
                    item.unlocked = True
                elif ctx.invoked_with == 'lock':
                    item.unlocked = False

        await self.storage.save()
        await ctx.send('\n'.join(status))

    @shop.command(name='refresh')
    @commands.is_owner()
    async def shop_refresh(self, ctx):
        """Refresh the shop with new data."""

        # This is hacky but YOLO
        from .data import items
        import importlib
        importlib.reload(items)

        pre_existing = self.storage['store']
        new_items = [Item(**data) for data in items.raw]
        tally = []

        # I'm only going to add items, I can't remove items.
        # Just lock them if they don't need to be there.
        for new, old in itertools.zip_longest(new_items, pre_existing):
            if old is None:
                if new is not None:
                    tally.append(new)
                continue
            else:
                tally.append(old)

        await self.storage.put('store', tally)
        await ctx.send(ctx.tick(True))

    @shop_restock.before_invoke
    @shop_refresh.before_invoke
    async def shop_restock_before(self, ctx):
        self._shop_restocking = True

    @shop_restock.after_invoke
    @shop_refresh.after_invoke
    async def shop_restock_after(self, ctx):
        self._shop_restocking = False

    @commands.command()
    @commands.is_owner()
    async def announce(self, ctx, *, message):
        """Announces something via the bot."""
        await self.log_channel.send(f'\N{CHEERING MEGAPHONE} {message}')

    @commands.group(invoke_without_command=True, aliases=['bp'])
    async def backpack(self, ctx):
        """Check your backpack."""

        user = await self.get_participant(ctx.author.id)
        embed = discord.Embed(title='Backpack')
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(format='png'))

        if not user.backpack:
            embed.description = 'Empty...'
            return await ctx.send(embed=embed)

        store = self.storage['store']
        for item in store:
            try:
                uses = user.backpack[item.emoji]
            except KeyError:
                continue

            if item.uses == 0:
                prefix = 'Special Item'
            else:
                prefix = f'uses: {uses}/{item.uses}'

            embed.add_field(name=item.emoji, value=f'`{prefix}`\n{item.description}', inline=False)

        await ctx.send(embed=embed)

    @backpack.command(name='use')
    async def backpack_use(self, ctx, *, emoji: str):
        """Use an item from your backpack.

        Similar to the store, you need to pass in the emoji
        of the item you want to use.
        """

        user = await self.get_participant(ctx.author.id)

        try:
            uses = user.backpack[emoji]
        except KeyError:
            dialogue = [
                "Buddy ya think this item exists or you have it? <:notlikeblob:597590860623773696>",
                "I don't know where you've heard of such items <:whenyahomiesaysomewildshit:596577153135673344>",
                "They told me this item doesn't exist bro. Run along now <:blobsweats:596577181518266378>",
                f"Yeah right, as if {discord.utils.escape_mentions(emoji)} isn't a figment of your imagination"
            ]
            return await ctx.send(random.choice(dialogue))

        if uses == 0:
            return await ctx.send("Uh I don't think this item can be used...")

        item = discord.utils.get(self.storage['store'], emoji=emoji)
        if item is None:
            return await ctx.send('Uh... if this happens tell Danny since this is pretty weird.')

        if not item.usable_by(user):
            return await ctx.send("Can't let you do that chief.")

        state = user.use(item)
        await self.storage.save()

        if state is State.already_dead:
            return await ctx.send("The dead can't use items...")
        elif state is State.dead:
            await self.kill(user)
        elif state is State.cured:
            await self.cure(user)
        elif state is State.become_healer:
            self.storage['stats'].healers += 1
            try:
                await ctx.author.add_roles(discord.Object(id=HEALER_ROLE_ID))
            except discord.HTTPException:
                pass
            finally:
                await self.storage.save()
                await self.send_healer_message(user)

        await ctx.send('The item was used... I wonder what happened?')

    @commands.command()
    async def info(self, ctx, *, member: discord.Member = None):
        """Shows you info about yourself, or someone else."""
        member = member or ctx.author
        embed = discord.Embed(title='Info')
        embed.set_author(name=str(member), icon_url=member.avatar_url_as(format='png'))

        user = await self.get_participant(member.id)

        badges = []
        if user.death is not None:
            badges.append('\N{COFFIN}')
            embed.set_footer(text='Dead since').timestamp = user.death
        if user.masked:
            badges.append('\N{FACE WITH MEDICAL MASK}')
        if user.is_infectious():
            badges.append('\N{BIOHAZARD SIGN}\ufe0f')
        if user.healer:
            badges.append('\N{STAFF OF AESCULAPIUS}\ufe0f')
        if user.immunocompromised:
            badges.append('\U0001fa78')

        embed.description = f'Sickness: [{user.sickness}/100]'
        embed.add_field(name='Badges', value=' '.join(badges) or 'None')
        embed.add_field(name='Backpack', value=' '.join(user.backpack) or 'Empty', inline=False)
        if user.infected_since and not user.death:
            embed.set_footer(text='Infected since').timestamp = user.infected_since

        await ctx.send(embed=embed)

    @commands.group()
    @commands.is_owner()
    async def gm(self, ctx):
        """Game master commands."""
        pass

    @gm.command(name='infect', aliases=['healer', 'kill'])
    async def gm_infect(self, ctx, *, member: discord.Member):
        """Infect or make a user a healer."""

        user = await self.get_participant(member.id)
        if ctx.invoked_with == 'infect':
            await self.infect(user)
        elif ctx.invoked_with == 'healer':
            user.healer = True
            self.storage['stats'].healers += 1
            try:
                await member.add_roles(discord.Object(id=HEALER_ROLE_ID))
            except discord.HTTPException:
                pass
            finally:
                await self.storage.save()
                await self.send_healer_message(user)
        elif ctx.invoked_with == 'kill':
            await self.kill(user)

    @gm.command(name='items')
    async def gm_items(self, ctx):
        """Shows current item metadata."""

        store = self.storage['store']
        to_send = [
            f'{i.emoji}: `<in_stock={i.in_stock} unlocked={i.unlocked} total={i.total} uses={i.uses}>`'
            for i in store
        ]
        await ctx.send('\n'.join(to_send))

    @gm.command(name='rates')
    async def gm_rates(self, ctx):
        to_send = []
        for channel_id, authors in self._authors.items():
            if len(authors) == 0:
                to_send.append(f'<#{channel_id}>: 0')
            else:
                total = sum(p.sickness_rate for p in authors) / len(authors)
                to_send.append(f'<#{channel_id}>: {total/1000:.3%}')

        await ctx.send('\n'.join(to_send))

    @commands.command(name='stats')
    async def _stats(self, ctx):
        """Stats on the outbreak."""

        stats = self.storage['stats']
        participants = len(self.storage['participants'])
        msg = f'Total Participants: {participants}\nDead: {stats.dead}\n' \
              f'Infected: {stats.infected - stats.cured - stats.dead}\nHealers: {stats.healers}\nCured: {stats.cured}\n'

        await ctx.send(msg)


def setup(bot):
    bot.add_cog(Virus(bot))
