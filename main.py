from pymongo import MongoClient
import nextcord
from nextcord.ext import commands, tasks
from lib.str_arr.py_str_arr import StrArray
from lib.vec.vec import ui64_vec
from typing import Any, Self, Literal, Union
import traceback
import requests
import dotenv
import server
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
        req = requests.get(self.event_url() , headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
        if req.status_code == 200:
            try:
                return int(req.json()[0]['id'])
            except:
                return 0
        else:
            raise Exception("can't get last event id")
    
    def is_exists(self):
        return requests.get(self.event_url()).status_code == 200
    
    def get_real_name(self):
        if (req:=requests.get(f"https://api.github.com/repos/{self.user}/{self.repo}")).status_code == 200:
            self._user, self._repo = req.json()['full_name'].split("/", 1)
        else:
            raise Exception("can't get repository data")
    
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

load_repos()

@tasks.loop(seconds=5)
async def event_loop():
    for ind in range(len(repos)):
        repo_event_url = repos[ind]
        try:
            event_req = requests.get(repo_event_url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})
            if event_req.status_code == 200:
                try:
                    event_id = int(event_req.json()[0]['id'])
                except:
                    event_id = 0
            else:
                raise Exception
        except:
            repo: github_repository = github_repository.get_from_event_url(repo_event_url)
            for guild_data in t_guilds.find({"repos": {'$elemMatch': {'0': repo.url("GITHUB REPO")}}}, {"log-channel": 1, "repos.$": 1, 'id': 1}):
                try:
                    log_channel: nextcord.TextChannel = await bot.fetch_channel(int(guild_data['log-channel']))
                    await log_channel.send(embed=repo_removed_emb(guild_data['repos'][0][1], repo))
                except:
                    pass
                events_id.pop(ind)
                repos.pop(ind)
                t_guilds.update_many({}, {"$pull": {"repos": {'$in': [repo.url("GITHUB REPO")]}}})
            continue
        if event_id != events_id[ind]:
            last_event = event_req.json()[0]
            is_hanled = False
            emb = nextcord.Embed()
            match last_event:
                case {"type": "CreateEvent", "payload": payload, "actor": actor, "repo": repo}:
                    is_hanled = True
                    emb.title = "Create " + payload['ref_type'].capitalize() + " Event"
                    emb.description = f"summary: a new {payload['ref_type']} was added\nrepository: [{repo['name']}](https://github.com/{repo['name']})\nactor: [{actor['display_login']}](https://github.com/{actor['login']}/)\n"
                    emb.set_footer(text=actor['display_login'], icon_url=f"https://avatars.githubusercontent.com/u/{actor['id']}")
                case {"type": "DeleteEvent", "payload": payload, "actor": actor, "repo": repo}:
                    is_hanled = True
                    emb.title = "Delete " + payload['ref_type'].capitalize() + " Event"
                    emb.description = f"summary: a {payload['ref_type']} was removed\nrepository: [{repo['name']}](https://github.com/{repo['name']})\nactor: [{actor['display_login']}](https://github.com/{actor['login']}/)\n"
                    emb.set_footer(text=actor['display_login'], icon_url=f"https://avatars.githubusercontent.com/u/{actor['id']}")
                case {"type": "ForkEvent", "payload": payload, "actor": actor, "repo": repo}:
                    is_hanled = True
                    emb.title = "Fork Event"
                    emb.description = f"summary: a user forked this repository\nrepository: [{repo['name']}](https://github.com/{repo['name']})\nactor: [{actor['display_login']}](https://github.com/{actor['login']}/)\n"
                    emb.set_footer(text=actor['display_login'], icon_url=f"https://avatars.githubusercontent.com/u/{actor['id']}")
                case {"type": "PushEvent", "payload": payload, "actor": actor, "repo": repo}:
                    is_hanled = True
                    emb.title = "Push Event"
                    emb.description = f"summary: a user made a push\nrepository: [{repo['name']}](https://github.com/{repo['name']})\nactor: [{actor['display_login']}](https://github.com/{actor['login']}/)\nnumber of commits: {len(payload['commits'])}\nlast commit: [{payload['head'][:7]}](https://github.com/{repo['name']}/commits/{payload['head']})\nlast commit message: `{payload['commits'][-1]['message']}`"
                    emb.set_footer(text=actor['display_login'], icon_url=f"https://avatars.githubusercontent.com/u/{actor['id']}")
            if is_hanled:
                for guild_data in t_guilds.find({"repos": {'$elemMatch': {'0': last_event['repo']['name']}}}, {"log-channel": 1, 'id': 1}):
                    try:
                        if guild_data['log-channel'] != None:
                            log_channel: nextcord.TextChannel = await bot.fetch_channel(int(guild_data['log-channel']))
                            await log_channel.send(embed=emb)
                    except:
                        pass
            events_id[ind] = int(last_event['id'])

