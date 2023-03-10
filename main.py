from pymongo import MongoClient
import nextcord
from nextcord.ext import commands
from lib.str_arr.py_str_arr import StrArray
from lib.vec.vec import ui64_vec
from typing import Any, Self, Literal, Union
import traceback
import requests
import dotenv
import os
import re

DEL_ERR_MSG = 30

class github_repository:
    def __init__(self, user: str, repo: str, type: str = "HTTPS") -> None:
        self.user = user
        self.repo = repo
        self.type = type
        
    @property
    def user(self) -> str:
        return self._user
    @user.setter
    def user(self, val: str) -> None:
        if not re.match("^([A-Za-z\d\-]{5,})$", val):
            raise Exception(f"username '{val}' is invalid")
        self._user = val
    
    @property
    def repo(self) -> str:
        return self._repo
    @repo.setter
    def repo(self, val: str) -> None:
        if not re.match("^(.{1,104})$", val):
            raise Exception(f"repository '{val}' is invalid")
        self._repo = re.sub("([^_\w\.]+)", "-", val)
        
    @property
    def type(self) -> str:
        if hasattr(self, "_type"):
            return self._type
        else:
            return None
    @type.setter
    def type(self, val: str) -> None:
        if hasattr(self, "_type"):
            raise Exception("can't change address type")
        else:
            if val in ("HTTPS", "SSH", "GITHUB REPO",):
                self._type = val
            else:
                raise Exception(f"repository type '{val}' not defined")

    @classmethod
    def get_from_url(cls, url: str) -> Self:
        _type = None
        _user = None
        _repo = None
        _data = None
        if url.startswith(("https://github.com/", "http://github.com/")):
            _type = "HTTPS"
            _data = re.findall("^https?://github\.com/([A-Za-z\d\-]{5,})/(.{1,104})$", url)
        elif url.startswith("git@github.com:"):
            _type = "SSH"
            _data = re.findall("^git@github\.com:([A-Za-z\d\-]{5,})/(.{1,104})$", url)
            if not _data[0][1].endswith(".git"):
                _data = ()
        else:
            _type = "GITHUB REPO"
            _data = re.findall("^([A-Za-z\d\-]{5,})/(.{1,104})$", url)
        if len(_data) > 0:
            _data = (_data[0][0], re.sub("(\.git)$", "", _data[0][1]))
            _user, _repo = _data
        else:
            raise Exception("repository address in invalid")
        return cls(_user, _repo, _type)
    
    @classmethod
    def get_from_event_url(cls, url: str) -> Self:
        _data = re.findall("^https?://api\.github\.com/repos/([A-Za-z\d\-]{5,})/(.{1,104})$", url)
        if len(_data) > 0:
            if _data[0][1].endswith("/events"):
                _repo = re.sub("([^_\w\.]+)", "-", re.sub("(/events)$", "", _data[0][1]))
            else:
                raise Exception("repository address in invalid")
            _user = _data[0][0]
            return cls(_user, _repo, "HTTPS")
        raise Exception("repository address in invalid")
    
    def url(self, as_type: Literal["HTTPS", "SSH", "GITHUB REPO"] = None) -> str:
        if as_type is None:
            as_type = self.type
        res = None
        match as_type:
            case "HTTPS":
                res = f"https://github.com/{self.user}/{self.repo}.git"
            case "SSH":
                res = f"git@github.com:{self.user}/{self.repo}.git"
            case "GITHUB REPO":
                res = f"{self.user}/{self.repo}"
            case _:
                raise Exception(f"repository type '{as_type}' not defined")
        return res
    
    def event_url(self):
        return f"https://api.github.com/repos/{self.user}/{self.repo}/events"
    
    def get_last_event_id(self):
        return int(requests.get(self.event_url() , headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}).json()[0]['id'])
    
    def is_exists(self):
        return requests.get(self.event_url()).status_code == 200
    
    def __repr__(self) -> str:
        return self.url()
    
    def __eq__(self, val) -> bool:
        if (_type:=type(val)) == github_repository:
            return self.event_url() == val.event_url()
        elif _type == str:
            return self.event_url() == github_repository.get_from_url(val).event_url()
        else:
            raise Exception(f"can't check equalment {type(self)} and {type(val)} objects")

dotenv.load_dotenv()

BOT_TOKEN=os.environ['BOT_TOKEN'] # discord bot token
GITHUB_TOKEN=os.environ['GITHUB_TOKEN'] # github token
DB_URI=os.environ['DB_URI'] # mongodb cluster url

connetion = MongoClient(DB_URI)
db = connetion['repobot-db']
t_guilds = db['guilds']

bot = commands.Bot("/", intents=nextcord.Intents.all())

repos = StrArray()
events_id = ui64_vec([])

def load_repos():
    global repos, events_id
    try:
        repos
    except:
        pass
    else:
        del repos
    try:
        events_id
    except:
        pass
    else:
        del events_id
    repos = StrArray()
    events_id = ui64_vec([])
    
    print("loading watch list...")
    
    for item in t_guilds.find():
        for repo in item['repos']:
            print("->", repo, end=" ")
            try:
                repos.index(repo[0])
            except ValueError:
                try:
                    repos.append(github_repository.get_from_url(repo[0]).event_url())
                except Exception as e:
                    print("failed")
                    traceback.print_exc()
                else:
                    print("loaded")
    print("repositories loaded")
    print("loading last events...", end=" ")
    for repo in repos:
        try:
            events_id.append(github_repository.get_from_event_url(repo).get_last_event_id())
        except KeyError:
            events_id.append(1)
    print("loaded")
        
