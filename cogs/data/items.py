# The item store is a bit odd.
# Every person can only buy an item once (and it's put in their backpack).
# An item can only be bought once and they have limited uses.
# Items are free and on a first come first served basis. They get restocked every so often.
# The item shop only has a few items unlocked per day. They might rotate as well.

from textwrap import dedent

# An easier way to alias emoji items
class Emoji:
    mask = '\U0001f637'
    bed = '\U0001f6cf\ufe0f'
    soap = '\U0001f9fc'
    handsanitizer = '\U0001fa78'
    dna = '\U0001f9ec'
    microbe = '\U0001f9a0'
    petri_dish = '\U0001f9eb'
    test_tube = '\U0001f9ea'
    pill = '\N{PILL}'
    syringe = '\N{SYRINGE}'
    shower = '\N{SHOWER}'
    microscope = '\N{MICROSCOPE}'
    potato = '\N{POTATO}'
    herb = '\N{HERB}'
    books = '\N{BOOKS}'
    love_letter = '\N{LOVE LETTER}'
    present = '\N{WRAPPED PRESENT}'
    airplane = '\N{AIRPLANE}'
    bell = '\N{BELLHOP BELL}\ufe0f'
    meditate = '\U0001f9d8'
    toilet_paper = '\U0001f9fb'
    gun = '\N{PISTOL}'
    dagger = '\N{DAGGER KNIFE}\ufe0f'