class add_or_remove_repo_emb(nextcord.Embed):
    def __init__(self, add=True):
        super().__init__(title="Adding repository" if add else "Removing repository", description="waiting to validating repository address...", color=0x0092ed)

class set_log_channel_emb(nextcord.Embed):
    def __init__(self, log_channel: nextcord.TextChannel):
        super().__init__(title="Log channel changed", description=f"log channel successfully changed to {log_channel.mention}", color=0x00ff00)
        
class repo_removed_emb(nextcord.Embed):
    def __init__(self, adder_id: Union[str, int], repo: github_repository):
        super().__init__(title="Error", description=f"<@{adder_id}> looks like the repository you added ([{repo.url('GITHUB REPO')}]({repo.url('HTTPS')})) has been removed. This repository was removed from the watch list.", color=0xff0000)

class log_channel_deleted_emb(nextcord.Embed):
    def __init__(self, owner: nextcord.Member):
        super().__init__(title="Error", description=f"{owner.mention} the channel log was deleted. To reset the log channel, use the `/set-log-channel` command", color=0xff0000)

@bot.event
async def on_ready():
    event_loop.start()
    print(f"logged in as {bot.user}, ID = {bot.user.id}")

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
    
@bot.event
async def on_guild_channel_delete(channel: nextcord.TextChannel):
    if t_guilds.find_one({'id': str(channel.guild.id), 'log-channel': str(channel.id)}) != None:
        t_guilds.update_one({"id": str(channel.guild.id)}, {"$set": {"log-channel": None}})
        await channel.guild.system_channel.send(embed=log_channel_deleted_emb(channel.guild.owner))
    
@bot.slash_command("set-log-channel", "set the text channel to display logs there")
async def set_log_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel = nextcord.SlashOption(required=True, description="text channel (note that the bot must have permission to send messages there)")):
    t_guilds.update_one({"id": str(interaction.guild.id)}, {"$set": {'log-channel': str(channel.id)}})
    await interaction.send(embed=set_log_channel_emb(channel))

@bot.slash_command("add-repo", "add new repository to watch list")
async def add_repo(interaction: nextcord.Interaction, repo: str = nextcord.SlashOption(required=True, description="url of repository (HTTPS, SSH or repository addres `user/repo`)")):
    emb = add_or_remove_repo_emb()
    msg: nextcord.PartialInteractionMessage = await interaction.send(embed=emb)
    if t_guilds.find({"id": str(interaction.guild.id)})[0]["log-channel"] == None:
        emb.title = "Adding repository was failed"
        emb.description = "log channel is not set"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    try:
        repository = github_repository.get_from_url(repo)
    except Exception as e:
        emb.title = "Adding repository was failed"
        emb.description = str(e)+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    else:
        emb.description = f"checking availability of [{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository"
        await msg.edit(embed=emb)
    if repository.is_exists():
        repository.get_real_name()
        emb.description = f"adding [{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository into watch list..."
        await msg.edit(embed=emb)
    else:
        emb.title = "Adding repository was failed"
        emb.description = "repository not found, may be private or not exist"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    
    if (t_guilds.find_one({"id": str(interaction.guild.id), "repos": {'$elemMatch': {'0': repository.url("GITHUB REPO")}}})) != None:
        emb.title = "Adding repository was failed"
        emb.description = "this repository is already in your watchlist"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
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
        emb.title = "Adding repository was failed"
        emb.description = "an error has occurred. please try again later"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    
    emb.title = "Adding repository was successfully"
    emb.description = f"[{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository has been added to the watch list."
    emb.color = 0x00ff00
    await msg.edit(embed=emb)
    
