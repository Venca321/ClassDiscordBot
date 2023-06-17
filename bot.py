
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo
import discord, sqlite3, random, string, datetime, os

REPORT_TIME = datetime.datetime.strptime('17:00', '%H:%M')
DATABASE_FILE = "Data/database.db"
TOKEN = os.environ["TOKEN"]

intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command('help')

def get_id(length):
    while True:
        new_id = "".join(random.choice(string.ascii_letters+string.digits) for i in range(length))
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()
        cursor.execute("select * from zaznamy where id=:id", {"id": new_id})
        if cursor.fetchall(): connection.close()
        else: break
    return new_id

def db_setup():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    try: cursor.execute("create table zaznamy (id text, co_to_je text, predmet text, datum text, popis text)")
    except: None
    try: 
        cursor.execute("create table mute (mute text, time integer)")
        cursor.execute("insert into mute values (?,?)", ("mute", 0))
        connection.commit()
    except: None

    connection.close()

@client.event
async def on_ready():
    db_setup()
    my_task.start()
    print(f'{client.user} online!')

@client.command()
async def help(ctx):
    embedVar = discord.Embed(title=" ----- Jak používat tohoto bota? ----- ", color=0x00ff00)
    embedVar.add_field(name="!help", value="Tato nabídka", inline=False)
    embedVar.add_field(name="!add {test/úkol} / {předmět} / {datum} / {popis}", value="Přidá test/úkol do kalendáře\nDatum ve formátu den.měsíc.rok", inline=False)
    embedVar.add_field(name="!show {kolik dní dopředu}", value="Zobrazí úkoly/testy/vše\nkolik dní dopředu: číslo", inline=False)
    embedVar.add_field(name="!remove {id}", value="Odebere test/úkol", inline=False)
    await ctx.send(embed=embedVar)

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
  if payload.channel_id != 1083352973259841606: return
  if str(payload.emoji) == "👍":
    role = discord.utils.get(payload.member.guild.roles, name="Upozornění na testy")
    await payload.member.add_roles(role)

@client.command()
async def add(ctx, *, arguments):
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    arguments = arguments.split(" / ")
    co_to_je = arguments[0].lower()
    predmet = (arguments[1].lower())[:1].upper() + (arguments[1].lower())[1:]
    datum = arguments[2].split(".")
    popis = arguments[3]

    if datum[0].startswith("0"): den = datum[0][1:]
    else: den = datum[0]
    if datum[1].startswith("0"): mesic = datum[1][1:]
    else: mesic = datum[1]
    datum = f"{den}.{mesic}.{datum[2]}"

    today = datetime.date.today()
    d1 = datetime.datetime.strptime(datum, "%d.%m.%Y").date()
    if co_to_je == "test" or co_to_je == "úkol":
        if not len(datum.split(".")) == 3 and int(datum.split(".")[0]) <= 31 and int(datum.split(".")[1]) <= 12 and int(datum.split(".")[2]) <= (today+datetime.timedelta(days=1)).year and int(datum.split(".")[2]) > 2022:
            await ctx.send("Neplatný datum, zkuste formát den.mesic.rok")

        elif today>d1:
            await ctx.send("Datum nemůže být v minulosti")

        else:
            try:
                cursor.execute("insert into zaznamy values (?,?,?,?,?)", (get_id(15), co_to_je, predmet, datum, popis))
                connection.commit()
            except: None
            await ctx.send("Záznam byl úspěšně vytvořen")
    else: await ctx.send("Neplatný typ záznamu, zkuste test/úkol")

    connection.close()

