from pymongo import MongoClient
import nextcord
from nextcord.ext import commands
from lib.str_arr.py_str_arr import StrArray
from lib.vec.vec import ui64_vec
from typing import Any, Self, Literal
import requests
import asyncio
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
        if not re.match("^([A-Za-z\d\-\.]+)$", val):
            raise Exception(f"repository '{val}' is invalid")
        self._repo = val
        
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
        return cls(_user, re.sub("([^_\w\.]+)", "-", _repo), _type)
    
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
DB_URI=os.environ['DB_URI'] # mongodb cluster url

connetion = MongoClient(DB_URI)
db = connetion['repobot-db']
t_guilds = db['guilds']

bot = commands.Bot("/", intents=nextcord.Intents.all())

reps = StrArray()
events_id = ui64_vec([])


class add_project_emb(nextcord.Embed):
    def __init__(self):
        super().__init__(title="adding project", description="waiting to validating repository address...", color=0x0092ed)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}, ID = {bot.user.id}")

@bot.event
async def on_guild_join(guild: nextcord.Guild):
    t_guilds.insert_one({"id": str(guild.id), "repos": []})

@bot.slash_command("add-project", "add new project to watch list")
async def add_project(interaction: nextcord.Interaction, repo: str = nextcord.SlashOption(required=True, description="url of repository (HTTPS, SSH or repository addres `user/repo`)")):
    emb = add_project_emb()
    msg: nextcord.PartialInteractionMessage = await interaction.send(embed=emb)
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
    
    # `add to watch list` process here ...
    
    emb.title = "adding repository was successfully"
    emb.description = f"[{repository.repo}]({repository.url('HTTPS')}) repository has been added to the watch list."
    emb.color = 0x00ff00
    await msg.edit(embed=emb)

bot.run(BOT_TOKEN)