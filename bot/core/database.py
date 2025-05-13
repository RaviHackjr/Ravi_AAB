from motor.motor_asyncio import AsyncIOMotorClient
from bot import Var
import datetime

class MongoDB:
    def __init__(self, uri, database_name):
        self.__client = AsyncIOMotorClient(uri)
        self.__db = self.__client[database_name]
        self.__animes = self.__db.animes[Var.BOT_TOKEN.split(':')[0]]
        self.__anime_channels = self.__db.anime_channels

    async def getAnime(self, ani_id):
        botset = await self.__animes.find_one({'_id': ani_id})
        return botset or {}

    async def saveAnime(self, ani_id, ep, qual, post_id=None):
        quals = (await self.getAnime(ani_id)).get(ep, {qual: False for qual in Var.QUALS})
        quals[qual] = True
        timestamp = datetime.datetime.now()
        quals["timestamp"] = timestamp
        await self.__animes.update_one({'_id': ani_id}, {'$set': {ep: quals}}, upsert=True)
        if post_id:
            await self.__animes.update_one({'_id': ani_id}, {'$set': {"msg_id": post_id}}, upsert=True)

    async def add_anime_channel_mapping(self, anime_name: str, channel: str):
        await self.__anime_channels.update_one(
            {"anime_name": anime_name.lower()},
            {"$set": {"channel_id": channel}},
            upsert=True
        )

    async def remove_anime_channel_mapping(self, anime_name: str, channel: int):
        await self.__anime_channels.delete_one(
            {"anime_name": anime_name.lower(), "channel_id": channel}
        )

    async def get_anime_channel(self, anime_name: str) -> int | None:
        entry = await self.__anime_channels.find_one({"anime_name": anime_name.lower()})
        return entry["channel_id"] if entry else None
        
    async def get_all_anime_channels(self):
        try:
            anime_channels = await self.__anime_channels.find().to_list(length=None)
            
            return {entry['anime_name']: entry['channel_id'] for entry in anime_channels}
        except Exception as e:
            print(f"Error fetching anime channels: {e}")
            return {}

    async def reboot(self):
        await self.__animes.drop()

db = MongoDB(Var.MONGO_URI, "GenAnimeOngoingV2")