@bot.slash_command("remove-repo", "remove a repository from watch list")
async def remove_repo(interaction: nextcord.Interaction, repo: str = nextcord.SlashOption(required=True, description="url of repository (HTTPS, SSH or repository addres `user/repo`)")):
    emb = add_or_remove_repo_emb(False)
    msg: nextcord.PartialInteractionMessage = await interaction.send(embed=emb)
    try:
        repository = github_repository.get_from_url(repo)
    except Exception as e:
        emb.title = "Removing repository was failed"
        emb.description = str(e)+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    else:
        emb.description = f"Checking the existence of the [{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository"
        await msg.edit(embed=emb)
        
    if repository.is_exists():
        repository.get_real_name()
        if (db_res:=t_guilds.find_one({"id": str(interaction.guild.id), "repos": {'$elemMatch': {'0': repository.url("GITHUB REPO")}}})) == None:
            emb.title = "Removing repository was failed"
            emb.description = f"repository [{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) was not found in the watch list"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
            emb.color = 0xff0000
            await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
            return
        if not (interaction.user.guild_permissions.administrator or db_res['repos'][0][1] == str(interaction.user.id)):
            emb.title = "Removing repository was failed"
            emb.description = f"you do not have access to remove this repository from the contact list. You must have added this repository yourself or be an administrator to be able to do this"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
            emb.color = 0xff0000
            await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
            return
        emb.description = f"removing [{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository into watch list..."
        await msg.edit(embed=emb)
    else:
        emb.title = "Adding repository was failed"
        emb.description = "the repository entered in GitHub does not exist"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    try:
        t_guilds.update_one({"id": str(interaction.guild.id)}, {"$pull": {"repos": {'$in': [repository.url("GITHUB REPO")]}}})
        events_id.pop(ind:=repos.index(repository.event_url()))
        repos.pop(ind)
    except:
        traceback.print_exc()
        emb.title = "Removing repository was failed"
        emb.description = "an error has occurred. please try again later"+f".\n*(this message will be deleted after {DEL_ERR_MSG} seconds)*"
        emb.color = 0xff0000
        await msg.edit(embed=emb, delete_after=DEL_ERR_MSG)
        return
    emb.title = "Removing repository was successfully"
    emb.description = f"[{repository.url('GITHUB REPO')}]({repository.url('HTTPS')}) repository has been removed from the watch list."
    emb.color = 0x00ff00
    await msg.edit(embed=emb)

@bot.slash_command("watch-list", "veiw all repositories added with this server members")
async def show_watch_list(interaction: nextcord.Interaction):
    emb = nextcord.Embed()
    _repos, _users = [], []
    for repo, user in t_guilds.find_one({'id': str(interaction.guild.id)}, {'repos': 1, '_id': 0})['repos']:
        _repos.append(f"[{repo}](https://github.com/{repo})")
        _users.append(f"<@{user}>")
    if len(_repos) == 0:
        emb.description = "there are no repositories from your server in the watch list"
        emb.color = 0xff0000
        await interaction.send(embed=emb)
        return
    emb.title = "Server Watch list"
    emb.description = f"the repositories that are in the watch list for this server ({len(_repos)} items):"
    emb.add_field(name="reposository", value="\n".join(_repos))
    emb.add_field(name="added by", value="\n".join(_users))
    await interaction.send(embed=emb, allowed_mentions=nextcord.AllowedMentions(users=False))

if __name__ == "__main__":
    server.run_as_thread()
    try:
        bot.run(BOT_TOKEN)
    except nextcord.errors.HTTPException:
        os.system("kill 1")