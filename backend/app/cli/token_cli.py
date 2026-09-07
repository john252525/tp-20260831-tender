import argparse
import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.api_token import ApiToken

async def create_token(description, rate_limit):
    token = uuid.uuid4().hex
    async with AsyncSessionLocal() as session:
        api_token = ApiToken(token=token, description=description, rate_limit_per_minute=rate_limit)
        session.add(api_token)
        await session.commit()
        print(f'Token created: {token}')

async def revoke_token(token_id):
    try:
        token_uuid = uuid.UUID(token_id)
    except ValueError:
        print('Invalid UUID')
        return
    async with AsyncSessionLocal() as session:
        token = await session.get(ApiToken, token_uuid)
        if token:
            token.is_active = False
            await session.commit()
            print('Token revoked')
        else:
            print('Token not found')

async def list_tokens():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ApiToken))
        tokens = result.scalars().all()
        for t in tokens:
            print(f'{str(t.id)}: {t.description} active={t.is_active} last_used={t.last_used_at}')

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    create_parser = subparsers.add_parser('create')
    create_parser.add_argument('--description', required=True)
    create_parser.add_argument('--rate-limit', type=int, default=60)
    revoke_parser = subparsers.add_parser('revoke')
    revoke_parser.add_argument('token_id')
    list_parser = subparsers.add_parser('list')

    args = parser.parse_args()
    if args.command == 'create':
        asyncio.run(create_token(args.description, args.rate_limit))
    elif args.command == 'revoke':
        asyncio.run(revoke_token(args.token_id))
    elif args.command == 'list':
        asyncio.run(list_tokens())

if __name__ == '__main__':
    main()
