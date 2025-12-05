from mirror import APIContact

async def test_add_user():
    async def main():
        api_contact = APIContact()
        success = await api_contact.search_and_add(phone='18612393510')

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_add_user())