@client.command()
async def show(ctx, *, kolik=999):
    kolik = int(kolik)
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    cursor.execute("select * from zaznamy")
    data = cursor.fetchall()

    counter = 0
    today = datetime.date.today()
    target_date = today + datetime.timedelta(days = kolik)
    will_show = {}
    for zaznam in data:
        d1 = datetime.datetime.strptime(zaznam[3], "%d.%m.%Y").date()
        if today > d1:
            cursor.execute("delete from zaznamy where id=:id", {"id":zaznam[0]})
            connection.commit()
        
        elif target_date >= d1:
            date = zaznam[3].split(".")
            value = int(date[0]) + (int(date[1]) * 100) + (int(date[2]) * 10_000)
            try:
                will_show[value] = will_show[value] + [[zaznam[3], zaznam[2], zaznam[1], zaznam[4], zaznam[0]]]
            except:
                will_show[value] = [[zaznam[3], zaznam[2], zaznam[1], zaznam[4], zaznam[0]]]
    
    myKeys = list(will_show.keys())
    myKeys.sort()
    sorted_show = {i: will_show[i] for i in myKeys}

    embedVar = discord.Embed(title=" ----- Kalendář záznamů ----- ", color=0x00ff00)
    for key in sorted_show.keys():
        records = sorted_show[key]
        for record in records:
            embedVar.add_field(name=f"{record[1]} ({record[2]})", value=f"Datum: {record[0]}\nPopis: {record[3]}\nID: {record[4]}", inline=False)
            counter += 1
    
    if counter > 0: await ctx.send(embed=embedVar)
    else: await ctx.send("Takové záznamy neexistují")

    connection.close()

@client.command()
async def remove(ctx, *, id):
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()

    try:
        cursor.execute("delete from zaznamy where id=:id", {"id":id})
        connection.commit()
        await ctx.send("Záznam úspěšně odstraněn")
    except:
        await ctx.send("Nastal nějaký problém")

    connection.close()

@client.command()
async def clear(ctx, *, kolik=5):
    if ctx.message.author.id == 710059910783697026:
        await ctx.channel.purge(limit=int(kolik)+1)

@client.command()
async def mute(ctx, *, time):
    if ctx.message.author.id == 710059910783697026:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        time = int(time)
        cursor.execute("delete from mute where mute=:mute", {"mute":"mute"})
        connection.commit()
        cursor.execute(f"insert into mute values (?,?)", ("mute", time))
        connection.commit()
        connection.close()

        await ctx.channel.send(f"Příštích {time} dní nebudu zasílat oznámení")

@client.command()
async def mute_for(ctx):
    if ctx.message.author.id == 710059910783697026:
        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        cursor.execute("select * from mute where mute=mute")
        data = cursor.fetchall()
        connection.close()

        if data[0][1] == 0: await ctx.channel.send(f"Oznámení jsou zapnutá")
        else: await ctx.channel.send(f"Oznámení nezasílám ještě {data[0][1]} dní")

allert_time = datetime.time(hour=REPORT_TIME.hour, minute=REPORT_TIME.minute, tzinfo=ZoneInfo("Europe/Prague"))
@tasks.loop(time=allert_time)
async def my_task():
    now = datetime.datetime.now()
    if not (now.weekday() == 4 or now.weekday() == 5):
        channel = client.get_channel(1083353935026335795)

        connection = sqlite3.connect(DATABASE_FILE)
        cursor = connection.cursor()

        cursor.execute("select * from mute where mute=mute")
        mute = cursor.fetchall()[0][1]

        if not mute == 0:
            cursor.execute("delete from mute where mute=:mute", {"mute":"mute"})
            connection.commit()
            cursor.execute(f"insert into mute values (?,?)", ("mute", mute-1))
            connection.commit()
            connection.close()
        
        else:
            embedVar = discord.Embed(title=" ---------- Na zítra ---------- ", color=0xff0000)

            cursor.execute("select * from zaznamy")
            data = cursor.fetchall()

            counter = 0
            today = datetime.date.today()
            target_date = today + datetime.timedelta(days=1)
            for zaznam in data:
                d1 = datetime.datetime.strptime(zaznam[3], "%d.%m.%Y").date()
                if today >= d1:
                    cursor.execute("delete from zaznamy where id=:id", {"id":zaznam[0]})
                    connection.commit()
                
                elif d1 == target_date:
                    embedVar.add_field(name=f"{zaznam[2]} ({zaznam[1]})", value=f"Datum: {zaznam[3]}\nPopis: {zaznam[4]}", inline=False)
                    counter += 1
            
            connection.close()

            if counter > 0: await channel.send("@here", embed=embedVar)
            else: await channel.send("Na zítra nic nemáme v kalendáři")

client.run(TOKEN)