raw = [
    {
        'emoji': Emoji.mask,
        'name': 'Mask',
        'total': 5,
        'description': 'Helps prevent the spread of the disease!',
        'code': 'user.masked = True',
    },
    {
        'emoji': Emoji.bed,
        'name': 'Rest',
        'total': 20,
        'uses': 3,
        'description': 'A good night\'s rest.',
        'code': dedent("""
            if user.infected:
                return user.add_sickness(-3)
        """),
    },
    {
        'emoji': Emoji.soap,
        'name': 'Soap',
        'total': 20,
        'uses': 3,
        'description': 'Washing your hands is always good.',
        'code': dedent("""
            if user.infected:
                user.sickness = max(user.sickness - 5, 5)
        """),
    },
    {
        'emoji': Emoji.handsanitizer,
        'name': 'Hand Sanitizer',
        'description': 'One of the best ways to prevent infection',
        'total': 10,
        'uses': 3,
        'code': dedent("""
            if user.infected:
                user.sickness = max(user.sickness - random.randint(10, 15), 5)
        """)
    },
    {
        'emoji': Emoji.dna,
        'name': 'Research Item',
        'description': 'Will we ever figure out the cause of this?',
        'total': 5,
        'uses': 0,
        'code': 'pass',
        'predicate': 'return user.healer',
    },
    {
        'emoji': Emoji.microbe,
        'name': 'Research Item',
        'description': 'Who did this?',
        'total': 5,
        'uses': 0,
        'code': 'pass',
        'predicate': 'return user.healer',
    },
    {
        'emoji': Emoji.petri_dish,
        'name': 'Research Item',
        'description': 'If we don\'t try then how will we know?',
        'total': 5,
        'uses': 0,
        'code': 'pass',
        'predicate': 'return user.healer',
    },
    {
        'emoji': Emoji.test_tube,
        'name': 'Research Item',
        'description': 'A cure must be possible, surely',
        'total': 5,
        'uses': 0,
        'code': 'pass',
        'predicate': 'return user.healer',
    },
    {
        'emoji': Emoji.microscope,
        'name': 'Research Item',
        'description': 'Research is necessary',
        'total': 5,
        'uses': 0,
        'code': 'pass',
        'predicate': 'return user.healer',
    },
    {
        'emoji': Emoji.syringe,
        'name': 'Donate Blood',
        'description': 'Donating blood for those in need might be helpful',
        'total': 10,
        'code': dedent("""
            if user.immunocompromised:
                return user.add_sickness(random.randint(20, 40))
            if user.infected:
                return user.add_sickness(random.randint(10, 15))
            return user.add_sickness(random.randint(-15, 15))
        """),
        'predicate': 'return user.is_infectious()'
    },
    {
        'emoji': Emoji.shower,
        'name': 'Shower',
        'description': 'You do shower right?',
        'total': 25,
        'uses': 5,
        'code': dedent("""
            if user.infected:
                if user.sickness >= 30:
                    user.sickness -= random.randint(8, 16)
                elif user.sickness >= 10:
                    user.sickness = max(user.sickness - 3, 10)
        """),
    },
    {
        'emoji': Emoji.pill,
        'name': 'Medicine',
        'description': 'Experimental medicine that might help',
        'total': 10,
        'code': dedent("""
            roll = random.random()
            if roll < 0.1:
                user.sickness = 0
                return State.cured
            return user.add_sickness(random.randint(-20, -5))
        """),
        'predicate': 'return user.is_infectious()',
    },
    {
        'emoji': Emoji.potato,
        'name': 'Potato',
        'unlocked': True,
        'total': 100,
        'description': '"Some people like potatoes. Me? I love potatoes." — Whoever buys this',
        'uses': 5,
        'code': 'user.sickness = max(user.sickness - 1, 1)',
        'predicate': 'return user.is_infectious()',
    },
    {
        'emoji': Emoji.herb,
        'name': 'Chinese medicine',
        'total': 20,
        'uses': 5,
        'description': 'Who needs western medicine?',
        'code': 'return user.add_sickness(random.randint(-2, 2))',
        'predicate': 'return user.is_infectious()',
    },
    {
        'emoji': Emoji.books,
        'name': 'Education',
        'description': 'The most important thing in a society',
        'total': 100,
        'code': dedent("""
            roll = random.random()
            if roll < 0.05:
                user.healer = True
                return State.become_healer
        """),
        'predicate': 'return not user.healer'
    },
    {
        'emoji': Emoji.love_letter,
        'name': 'Love Letter',
        'description': 'Send a love letter to someone in your dying breath.',
        'total': 5,
        'code': dedent(f"""
            member = await ctx.request('Who do you want to send this letter to?')
            if member is ...:
                raise VirusError("Timed out")
            elif member is None:
                raise VirusError("I don't know this member.")

            participant = await ctx.cog.get_participant(member.id)
            participant.backpack['{Emoji.love_letter}'] = 0
            chances = [(10, 'infect'), (89, 'nothing'), (1, 'kill')]
            value = weighted_random(chances)
            if value == 'infect':
                await ctx.cog.reinfect(participant)
            elif value == 'kill':
                await ctx.silent_react('\N{COLLISION SYMBOL}')
                return State.dead
        """),
        'predicate': 'return user.sickness >= 70'
    },
    {
        'emoji': Emoji.present,
        'name': 'Mystery Gift',
        'description': "I wonder what's inside",
        'total': 20,
        'code': dedent("""
            if user.is_susceptible():
                roll = random.random()
                if roll < 0.25:
                    await ctx.cog.infect(user)
            elif user.infected:
                roll = weighted_random([(1, 'a'), (3, 'b'), (6, 'c')])
                if roll == 'a':
                    await ctx.silent_react('\N{COLLISION SYMBOL}')
                    return State.dead
                elif roll == 'b':
                    return user.add_sickness(-10)
                else:
                    return user.add_sickness(random.randint(10, 20))
        """)
    },
    {
        'emoji': Emoji.airplane,
        'name': 'Fly',
        'description': "Go somewhere else, the sky's the limit",
        'total': 10,
        'code': dedent("""
            channel = await ctx.request('What channel should we fly to?', commands.TextChannelConverter)
            if channel is ...:
                raise VirusError('Timed out')
            elif channel is None:
                raise VirusError('Invalid channel')

            if user.healer:
                # Healers have a higher chance of healing
                rates = [(20, -20), (65, -5), (5, 20), (10, 15)]
            elif user.infected:
                rates = [(65, 20), (5, -5), (20, 10), (10, 15)]
            else:
                rates = [(90, 0), (5, -5), (5, 5)]

            sickness = weighted_random(rates)
            await ctx.cog.apply_sickness_to_all(channel, sickness, cause=user)
        """)
    },
    {
        'emoji': Emoji.bell,
        'name': "Evangelist's Bell",
        'description': "Probably not a good idea to touch this one...",
        'total': 25,
        'code': dedent("""
            rates = [(75, 'infect'), (2, 'cure'), (3, 'die'), (20, 'healer')]
            roll = weighted_random(rates)
            if roll == 'infect':
                await ctx.cog.reinfect(user)
            elif roll == 'cure':
                await ctx.cog.cure(user)
            elif roll == 'die':
                await ctx.cog.kill(user)
            elif roll == 'healer':
                return State.become_healer
        """)
    },
]