async def event_loop():
    while True:
        for ind in range(len(repos)):
            req = requests.get(repos[ind], headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
            if req.status_code == 404:
                # removed!
                repo: github_repository = github_repository.get_from_event_url(repos[ind])
                for guild_data in t_guilds.find({"repos": {'$elemMatch': {'0': repo.url("GITHUB REPO")}}}, {"log-channel": 1, "repos.$": 1, 'id': 1}):
                    try:
                        log_channel: nextcord.TextChannel = await bot.fetch_channel(int(guild_data['log-channel']))
                        await log_channel.send(embed=repository_removed_emb(guild_data['repos'][0][1], repo))
                    except:
                        pass
                    events_id.pop(ind)
                    repos.pop(ind)
                    t_guilds.update_many({}, {"$pull": {"repos": {'$in': [repo.url("GITHUB REPO")]}}})
                continue
            event = req.json()[0]
            if int(event['id']) != events_id[ind]:
                # new event!
                pass
            
    

class add_project_emb(nextcord.Embed):
    def __init__(self):
        super().__init__(title="adding project", description="waiting to validating repository address...", color=0x0092ed)

class set_log_channel_emb(nextcord.Embed):
    def __init__(self, log_channel: nextcord.TextChannel):
        super().__init__(title="log channel changed", description=f"log channel successfully changed to {log_channel.mention}", color=0x00ff00)
        
class repository_removed_emb(nextcord.Embed):
    def __init__(self, adder_id: Union[str, int], repo: github_repository):
        super().__init__(title="Error", description=f"<@{adder_id}> it seems that the repository you added has been deleted", color=0xff0000)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}, ID = {bot.user.id}")
    load_repos()
    bot.loop.create_task(event_loop(), name="event_loop")
    print("event loop started")

@bot.event
async def on_guild_join(guild: nextcord.Guild):
    t_guilds.insert_one({"id": str(guild.id), "repos": [], "log-channel": None})
    
    integrations: list[nextcord.Integration] = await guild.integrations()
    for integration in integrations:
        if isinstance(integration, nextcord.BotIntegration):
            if integration.application.user.name == bot.user.name:
                inviter: nextcord.Member = integration.user
                break
    await guild.system_channel.send(f"{inviter.mention} Thank you for inviting me. To start the robot activity, you need to enter the log channel of the robot, you can do this by entering the `/set-log-channel` command.")

@bot.event
async def on_guild_remove(guild: nextcord.Guild):
    t_guilds.delete_one({"id": str(guild.id)})
    
@bot.slash_command("set-log-channel", "set the text channel to display logs there")
async def set_log_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel = nextcord.SlashOption(required=True, description="text channel (note that the bot must have permission to send messages there)")):
    t_guilds.update_one({"id": str(interaction.guild.id)}, {"$set": {'log-channel': str(channel.id)}})
    await interaction.send(embed=set_log_channel_emb(channel))

@bot.slash_command("add-project", "add new project to watch list")
async def add_project(interaction: nextcord.Interaction, repo: str = nextcord.SlashOption(required=True, description="url of repository (HTTPS, SSH or repository addres `user/repo`)")):
    emb = add_project_emb()
    msg: nextcord.PartialInteractionMessage = await interaction.send(embed=emb)
    if t_guilds.find({"id": str(interaction.guild.id)})[0]["log-channel"] == None:
        emb.title = "adding repository was failed"
        emb.description = "log channel is not set"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    try:
        repository = github_repository.get_from_url(repo)
    except Exception as e:
        emb.title = "adding repository was failed"
        emb.description = str(e)+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    else:
        emb.description = f"checking availability of [{repository.repo}]({repository.url('HTTPS')}) repository"
        await msg.edit(embed=emb)
    if repository.is_exists():
        emb.description = f"adding [{repository.repo}]({repository.url('HTTPS')}) repository into watch list..."
        await msg.edit(embed=emb)
    else:
        emb.title = "adding repository was failed"
        emb.description = "repository not found, may be private or not exist"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    
    try:
        t_guilds.update_one({"id": str(interaction.guild.id)}, {"$push": {"repos": [repository.url("GITHUB REPO"), str(interaction.user.id)]}})
        repos.append(repository.event_url())
        events_id.append(repository.get_last_event_id())
    except:
        t_guilds.update_one({"id": str(interaction.guild.id)}, {"$pull": {"repos": {'$in': [repository.url("GITHUB REPO")]}}})
        traceback.print_exc()
        emb.title = "adding repository was failed"
        emb.description = "an error has occurred. please try again later"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    
    emb.title = "adding repository was successfully"
    emb.description = f"[{repository.repo}]({repository.url('HTTPS')}) repository has been added to the watch list."
    emb.color = 0x00ff00
    await msg.edit(embed=emb)

bot.run(BOT_TOKEN)